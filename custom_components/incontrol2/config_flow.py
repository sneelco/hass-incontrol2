"""Config flow for InControl2."""
import logging

from .incontrol2 import InControl2OAuth, InControl2OauthError

import voluptuous as vol
from aiohttp.web import Response, HTTPBadRequest, Request
from homeassistant import config_entries
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.storage import Store
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import get_url

from typing import Mapping, Any

from .const import (
    AUTH_CALLBACK_NAME,
    AUTH_CALLBACK_PATH,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
    INCONTROL_URL
)

DATA_INCONTROL2_IMPL = "incontrol2_flow_implementation"

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register("incontrol2")
class Incontrol2FlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize flow."""
        self._registered_view = False
        self._oauth = None
        self.data_schema = {
            vol.Required(CONF_CLIENT_ID): str,
            vol.Required(CONF_CLIENT_SECRET): str,
        }

    async def async_step_user(self, user_input=None) -> dict:
        """Handle external yaml configuration."""
        if self.hass.config_entries.async_entries(DOMAIN):
            return self.async_abort(reason="already_setup")

        if not user_input:
            cb_url = self._cb_url()
            return self.async_show_form(
                step_id="user",
                description_placeholders={
                    "incontrol_url": INCONTROL_URL,
                    "cb_url": cb_url
                },
                data_schema=vol.Schema(self.data_schema),
            )

        self.hass.data[DATA_INCONTROL2_IMPL] = user_input

        return await self.async_step_auth()

    async def async_step_auth(self, user_input=None) -> dict:
        """Handle a flow start."""

        config = self.hass.data[DATA_INCONTROL2_IMPL]

        if self.hass.config_entries.async_entries(DOMAIN):
            return self.async_abort(reason="already_setup")

        errors = {}

        if "code" in config:
            return await self.async_step_code(config["code"])

        if user_input is not None:
            errors["base"] = "follow_link"

        if not self._registered_view:
            self._generate_view()

        auth_url = await self._get_authorize_url()
        cb_url = self._cb_url()

        return self.async_show_form(
            step_id="auth",
            description_placeholders={
                "authorization_url": auth_url,
                "cb_url": cb_url,
            },
            errors=errors,
        )

    async def async_step_code(self, code: str = None) -> dict:
        """Received code for authentication."""

        try:
            await self._get_token_info(code)
        except InControl2OauthError:
            return self.async_abort(reason="access_token")

        config = self.hass.data[DATA_INCONTROL2_IMPL].copy()
        config["callback_url"] = self._cb_url()

        id = config.get(CONF_CLIENT_ID)[-5:]
        unique_id = f"InControl2-{id}"
        await self.async_set_unique_id(unique_id)

        self._abort_if_unique_id_configured(error="already_configured_account")

        return self.async_create_entry(title=unique_id, data=config)

    async def _get_token_info(self, code: str) -> dict:
        oauth = self._generate_oauth()
        token_info = await oauth.get_access_token(code)

        return token_info

    def _generate_view(self) -> None:
        self.hass.http.register_view(Incontrol2AuthCallbackView())
        self._registered_view = True

    def _generate_oauth(self) -> InControl2OAuth:
        config = self.hass.data[DATA_INCONTROL2_IMPL]
        clientsession = async_get_clientsession(self.hass)
        callback_url = self._cb_url()
        store = Store(hass=self.hass, key=STORAGE_KEY, version=STORAGE_VERSION)

        oauth = InControl2OAuth(
            config.get(CONF_CLIENT_ID),
            config.get(CONF_CLIENT_SECRET),
            callback_url,
            clientsession,
            store,
        )
        return oauth

    def _cb_url(self) -> str:
        return f"{get_url(self.hass)}{AUTH_CALLBACK_PATH}"

    async def _get_authorize_url(self) -> str:
        oauth = self._generate_oauth()
        return oauth.get_authorize_url()

    """Config flow to handle re-authentication."""

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ):
        """Perform reauth upon an API authentication error."""
        # Clear old code
        if DATA_INCONTROL2_IMPL not in self.hass.data or self.hass.data[DATA_INCONTROL2_IMPL] is None:
            if entry_data is not None:
                if "code" in entry_data:
                    del entry_data["code"]

                self.hass.data[DATA_INCONTROL2_IMPL] = entry_data
            else:
                self.hass.data[DATA_INCONTROL2_IMPL] = {}

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ):
        """Dialog that informs the user that reauth is required."""

        config = self.hass.data[DATA_INCONTROL2_IMPL]

        errors = {}

        if "code" in config:
            return await self.async_step_reauth_code(config["code"])

        if user_input is not None:
            errors["base"] = "follow_link"

        if not self._registered_view:
            self._generate_view()

        auth_url = await self._get_authorize_url()
        cb_url = self._cb_url()

        return self.async_show_form(
            step_id="reauth",
            description_placeholders={
                "authorization_url": auth_url,
                "cb_url": cb_url,
            },
            errors=errors,
        )

    async def async_step_reauth_code(self, code: str = None) -> dict:
        """Received code for authentication."""

        try:
            await self._get_token_info(code)
        except InControl2OauthError:
            return self.async_abort(reason="access_token")

        config = self.hass.data[DATA_INCONTROL2_IMPL].copy()
        config["callback_url"] = self._cb_url()

        id = config.get(CONF_CLIENT_ID)[-5:]
        unique_id = f"InControl2-{id}"

        entry = await self.async_set_unique_id(unique_id)

        self.hass.config_entries.async_update_entry(entry=entry, data=config)

        return self.async_abort(reason="reauth_successful")


class Incontrol2AuthCallbackView(HomeAssistantView):
    """Incontrol2 Authorization Callback View."""

    requires_auth = False
    url = AUTH_CALLBACK_PATH
    name = AUTH_CALLBACK_NAME

    @staticmethod
    async def get(request: Request) -> Response:
        """Receive authorization token."""
        code = request.query.get("code")
        if code is None:
            return Response(text="No code was provided", status=HTTPBadRequest.status_code)

        hass = request.app["hass"]
        hass.data[DATA_INCONTROL2_IMPL]["code"] = code

        return Response(text="Authentication was successful. You can close this window.")
