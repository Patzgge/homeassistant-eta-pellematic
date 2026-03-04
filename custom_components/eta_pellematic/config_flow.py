"""Config flow and Options flow for ETA Pellematic."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN

class EtaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Initial setup via UI."""
        if user_input is not None:
            return self.async_create_entry(title=f"ETA ({user_input[CONF_HOST]})", data=user_input)

        # KORREKTUR: Hier stand vorher self.show_form -> muss async_show_form sein
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> EtaOptionsFlowHandler:
        """Get the options flow for this handler."""
        return EtaOptionsFlowHandler(config_entry)

class EtaOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options (Configure button)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict | None = None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Aktuellen Wert sicher abrufen
        options = self.config_entry.options
        data = self.config_entry.data
        current_interval = options.get(CONF_SCAN_INTERVAL, data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL))

        # KORREKTUR: Hier stand vorher self.show_form -> muss async_show_form sein
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=current_interval,
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            }),
        )
