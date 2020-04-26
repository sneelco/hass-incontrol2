"""Config flow for InControl2."""
import logging

from .incontrol2 import InControl2OAuth, InControl2OauthError

import voluptuous as vol
from aiohttp.web import Response, HTTPBadRequest, Request
from homeassistant import config_entries
from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    AUTH_CALLBACK_NAME,
    AUTH_CALLBACK_PATH,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
)

DATA_INCONTROL2_IMPL = "incontrol2_flow_implementation"

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register("incontrol2")
class Incontrol2FlowHandler(config_entries.ConfigFlow):
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
            return self.async_show_form(
                step_id="user",
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

        return self.async_show_form(
            step_id="auth",
            description_placeholders={
                "authorization_url": await self._get_authorize_url(),
                "cb_url": self._cb_url(),
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

        return self.async_create_entry(title="InControl2", data=config)

    async def _get_token_info(self, code: str) -> dict:
        oauth = self._generate_oauth()
        token_info = await oauth.get_access_token(code)

        store = self.hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)
        await store.async_save(token_info)

        return token_info

    def _generate_view(self) -> None:
        self.hass.http.register_view(Incontrol2AuthCallbackView())
        self._registered_view = True

    def _generate_oauth(self) -> InControl2OAuth:
        config = self.hass.data[DATA_INCONTROL2_IMPL]
        clientsession = async_get_clientsession(self.hass)
        callback_url = self._cb_url()

        oauth = InControl2OAuth(
            config.get(CONF_CLIENT_ID),
            config.get(CONF_CLIENT_SECRET),
            callback_url,
            clientsession,
        )
        return oauth

    def _cb_url(self) -> str:
        return f"{self.hass.config.api.base_url}{AUTH_CALLBACK_PATH}"

    async def _get_authorize_url(self) -> str:
        oauth = self._generate_oauth()
        return oauth.get_authorize_url()


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
