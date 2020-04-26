"""Support for InControl2 vehicles."""

import logging

from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.device_tracker.const import (
    SOURCE_TYPE_GPS,
)

from .const import (
    DOMAIN,
    DATA_INCONTROL2
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up the Ambicliamte device from config entry."""
    devs = []
    for device in hass.data[DATA_INCONTROL2].get_all_devices():
        devs.append(InControl2DeviceTracker(device, {}))

    async_add_entities(devs, True)


class InControl2DeviceTracker(TrackerEntity, RestoreEntity):

    def __init__(self, vehicle, store):
        """Initialize the sensor."""
        """Initialize the thermostat."""
        self._vehicle = vehicle
        self._store = store
        self._data = {}
        self._state = 'offline'

        self._vehicle.add_entity(self)

    @property
    def name(self):
        """Return the name of the sensor."""
        return f'{self._vehicle.name} Location'

    @property
    def icon(self):
        return 'mdi:map-marker'

    @property
    def unique_id(self):
        return f'{self._vehicle.org_id}_{self._vehicle.group_id}_{self._vehicle.device_id}'

    @property
    def latitude(self):
        """Return latitude value of the device."""

        return self._vehicle.location.get('latitude')

    @property
    def longitude(self):
        """Return longitude value of the device."""

        return self._vehicle.location.get('longitude')

    @property
    def source_type(self):
        """Return the source type, eg gps or router, of the device."""
        return self._data.get("source_type", SOURCE_TYPE_GPS)

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.unique_id)
            },
            "name": self._vehicle.data.get("name"),
            "manufacturer": "PepLink",
            "model": self._vehicle.data.get("product_name"),
            "sw_version": self._vehicle.data.get("fw_ver "),
        }

    @property
    def state_attributes(self):
        """Return the state attributes of the sun."""
        return self._vehicle.location

    async def async_update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """

        await self._vehicle.update()
