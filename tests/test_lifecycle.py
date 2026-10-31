"""Discover and configure the integration using the actual HA config-entry flow."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from homeassistant import loader
from homeassistant.auth import auth_manager_from_config
from homeassistant.config_entries import ConfigEntries, ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry,
    device_registry,
    entity_registry,
    floor_registry,
    frame,
    label_registry,
)

from custom_components.guest_access.const import DOMAIN
from custom_components.guest_access.manager import AccessError


async def test_configure_reload_and_remove(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    loader.async_setup(hass)
    frame.async_setup(hass)
    (tmp_path / "custom_components").symlink_to(
        Path(__file__).parents[1] / "custom_components", target_is_directory=True
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
    hass.auth = await auth_manager_from_config(hass, [{"type": "homeassistant"}], [])
    try:
        flow = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert flow["type"] == "form"
        result = await hass.config_entries.flow.async_configure(flow["flow_id"], {})
        assert result["type"] == "create_entry"
        await hass.async_block_till_done()
        entry = result["result"]
        assert entry.state is ConfigEntryState.LOADED
        assert not hass.data[DOMAIN].enabled
        assert not hass.data[DOMAIN].links
        await hass.data[DOMAIN].set_enabled(True)
        now = datetime.now(UTC)
        saved = await hass.data[DOMAIN].save_link(
            {
                "name": "Persisted synthetic guest",
                "enabled": True,
                "starts_at": (now - timedelta(hours=1)).isoformat(),
                "expires_at": (now + timedelta(hours=1)).isoformat(),
                "grants": [
                    {"entity_id": "lock.synthetic", "action": "open", "label": "Open"}
                ],
            },
            password="synthetic-persisted-password",
        )
        session = await hass.data[DOMAIN].login(
            saved["id"], "synthetic-persisted-password", "peer"
        )
        remembered = await hass.data[DOMAIN].login(
            saved["id"],
            "synthetic-persisted-password",
            "remembered-peer",
            remember=True,
        )
        assert await hass.config_entries.async_reload(entry.entry_id)
        assert hass.data[DOMAIN].enabled
        assert hass.data[DOMAIN].status(remembered)
        assert len(hass.data[DOMAIN].sessions) == 1
        assert saved["id"] in hass.data[DOMAIN].links
        assert await hass.data[DOMAIN].reveal_password(saved["id"]) == {
            "password": "synthetic-persisted-password"
        }
        with pytest.raises(AccessError, match="sign_in"):
            hass.data[DOMAIN].status(session)
        persisted = (tmp_path / ".storage" / DOMAIN).read_text()
        assert "synthetic-persisted-password" not in persisted
        assert session not in persisted
        assert remembered not in persisted
        duplicate = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        assert duplicate["type"] == "abort"
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert DOMAIN not in hass.data
        await hass.config_entries.async_remove(entry.entry_id)
        assert not (tmp_path / ".storage" / DOMAIN).exists()
        assert not (tmp_path / ".storage" / f"{DOMAIN}_key").exists()
    finally:
        await hass.async_stop(force=True)
