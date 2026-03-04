"""Sensor platform for ETA Pellematic with DeviceClasses."""
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

UNIT_MAP = {
    "°C": (SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    "kW": (SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    "W": (SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    "kg": (SensorDeviceClass.WEIGHT, SensorStateClass.TOTAL_INCREASING),
    "bar": (SensorDeviceClass.PRESSURE, SensorStateClass.MEASUREMENT),
    "Pa": (SensorDeviceClass.PRESSURE, SensorStateClass.MEASUREMENT),
    "s": (SensorDeviceClass.DURATION, SensorStateClass.TOTAL_INCREASING),
    "h": (SensorDeviceClass.DURATION, SensorStateClass.TOTAL_INCREASING),
    "%": (None, SensorStateClass.MEASUREMENT),
}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [EtaSensor(coordinator, uri, ep.name) 
                for uri, ep in coordinator.discovered_endpoints.items()]
    async_add_entities(entities)

class EtaSensor(CoordinatorEntity, SensorEntity):
    """Representation of an ETA Sensor."""
    def __init__(self, coordinator, uri, name):
        super().__init__(coordinator)
        self._uri, self._attr_name = uri, name
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{uri}"
        self._attr_has_entity_name = True

    @property
    def native_value(self):
        data = self.coordinator.data.get(self._uri)
        if not data: return None
        if not data.get('unit'): return data.get('str_value')
        try:
            return float(data['raw']) / data['scale']
        except (ValueError, TypeError):
            return data.get('str_value')

    @property
    def native_unit_of_measurement(self):
        data = self.coordinator.data.get(self._uri)
        return data.get('unit') if data else None

    @property
    def device_class(self):
        unit = self.native_unit_of_measurement
        return UNIT_MAP.get(unit, (None, None))[0]

    @property
    def state_class(self):
        unit = self.native_unit_of_measurement
        return UNIT_MAP.get(unit, (None, None))[1]
