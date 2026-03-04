"""Switch platform for ETA Pellematic."""
from typing import Any
from homeassistant.components.switch import SwitchEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [EtaSwitch(coordinator, uri, ep.name) 
                for uri, ep in coordinator.discovered_endpoints.items() 
                if uri.endswith("12080")]
    async_add_entities(entities)

class EtaSwitch(CoordinatorEntity, SwitchEntity):
    """Generic ETA On/Off Switch."""
    def __init__(self, coordinator, uri, name):
        super().__init__(coordinator)
        self._uri, self._attr_name = uri, name
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_sw_{uri}"

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data.get(self._uri)
        return data and data.get('raw') == "1803"

    async def async_turn_on(self, **kwargs):
        if await self.coordinator.api.write_value(self._uri, 1803):
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        if await self.coordinator.api.write_value(self._uri, 1802):
            await self.coordinator.async_request_refresh()
