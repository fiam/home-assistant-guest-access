"""A scoped guest interface on HA's existing HTTP server; no extra server."""

from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .http import register_views
from .manager import Manager
from .storage import CheckedStore

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass, config):
    return True


async def async_setup_entry(hass: HomeAssistant, entry):
    async def dispatch(entity_id, action):
        await hass.services.async_call(
            entity_id.split(".", 1)[0], action, {"entity_id": entity_id}, blocking=True
        )

    def available(entity_id):
        state = hass.states.get(entity_id)
        return state is not None and state.state not in {"unavailable", "unknown"}

    manager = Manager(
        CheckedStore(hass, 1, DOMAIN, private=True),
        dispatch,
        available,
        key_store=CheckedStore(hass, 1, f"{DOMAIN}_key", private=True),
    )
    await manager.load()
    hass.data[DOMAIN] = entry.runtime_data = manager
    # Views stay registered across config-entry reloads and resolve the current manager.
    if not hass.data.get(f"{DOMAIN}_registered"):
        assets = await hass.async_add_executor_job(
            lambda: {
                p.name: p.read_text()
                for p in (Path(__file__).parent / "frontend").iterdir()
                if p.suffix in {".html", ".js", ".css"}
            }
        )
        register_views(hass, assets)
        hass.data[f"{DOMAIN}_registered"] = True
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path="guest-access-admin",
        webcomponent_name="guest-access-panel",
        sidebar_title="Guest Access",
        sidebar_icon="mdi:account-key",
        module_url="/guest-access/assets/admin.js?v=0.3.1",
        require_admin=True,
        config_panel_domain=DOMAIN,
    )
    return True


async def async_unload_entry(hass, entry):
    manager = hass.data.pop(DOMAIN)
    manager.closed = True
    frontend.async_remove_panel(hass, "guest-access-admin")
    # Drain accepted actions and writes; queued mutations reject the closed manager.
    await manager.close()
    return True


async def async_remove_entry(hass, entry):
    await Store(hass, 1, DOMAIN, private=True).async_remove()
    await Store(hass, 1, f"{DOMAIN}_key", private=True).async_remove()
