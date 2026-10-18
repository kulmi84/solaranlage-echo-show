"""Local diagnostic status; no household readings or tokens in attributes."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([UploadStatus(hass.data[DOMAIN][entry.entry_id], entry)])


class UploadStatus(CoordinatorEntity, SensorEntity):
    _attr_has_entity_name = True
    _attr_name = "Verbindung"
    _attr_icon = "mdi:cloud-upload-outline"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator, entry):
        super().__init__(coordinator)
        self._attr_unique_id = entry.entry_id + "_connection"
        self._attr_device_info = {"identifiers": {(DOMAIN, entry.entry_id)}, "name": "Solaranlage Echo Show",
                                  "manufacturer": "Solaranlage", "model": "Cloud Relay"}

    @property
    def native_value(self):
        return self.coordinator.data["status"]

    @property
    def extra_state_attributes(self):
        return {key: self.coordinator.data.get(key) for key in ("last_upload", "history_status", "missing_values")}
