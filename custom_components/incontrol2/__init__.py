"""Support for InControl2 devices."""
import logging
from datetime import timedelta

import voluptuous as vol
from . import incontrol2

from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from . import config_flow
from .const import (
    DATA_INCONTROL2,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_SCAN_INTERVAL,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)
_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(minutes=10)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_CLIENT_ID): cv.string,
                vol.Required(CONF_CLIENT_SECRET): cv.string,
                vol.Optional(CONF_SCAN_INTERVAL, default=SCAN_INTERVAL): cv.time_period,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up Inconstrol2 components."""

    async def update_service(call):
        await update_devices()

    async def update_devices(now=None):
        data_connection = hass.data.get(DATA_INCONTROL2)

        if incontrol2 is None:
            return

        await data_connection.update_all_devices()

    async_track_time_interval(hass, update_devices, SCAN_INTERVAL)
    hass.services.async_register(DOMAIN, 'update_all', update_service)

    return True


async def async_setup_entry(hass, entry):
    """Set up Incontrol2 from a config entry."""

    config = entry.data
    websession = async_get_clientsession(hass)
    store = hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)
    token_info = await store.async_load()

    oauth = incontrol2.InControl2OAuth(
        config[CONF_CLIENT_ID],
        config[CONF_CLIENT_SECRET],
        config["callback_url"],
        websession,
    )

    try:
        token_info = await oauth.refresh_access_token(token_info)
    except incontrol2.InControl2OauthError:
        token_info = None

    if not token_info:
        _LOGGER.error("Failed to refresh access token")
        return

    await store.async_save(token_info)

    data_connection = incontrol2.InControl2Connection(
        oauth, token_info=token_info, websession=websession
    )

    if not await data_connection.find_orgs():
        _LOGGER.error("No orgs found")
        return

    hass.data[DATA_INCONTROL2] = data_connection

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "device_tracker")
    )

    return True
