"""Support for InControl2 vehicles."""

import logging
from typing import Callable

from .incontrol2 import InControl2Device
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.device_tracker.config_entry import TrackerEntity
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.components.device_tracker.const import (
    SourceType
)

from .const import (
    DOMAIN
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(_hass: HomeAssistant,
                            _entry: ConfigEntry,
                            async_add_entities: Callable[[list, bool], None]) -> None:
    """Set up the InControl2 device from config entry."""
    devs = []
    for device in InControl2Device.get_devices():
        devs.append(InControl2DeviceTracker(device, {}))

    async_add_entities(devs, True)


class InControl2DeviceTracker(TrackerEntity, RestoreEntity):

    def __init__(self, vehicle: InControl2Device, store):
        """Initialize the sensor."""
        """Initialize the thermostat."""
        self._vehicle = vehicle
        self._store = store
        self._data = {}
        self._state = 'offline'

        self._vehicle.add_entity(self)

    async def async_update(self) -> bool:
        await self._vehicle.update()

        _LOGGER.debug(f"lat: {self.latitude}, long: {self.longitude}")
        return True

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
        return SourceType.GPS

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
