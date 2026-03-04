"""Config flow for ETA Pellematic integration."""
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EtaApi
from .const import CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN, NAME


class EtaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for ETA Heating."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            api = EtaApi(session, user_input[CONF_HOST], user_input[CONF_PORT])

            if await api.check_connection():
                return self.async_create_entry(
                    title=f"{NAME} ({user_input[CONF_HOST]})",
                    data=user_input
                )
            else:
                errors["base"] = "cannot_connect"

        schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        })

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
