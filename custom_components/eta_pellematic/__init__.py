"""The ETA Pellematic integration."""
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EtaApi
from .const import CONF_HOST, CONF_PORT, DOMAIN
from .coordinator import EtaDataUpdateCoordinator

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up ETA Pellematic from a config entry."""
    session = async_get_clientsession(hass)
    api = EtaApi(session, entry.data[CONF_HOST], entry.data[CONF_PORT])

    coordinator = EtaDataUpdateCoordinator(hass, api)

    # Perform discovery before setting up platforms
    await coordinator.async_setup()

    # Initial fetch
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
