"""Exercise actual HA Store failures, including its swallowed write errors."""

from unittest.mock import patch

import pytest
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.util.file import WriteError

from custom_components.guest_access.manager import AccessError, Manager
from custom_components.guest_access.storage import CheckedStore


async def test_failed_password_change_reports_error_and_pauses(tmp_path, link_data):
    hass = HomeAssistant(str(tmp_path))
    store = CheckedStore(hass, 1, "synthetic_policy", private=True)
    keys = CheckedStore(hass, 1, "synthetic_key", private=True)
    manager = Manager(store, None, lambda _: True, key_store=keys)
    try:
        await manager.load()
        await manager.set_enabled(True)
        result = await manager.save_link(link_data, password="synthetic-password-one")
        with patch.object(
            store, "_async_write_data", side_effect=WriteError("disk full")
        ):
            with pytest.raises(AccessError, match="storage_failed"):
                await manager.save_link(
                    link_data,
                    link_id=result["id"],
                    password="synthetic-password-two",
                )
        assert manager.enabled is False
        assert manager.sessions == {}
    finally:
        await hass.async_stop(force=True)


async def test_failed_key_creation_does_not_finish_setup(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    keys = CheckedStore(hass, 1, "synthetic_key", private=True)
    manager = Manager(
        CheckedStore(hass, 1, "synthetic_policy", private=True),
        None,
        lambda _: True,
        key_store=keys,
    )
    try:
        with patch.object(
            keys, "_async_write_data", side_effect=WriteError("read only")
        ):
            with pytest.raises(OSError):
                await manager.load()
        assert manager.cipher is None
        assert manager.enabled is False
    finally:
        await hass.async_stop(force=True)


async def test_shutdown_cannot_acknowledge_a_deferred_save(tmp_path):
    hass = HomeAssistant(str(tmp_path))
    store = CheckedStore(hass, 1, "synthetic_policy", private=True)
    try:
        await store.async_save({"enabled": False})
        hass.set_state(CoreState.stopping)
        with pytest.raises(WriteError):
            await store.async_save({"enabled": True})
        assert await store.async_load() == {"enabled": False}
    finally:
        await hass.async_stop(force=True)
