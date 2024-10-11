"""Support for InControl2 vehicles."""

import logging
from typing import Callable

from .incontrol2 import InControl2Device
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import Entity
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass

from .const import (
    DOMAIN,
    PEPLINK,
    SIGNAL_UNITS,
    IncontrolIcons
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(_hass: HomeAssistant,
                            _entry: ConfigEntry,
                            async_add_entities: Callable[[list, bool], None]):
    devs = []
    for device in InControl2Device.get_devices():

        for wan in device.wans:
            if wan.get("type") == "ethernet":
                continue

            devs.append(InControl2Wan(wan["id"], wan, device, {}))

    async_add_entities(devs, True)


class InControl2Wan(SensorEntity):

    def __init__(self, wan_id, wan, vehicle, store):
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

        self._wan = wan

        return True

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
        signal_bars = self._wan.get("signal_bar", 0)

        if self._wan.get("virtualType") == "cellular" and signal_bars <= 6:
            return IncontrolIcons.CELLULAR_STRENGTH[signal_bars]

        if self._wan.get("virtualType") == "wifi" and signal_bars <= 6:
            return IncontrolIcons.WIFI_STRENGTH[signal_bars]

        return IncontrolIcons.SIGNAL_DEFAULT

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
            "manufacturer": PEPLINK,
            "model": self._vehicle.data.get("product_name"),
            "sw_version": self._vehicle.data.get("fw_ver "),
        }

    @property
    def device_class(self):
        return SensorDeviceClass.SIGNAL_STRENGTH

    @property
    def suggested_unit_of_measurement(self):
        return SIGNAL_UNITS

    @property
    def unit_of_measurement(self):
        return SIGNAL_UNITS

    @property
    def entity_registry_enabled_default(self) -> bool:
        return self._wan.get("is_enable", 0) == 1
