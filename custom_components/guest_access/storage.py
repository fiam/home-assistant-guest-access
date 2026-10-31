"""Confirm that access policy reached disk before acknowledging a change."""

import json
from pathlib import Path

from homeassistant.core import CoreState
from homeassistant.helpers.storage import Store
from homeassistant.util.file import WriteError


class CheckedStore(Store):
    """HA Store logs some write errors instead of propagating them to callers.

    Keep HA's format, private permissions and cache invalidation, but verify the
    on-disk result off the event loop. Access revocations must not report success
    when a write failed or was deferred until shutdown.
    """

    async def async_save(self, data):
        if self.hass.state is CoreState.stopping:
            raise WriteError("Guest access changes cannot be saved during shutdown")
        await super().async_save(data)
        saved = await self.hass.async_add_executor_job(
            lambda: json.loads(Path(self.path).read_bytes())
        )
        if saved != {
            "version": self.version,
            "minor_version": self.minor_version,
            "key": self.key,
            "data": data,
        }:
            raise WriteError("Guest access storage write could not be confirmed")
