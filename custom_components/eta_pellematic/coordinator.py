from datetime import timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL, DOMAIN

LOGGER = logging.getLogger(__name__)

class EtaDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, api, entry):
        self.api = api
        self.config_entry = entry
        
        scan_interval = entry.options.get(
            CONF_SCAN_INTERVAL, 
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )
        self.discovered_endpoints = {}

    async def async_setup(self):
        self.discovered_endpoints = await self.api.discover_endpoints()

    async def _async_update_data(self):
        uris = list(self.discovered_endpoints.keys())
        return await self.api.get_values(uris)
