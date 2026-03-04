"""Sensor platform for ETA Pellematic."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import EtaDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up ETA sensors dynamically."""
    coordinator: EtaDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = []
    # Loop through discovered endpoints and create entities
    for uri, endpoint in coordinator.discovered_endpoints.items():
        entities.append(EtaSensor(coordinator, uri, endpoint.name))

    async_add_entities(entities)


class EtaSensor(CoordinatorEntity, SensorEntity):
    """Representation of an ETA Sensor."""

    def __init__(self, coordinator, uri, name):
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._uri = uri
        self._custom_name = name
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{uri}"
        self._attr_has_entity_name = True

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._custom_name

    @property
    def native_value(self):
        """Return the value of the sensor."""
        data = self.coordinator.data.get(self._uri)
        if not data:
            return None

        # Logic: If unit exists, try to return float. Else return string.
        if data.get('unit'):
            try:
                raw = float(data.get('raw', 0))
                scale = float(data.get('scale', 1))
                return raw / scale
            except (ValueError, TypeError):
                pass
        
        return data.get('str_value')

    @property
    def native_unit_of_measurement(self):
        """Return the unit of measurement."""
        data = self.coordinator.data.get(self._uri)
        if data:
            return data.get('unit')
        return None

    @property
    def extra_state_attributes(self):
        """Return debugging attributes."""
        return {"uri": self._uri}
