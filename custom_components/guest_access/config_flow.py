"""One credential-free integration entry; links are managed in its admin panel."""

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow

from .const import DOMAIN


class GuestAccessConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")
        if user_input is not None:
            return self.async_create_entry(title="Guest Access", data={})
        return self.async_show_form(step_id="user", data_schema=vol.Schema({}))
