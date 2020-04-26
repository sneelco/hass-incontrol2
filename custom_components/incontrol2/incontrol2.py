"""Library to handle connection with Ambiclimate API."""
import asyncio
import json
import logging
import time
from datetime import timedelta
from urllib.parse import urlencode
from homeassistant.util import Throttle

import aiohttp
import async_timeout

DEFAULT_TIMEOUT = 10
API_ENDPOINT = 'https://api.ic.peplink.com/rest/'

_LOGGER = logging.getLogger(__name__)
MIN_TIME_BETWEEN_UPDATES = timedelta(minutes=5)


class InControl2OauthError(Exception):
    pass


class InControl2OAuth(object):
    OAUTH_AUTHORIZE_URL = 'https://api.ic.peplink.com/api/oauth2/auth'
    OAUTH_TOKEN_URL = 'https://api.ic.peplink.com/api/oauth2/token'

    def __init__(self, client_id, client_secret, redirect_uri, werbsession):
        """Create a InControl2OAuth object."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.websession = werbsession

    def get_authorize_url(self):
        """Get the URL to use to authorize this app."""
        payload = {'client_id': self.client_id,
                   'response_type': 'code',
                   'redirect_uri': self.redirect_uri}
        return self.OAUTH_AUTHORIZE_URL + '?' + urlencode(payload)

    async def get_access_token(self, code):
        """Get the access token for the app given the code."""
        payload = {'client_id': self.client_id,
                   'redirect_uri': self.redirect_uri,
                   'code': code,
                   'client_secret': self.client_secret,
                   'grant_type': 'authorization_code'}

        try:
            with async_timeout.timeout(DEFAULT_TIMEOUT):
                response = await self.websession.post(self.OAUTH_TOKEN_URL,
                                                      data=payload,
                                                      allow_redirects=True)
                if response.status != 200:
                    raise InControl2OauthError(response.status)
                token_info = await response.json()
                token_info['expires_at'] = int(time.time()) + token_info['expires_in']
                return token_info
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Timeout calling InControl2 to get auth token.")
            return None
        return None

    async def refresh_access_token(self, token_info):
        """Refresh access token."""
        if token_info is None:
            return token_info
        if not is_token_expired(token_info):
            return token_info

        payload = {'client_id': self.client_id,
                   'redirect_uri': self.redirect_uri,
                   'refresh_token': token_info['refresh_token'],
                   'client_secret': self.client_secret,
                   'grant_type': 'refresh_token'}

        refresh_token = token_info.get('refresh_token')

        try:
            with async_timeout.timeout(DEFAULT_TIMEOUT):
                response = await self.websession.post(self.OAUTH_TOKEN_URL,
                                                      data=payload,
                                                      allow_redirects=True)
                if response.status != 200:
                    _LOGGER.error("Failed to refresh access token: %s", response)
                    return None
                token_info = await response.json()
                token_info['expires_at'] = int(time.time()) + token_info['expires_in']
                if 'refresh_token' not in token_info:
                    token_info['refresh_token'] = refresh_token
                return token_info
        except (asyncio.TimeoutError, aiohttp.ClientError):
            _LOGGER.error("Timeout calling InControl2 to get auth token.")
        return None


def is_token_expired(token_info):
    """Check if token is expired."""
    return token_info['expires_at'] - int(time.time()) < 60*60


class InControl2Connection(object):
    def __init__(self, oauth: InControl2OAuth, token_info: dict,
                 timeout=DEFAULT_TIMEOUT,
                 websession=None):
        """Initialize the InControl2 connection."""
        if websession is None:
            async def _create_session():
                return aiohttp.ClientSession()

            loop = asyncio.get_event_loop()
            self.websession = loop.run_until_complete(_create_session())
        else:
            self.websession = websession
        self._timeout = timeout
        self.oauth = oauth
        self.token_info = token_info
        self._vehicles = []
        self._orgs = []

    async def request(self, command, params, retry=3, get=True):
        """Request data."""
        headers = {
            "Accept": "application/json",
            'Authorization': 'Bearer ' + self.token_info.get('access_token')
        }

        url = API_ENDPOINT + command
        try:
            with async_timeout.timeout(self._timeout):
                if get:
                    resp = await self.websession.get(url, headers=headers, params=params)
                else:
                    resp = await self.websession.post(url, headers=headers, json=params)
        except asyncio.TimeoutError:
            if retry < 1:
                _LOGGER.error("Timed out sending command to InControl2: %s", command)
                return None
            return await self.request(command, params, retry - 1, get)
        except aiohttp.ClientError:
            _LOGGER.error("Error sending command to InControl2: %s", command, exc_info=True)
            return None
        if resp.status != 200:
            _LOGGER.error(await resp.text())
            return None
        return await resp.text()

    async def find_orgs(self):
        """Get users InControl2 org information."""
        self._orgs = await InControl2Org.find_orgs(session=self)

        return bool(self._orgs)

    def get_orgs(self):
        """Get users InControl2 device information."""
        return self._orgs

    def get_all_devices(self):
        devices = []

        for org in self.get_orgs():
            for group in org.get_groups():
                devices.extend(group.get_devices())

        return devices

    async def update_all_devices(self):
        devices = self.get_all_devices()
        for device in devices:
            if not await device.update():
                _LOGGER.warning(f"Update failed for {device.name} ({device.device_id}). "
                                f"Likely throttled (min_interval: {MIN_TIME_BETWEEN_UPDATES})")
                continue

            for entity in device.entities:
                entity.async_schedule_update_ha_state(True)


class InControl2Org:
    @classmethod
    async def find_orgs(cls, session: InControl2Connection):
        """Get users InControl2 vehicle information."""
        res = await session.request('o', {})
        if not res:
            return False

        res = json.loads(res)
        orgs = []
        for org in res.get('data', []):
            org_instance = InControl2Org(org.get('id'),
                                         org.get('name'),
                                         org.get('status'),
                                         session)
            await org_instance.find_groups()
            orgs.append(org_instance)

        return orgs

    def __init__(self, org_id: str, name: str, status: str, session: InControl2Connection):
        self._org_id = org_id
        self._name = name
        self._status = status
        self.session = session
        self._groups = []

        _LOGGER.info(f'Found org {name}')

    async def find_groups(self):
        res = await self.session.request('o/{org_id}/g'.format(org_id=self._org_id), {})
        if not res:
            return False
        res = json.loads(res)
        groups = []

        for group in res.get('data', []):
            group_instance = InControl2Group(group.get('id'),
                                             group.get('name'),
                                             group,
                                             self._org_id,
                                             self.session)
            await group_instance.find_devices()
            groups.append(group_instance)

        self._groups = groups

        return bool(self._groups)

    def get_groups(self):
        """Get orgs InControl2 groups."""
        return self._groups


class InControl2Group:
    def __init__(self, group_id: int, name: str, data: dict, org_id: str, session: InControl2Connection):
        self._devices = []
        self._group_id = group_id
        self._name = name
        self._data = data
        self._org_id = org_id
        self.session = session
        self._devices = []

    async def find_devices(self):
        res = await self.session.request(f'o/{self._org_id}/g/{self._group_id}/d', {})
        if not res:
            return False
        res = json.loads(res)
        devices = []

        for device in res.get('data', []):
            device_instance = InControl2Device(device.get('id'),
                                               device,
                                               self._org_id,
                                               self._group_id,
                                               self.session)
            await device_instance.update()
            devices.append(device_instance)

        self._devices = devices

    def get_devices(self):
        return self._devices


class InControl2Device:
    """Instance of InControl2 vehicle."""

    def __init__(self, device_id: int, data: dict, org_id: str, group_id: int, session: InControl2Connection):
        """Initialize the Ambiclimate device class."""
        self._device_id = device_id
        self._data = data
        self._org_id = org_id
        self._group_id = group_id
        self.session = session

        self._location = {}
        self._wans = {}
        self._entities = []

    def add_entity(self, entity: object):
        self._entities.append(entity)

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    async def update(self):
        _LOGGER.info(f'Updating device, {self.name} ({self.device_id})')
        self._data = await self._update_device()
        self._location = await self._update_location()
        self._wans = await self._update_wans()

        return True

    async def _update_device(self):
        res = await self.session.request(f'o/{self._org_id}/g/{self._group_id}/d/{self._device_id}', {})
        if not res:
            return False
        res = json.loads(res)
        return res.get('data', {})

    async def _update_location(self):
        res = await self.session.request(f'o/{self._org_id}/g/{self._group_id}/d/{self._device_id}/loc', {})
        if not res:
            return False
        res = json.loads(res)
        locations = res.get('data', [])
        if bool(locations):
            return {
                'latitude': locations[0].get('la'),
                'longitude': locations[0].get('lo'),
                'altitude': locations[0].get('at'),
                'speed': locations[0].get('sp'),
                'timestamp': locations[0].get('ts'),
            }

        return {}

    async def _update_wans(self):
        res = await self.session.request(f'o/{self._org_id}/g/{self._group_id}/d/{self._device_id}/info/interfaces', {})
        if not res:
            return False
        res = json.loads(res)

        return res.get('data', [])

    @property
    def device_id(self):
        """Return a device ID."""
        return self._device_id

    @property
    def name(self):
        """Return a device name."""
        return self._data.get('name')

    @property
    def location(self):
        """Return a device name."""
        return self._location

    @property
    def wans(self):
        """Return a device name."""
        return self._wans

    @property
    def group_id(self):
        return self._group_id

    @property
    def data(self):
        return self._data

    @property
    def org_id(self):
        """Return a device name."""
        return self._org_id

    @property
    def entities(self):
        """Return a device name."""
        return self._entities

    @property
    def state(self):
        """Return a device name."""
        return self._data.get("status")