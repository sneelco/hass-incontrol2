"""Support for InControl2 devices."""
import logging
from datetime import timedelta

from . import incontrol2

from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.storage import Store
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.config_entries import ConfigEntryAuthFailed

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


async def async_setup(hass: HomeAssistant, *_) -> bool:
    """Set up InControl2 components."""

    async def update_service(*_) -> None:
        await update_devices()

    async def update_devices(*_) -> None:
        _LOGGER.debug("Scheduled update of all devices")
        incontrol2device = hass.data.get(DATA_INCONTROL2)

        if incontrol2device is None:
            return

        await incontrol2device.update_all()

    hass.services.async_register(DOMAIN, 'update_all', update_service)
    # TODO: Add service for checking for new devices

    async_track_time_interval(hass, update_devices, SCAN_INTERVAL)
    # TODO: Check for new devices occasionally
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Incontrol2 from a config entry."""

    config = entry.data
    websession = async_get_clientsession(hass)
    store = Store(hass=hass, key=STORAGE_KEY, version=STORAGE_VERSION)
    token_info = await store.async_load()

    oauth = incontrol2.InControl2OAuth(
        config[CONF_CLIENT_ID],
        config[CONF_CLIENT_SECRET],
        config["callback_url"],
        websession,
        store,
    )

    try:
        token_info = await oauth.refresh_access_token(token_info)
    except incontrol2.InControl2OauthError as err:
        _LOGGER.error("Failed to refresh access token")
        token_info = None
        raise ConfigEntryAuthFailed(err) from err

    data_connection = incontrol2.InControl2Connection(
        oauth, token_info=token_info, websession=websession
    )

    if not await incontrol2.InControl2Org.find_orgs(data_connection):
        _LOGGER.error("No orgs found")
        return False

    hass.data[DATA_INCONTROL2] = incontrol2.InControl2Device

    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "binary_sensor")
    )
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "sensor")
    )
    hass.async_create_task(
        hass.config_entries.async_forward_entry_setup(entry, "device_tracker")
    )

    return True
