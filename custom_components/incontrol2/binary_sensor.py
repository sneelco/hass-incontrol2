"""Support for InControl2 vehicles."""

import logging
from typing import Callable

from .incontrol2 import InControl2Device
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass

from .const import (
    DOMAIN,
    PEPLINK,
    IncontrolIcons
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(_hass: HomeAssistant,
                            _entry: ConfigEntry,
                            async_add_entities: Callable[[list, bool], None]):
    devs = []
    for device in InControl2Device.get_devices():
        devs.append(InControl2Vehicle(device, {}))

        for wan in device.wans:
            devs.append(InControl2WanStatus(wan["id"], wan, device, {}))

    async_add_entities(devs, True)


class InControl2Vehicle(BinarySensorEntity):

    def __init__(self, vehicle: InControl2Device, store):
        """Initialize the sensor."""
        self._vehicle = vehicle
        self._store = store
        self._data = {}

        self._vehicle.add_entity(self)
        _LOGGER.debug("found device")

    @property
    def name(self):
        """Return the name of the sensor."""
        return f'{self._vehicle.name} Status'

    async def async_update(self) -> bool:
        await self._vehicle.update()

        return True

    @property
    def is_on(self) -> bool:
        return self._vehicle.state != "online"

    @property
    def device_class(self):
        return BinarySensorDeviceClass.PROBLEM

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
            "manufacturer": PEPLINK,
            "model": self._vehicle.data.get("product_name"),
            "sw_version": self._vehicle.data.get("fw_ver "),
        }

    @property
    def state_attributes(self):
        """Return the state attributes of the vehicle."""
        return self._vehicle.data


class InControl2WanStatus(BinarySensorEntity):

    def __init__(self, wan_id, wan, vehicle, store):
        """Initialize the sensor."""
        self._wan_id = wan_id
        self._wan = wan
        self._vehicle = vehicle
        self._store = store
        self._data = {}

        self._vehicle.add_entity(self)
        _LOGGER.debug("found wan device")

    async def async_update(self) -> bool:
        await self._vehicle.update()

        wan = next((wan for wan in self._vehicle.wans if wan.get(
            'id') == self._wan_id), None)

        if wan is None:
            _LOGGER.debug(f"WAN id {self._wan_id} not found in update")
            return False

        _LOGGER.debug(f"WAN id {self._wan_id} updated: {wan}")

        self._wan = wan

        return True

    @property
    def name(self):
        """Return the name of the sensor."""
        return f'{self._vehicle.name} {self.wan_name} Status'

    @property
    def wan_name(self):
        return self._wan.get('name')

    @property
    def is_connected(self):
        status = self._wan.get("status")
        return "Connected" in status

    @property
    def device_id(self):
        return f'{self._vehicle.org_id}_{self._vehicle.group_id}_{self._vehicle.device_id}'

    @property
    def unique_id(self):
        return f'{self._vehicle.org_id}_{self._vehicle.group_id}_{self._vehicle.device_id}_wan_status_{self._wan_id}'

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self.device_id)
            },
            "name": self._vehicle.data.get("name"),
            "manufacturer": PEPLINK,
            "model": self._vehicle.data.get("product_name"),
            "sw_version": self._vehicle.data.get("fw_ver "),
        }

    @property
    def device_class(self):
        return BinarySensorDeviceClass.CONNECTIVITY

    @property
    def state_attributes(self):
        return self._wan

    @property
    def is_on(self) -> bool | None:
        """Return if the sensor is on or off."""
        if "Connected" in self._wan.get('status'):
            return True
        else:
            return False

    @property
    def entity_registry_enabled_default(self) -> bool:
        return self._wan.get("is_enable") == 1
