"""DataUpdateCoordinator for ETA Pellematic."""
import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import EtaApi
from .const import DOMAIN, UPDATE_INTERVAL

LOGGER = logging.getLogger(__name__)


class EtaDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the ETA API."""

    def __init__(self, hass: HomeAssistant, api: EtaApi):
        """Initialize the coordinator."""
        self.api = api
        self.discovered_endpoints = {}  # Map: uri -> EtaEndpoint

        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )

    async def async_setup(self):
        """Perform the initial discovery of sensors."""
        try:
            self.discovered_endpoints = await self.api.discover_endpoints()
            if not self.discovered_endpoints:
                LOGGER.warning("No ETA endpoints discovered.")
        except Exception as err:
            LOGGER.error("Discovery failed: %s", err)

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data for all discovered endpoints."""
        if not self.discovered_endpoints:
            await self.async_setup()

        uris_to_fetch = list(self.discovered_endpoints.keys())
        
        try:
            data = await self.api.get_values(uris_to_fetch)
            return data
        except Exception as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
