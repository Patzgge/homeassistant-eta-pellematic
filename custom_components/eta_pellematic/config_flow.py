"""Config flow and Options flow for ETA Pellematic."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.data_entry_flow import FlowResult

from .api import EtaApi
from .const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN

class EtaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ETA Pellematic."""
    VERSION = 1

    async def async_step_user(self, user_input: dict | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validierung: Wir prüfen, ob wir die Heizung erreichen können
            session = async_get_clientsession(self.hass)
            api = EtaApi(session, user_input[CONF_HOST], user_input.get(CONF_PORT, DEFAULT_PORT))
            
            if await api.check_connection():
                # Erfolg! Eintrag erstellen.
                # Wir setzen die Unique ID auf den Host, um Duplikate zu vermeiden
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                
                return self.async_create_entry(
                    title=f"ETA ({user_input[CONF_HOST]})", 
                    data=user_input
                )
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            }),
            errors=errors,
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

        # Aktuellen Wert sicher abrufen (Fallback auf Data, falls Options leer)
        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, 
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=current_interval,
                ): vol.All(vol.Coerce(int), vol.Range(min=10, max=3600)),
            }),
        )
