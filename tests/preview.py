"""Loopback-only UI preview with synthetic devices. NEVER use with production HA.

Run through tests/preview.sh. Its temporary admin bypass is preview-only and this
file is not included in the integration package.
"""

import asyncio
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aiohttp import web
from homeassistant import loader
from homeassistant.auth import auth_manager_from_config
from homeassistant.auth.const import GROUP_ID_ADMIN
from homeassistant.components.http import HomeAssistantView
from homeassistant.config_entries import ConfigEntries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry,
    device_registry,
    entity_registry,
    floor_registry,
    frame,
    label_registry,
)
from homeassistant.setup import async_setup_component


async def main():
    with tempfile.TemporaryDirectory() as config:
        hass = HomeAssistant(config)
        loader.async_setup(hass)
        frame.async_setup(hass)
        await asyncio.to_thread(
            Path(config, "custom_components").symlink_to,
            Path("/work/custom_components"),
        )
        hass.config_entries = ConfigEntries(hass, {})
        await hass.config_entries.async_initialize()
        device_registry.async_setup(hass)
        for registry in (
            floor_registry,
            area_registry,
            label_registry,
            device_registry,
            entity_registry,
        ):
            await registry.async_load(hass)
        hass.auth = await auth_manager_from_config(
            hass, [{"type": "homeassistant"}], []
        )
        await async_setup_component(hass, "api", {})
        flow = await hass.config_entries.flow.async_init(
            "guest_access", context={"source": "user"}
        )
        await hass.config_entries.flow.async_configure(flow["flow_id"], {})
        await hass.async_block_till_done()

        async def noop(call):
            pass

        for action in ("open", "lock", "unlock"):
            hass.services.async_register("lock", action, noop)
        for entity, label in (
            ("lock.synthetic_building", "Building entrance"),
            ("lock.synthetic_apartment", "Apartment door"),
        ):
            hass.states.async_set(
                entity, "locked", {"friendly_name": label, "supported_features": 1}
            )

        async def room_control(call):
            entity = call.data["entity_id"]
            state = hass.states.get(entity)
            attrs = dict(state.attributes)
            if call.domain == "light":
                brightness = round(call.data.get("brightness_pct", 100) * 255 / 100)
                on = call.service != "turn_off" and brightness > 0
                attrs["brightness"] = brightness if on else 0
                hass.states.async_set(entity, "on" if on else "off", attrs)
            else:
                position = call.data.get("position", attrs.get("current_position", 0))
                if call.service == "open_cover":
                    position = 100
                elif call.service == "close_cover":
                    position = 0
                attrs["current_position"] = position
                hass.states.async_set(entity, "open" if position else "closed", attrs)

        for domain, services in {
            "light": ("turn_on", "turn_off"),
            "cover": ("open_cover", "close_cover", "stop_cover", "set_cover_position"),
        }.items():
            for service in services:
                hass.services.async_register(domain, service, room_control)
        hass.states.async_set(
            "light.synthetic_room",
            "on",
            {
                "friendly_name": "Room light",
                "supported_color_modes": ["brightness"],
                "brightness": 153,
            },
        )
        hass.states.async_set(
            "cover.synthetic_room",
            "open",
            {
                "friendly_name": "Room blinds",
                "supported_features": 15,
                "current_position": 35,
            },
        )
        manager = hass.data["guest_access"]
        now = datetime.now(UTC)
        result = await manager.save_link(
            {
                "name": "Weekend guests",
                "enabled": True,
                "starts_at": (now - timedelta(hours=1)).isoformat(),
                "expires_at": (now + timedelta(days=2)).isoformat(),
                "grants": [
                    {
                        "entity_id": "lock.synthetic_building",
                        "action": "open",
                        "label": "Building entrance",
                    },
                    {
                        "entity_id": "lock.synthetic_apartment",
                        "action": "open",
                        "label": "Apartment door",
                    },
                ],
            },
            password="synthetic-preview-password",
        )
        room = await manager.save_link(
            {
                "name": "Guest room",
                "enabled": True,
                "starts_at": (now - timedelta(hours=1)).isoformat(),
                "expires_at": (now + timedelta(days=2)).isoformat(),
                "grants": [
                    {
                        "entity_id": f"{domain}.synthetic_room",
                        "action": action,
                        "label": label,
                    }
                    for domain, label, actions in (
                        (
                            "light",
                            "Room light",
                            ("turn_on", "turn_off", "set_brightness"),
                        ),
                        (
                            "cover",
                            "Room blinds",
                            (
                                "open_cover",
                                "close_cover",
                                "stop_cover",
                                "set_cover_position",
                            ),
                        ),
                    )
                    for action in actions
                ],
            },
            password="synthetic-preview-password",
        )
        await manager.set_enabled(True)
        user = await hass.auth.async_create_user(
            "Preview administrator", group_ids=[GROUP_ID_ADMIN]
        )
        refresh = await hass.auth.async_create_refresh_token(
            user, client_id="http://localhost/"
        )
        token = hass.auth.async_create_access_token(refresh)

        class Preview(HomeAssistantView):
            url = "/preview-admin"
            name = "guest_access:preview"
            requires_auth = False

            async def get(self, request):
                return web.Response(
                    content_type="text/html",
                    text="""<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;--primary-background-color:#f5f7fa;--card-background-color:white;--primary-text-color:#202b36;--secondary-text-color:#65717e;--primary-color:#007eae;--divider-color:#dce3e9;--secondary-background-color:#e4f4fc}</style></head><body><guest-access-panel></guest-access-panel><script type="module">import '/guest-access/assets/admin.js';document.querySelector('guest-access-panel').hass={callApi:async(method,path,data)=>{const response=await fetch('/api/'+path,{method,headers:{'Content-Type':'application/json','Authorization':'Bearer TOKEN'},body:JSON.stringify(data)});const result=await response.json();if(!response.ok)throw Error(result.message);return result;}};</script></body></html>""".replace(
                        "TOKEN", token
                    ),
                )

        class GuestPreview(HomeAssistantView):
            url = "/preview-guest"
            name = "guest_access:preview_guest"
            requires_auth = False

            async def get(self, request):
                raise web.HTTPFound(
                    "/guest-access#"
                    + (room if request.query.get("room") else result)["id"]
                )

        hass.http.register_view(Preview())
        hass.http.register_view(GuestPreview())
        runner = web.AppRunner(hass.http.app, access_log=None)
        await runner.setup()
        await web.TCPSite(runner, "0.0.0.0", 18123).start()
        print("Synthetic preview ready on the loopback-published port", flush=True)
        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()
            await hass.async_stop(force=True)


asyncio.run(main())
