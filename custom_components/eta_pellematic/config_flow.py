import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL, DEFAULT_PORT, DEFAULT_SCAN_INTERVAL, DOMAIN

class EtaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title=f"ETA ({user_input[CONF_HOST]})", data=user_input)

        return self.show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            }),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EtaOptionsFlowHandler(config_entry)

class EtaOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.config_entry.options.get(
            CONF_SCAN_INTERVAL, 
            self.config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )

        return self.show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(CONF_SCAN_INTERVAL, default=current_interval): vol.All(
                    vol.Coerce(int), vol.Range(min=10, max=3600)
                ),
            }),
        )
