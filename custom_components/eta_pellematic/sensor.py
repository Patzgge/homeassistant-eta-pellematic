from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN

UNIT_MAP = {
    "°C": (SensorDeviceClass.TEMPERATURE, SensorStateClass.MEASUREMENT),
    "kW": (SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT),
    "kg": (SensorDeviceClass.WEIGHT, SensorStateClass.TOTAL_INCREASING),
    "bar": (SensorDeviceClass.PRESSURE, SensorStateClass.MEASUREMENT),
    "Pa": (SensorDeviceClass.PRESSURE, SensorStateClass.MEASUREMENT),
}

async def async_setup_entry(hass, entry, async_add_entities):
    coordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [EtaSensor(coordinator, uri, ep.name) for uri, ep in coordinator.discovered_endpoints.items()]
    async_add_entities(entities)

class EtaSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, uri, name):
        super().__init__(coordinator)
        self._uri, self._attr_name = uri, name
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{uri}"
        self._attr_has_entity_name = True

    @property
    def native_value(self):
        data = self.coordinator.data.get(self._uri)
        if not data: return None
        str_val, unit = data.get('str_value', ''), data.get('unit')
        
        if str_val in ["xxx", "---", "", None]:
            return None if unit else "Inaktiv"
        
        if unit:
            try: return float(data['raw']) / data.get('scale', 1)
            except: return str_val
        return str_val

    @property
    def native_unit_of_measurement(self):
        if isinstance(self.native_value, (int, float)):
            return self.coordinator.data.get(self._uri, {}).get('unit')
        return None

    @property
    def device_class(self):
        unit = self.coordinator.data.get(self._uri, {}).get('unit')
        return UNIT_MAP.get(unit, (None, None))[0]

    @property
    def state_class(self):
        unit = self.coordinator.data.get(self._uri, {}).get('unit')
        return UNIT_MAP.get(unit, (None, None))[1]
