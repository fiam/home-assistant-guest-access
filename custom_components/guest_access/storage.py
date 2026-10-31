"""Confirm that access policy reached disk before acknowledging a change."""

import asyncio
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
        # A cancelled request must not release the manager's mutation lock while
        # an executor write can still overwrite a newer access policy.
        write = asyncio.create_task(self._async_save_checked(data))
        cancelled = False
        while not write.done():
            try:
                await asyncio.shield(write)
            except asyncio.CancelledError:
                cancelled = True
        write.result()
        if cancelled:
            raise asyncio.CancelledError

    async def _async_save_checked(self, data):
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
