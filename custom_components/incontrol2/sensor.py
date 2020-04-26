"""Support for InControl2 vehicles."""

import logging

from homeassistant.helpers.entity import Entity

from .const import (
    DOMAIN,
    DATA_INCONTROL2
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    devs = []
    for device in hass.data[DATA_INCONTROL2].get_all_devices():
        devs.append(InControl2Vehicle(device, {}))

        for wan in device.wans:
            devs.append(InControl2Wan(wan["id"], wan, device, {}))

    async_add_entities(devs, True)


class InControl2Vehicle(Entity):

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
        return f'{self._vehicle.name} Status'

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._vehicle.state

    @property
    def icon(self):
        return 'mdi:van-utility'

    @property
    def unique_id(self):
        return f'{self._vehicle.org_id}_{self._vehicle.group_id}_{self._vehicle.device_id}'

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
        return self._vehicle.data

    async def async_update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """

        await self._vehicle.update()


class InControl2Wan(Entity):

    def __init__(self, wan_id, wan, vehicle, store):
        """Initialize the sensor."""
        """Initialize the thermostat."""
        self._wan_id = wan_id
        self._wan = wan
        self._vehicle = vehicle
        self._store = store
        self._data = {}

        self._vehicle.add_entity(self)

    @property
    def name(self):
        """Return the name of the sensor."""
        return f'{self._vehicle.name} {self.wan_name} Signal'

    @property
    def wan_name(self):
        return self._wan.get('name')

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._wan.get("signal")

    @property
    def icon(self):
        icons = [
            'mdi:network-strength-off-outline',
            'mdi-network-strength-outline',
            'mdi:network-strength-1',
            'mdi:network-strength-2',
            'mdi:network-strength-3',
            'mdi:network-strength-4'
        ]

        signal_bars = self._wan.get("signal_bar")

        if signal_bars <= 6:
            return icons[signal_bars]

        return icons[0]

    @property
    def device_id(self):
        return f'{self._vehicle.org_id}_{self._vehicle.group_id}_{self._vehicle.device_id}'

    @property
    def unique_id(self):
        return f'{self._vehicle.org_id}_{self._vehicle.group_id}_{self._vehicle.device_id}_wan_{self._wan_id}'

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.device_id)
            },
            "name": self._vehicle.data.get("name"),
            "manufacturer": "PepLink",
            "model": self._vehicle.data.get("product_name"),
            "sw_version": self._vehicle.data.get("fw_ver "),
        }

    @property
    def unit_of_measurement(self):
        return "db"

    @property
    def state_attributes(self):
        """Return the state attributes of the sun."""
        return self._wan

    async def async_update(self):
        """Fetch new state data for the sensor.
        This is the only method that should fetch new data for Home Assistant.
        """

        await self._vehicle.update()
