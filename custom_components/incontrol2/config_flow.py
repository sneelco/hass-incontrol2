"""Config flow for InControl2."""
import logging

from . import incontrol2

from homeassistant import config_entries
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import callback
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


@callback
def register_flow_implementation(hass, client_id, client_secret):
    """Register a incontrol2 implementation.

    client_id: Client id.
    client_secret: Client secret.
    """
    hass.data.setdefault(DATA_INCONTROL2_IMPL, {})

    hass.data[DATA_INCONTROL2_IMPL] = {
        CONF_CLIENT_ID: client_id,
        CONF_CLIENT_SECRET: client_secret,
    }


@config_entries.HANDLERS.register("incontrol2")
class Incontrol2FlowHandler(config_entries.ConfigFlow):
    """Handle a config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    def __init__(self):
        """Initialize flow."""
        self._registered_view = False
        self._oauth = None

    async def async_step_user(self, user_input=None):
        """Handle external yaml configuration."""
        if self.hass.config_entries.async_entries(DOMAIN):
            return self.async_abort(reason="already_setup")

        config = self.hass.data.get(DATA_INCONTROL2_IMPL, {})

        if not config:
            _LOGGER.debug("No config")
            return self.async_abort(reason="no_config")

        return await self.async_step_auth()

    async def async_step_auth(self, user_input=None):
        """Handle a flow start."""
        if self.hass.config_entries.async_entries(DOMAIN):
            return self.async_abort(reason="already_setup")

        errors = {}

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

    async def async_step_code(self, code=None):
        """Received code for authentication."""
        if self.hass.config_entries.async_entries(DOMAIN):
            return self.async_abort(reason="already_setup")

        token_info = await self._get_token_info(code)

        if token_info is None:
            return self.async_abort(reason="access_token")

        errors = {}

        return self.async_show_form(
            step_id="list_org",
            description_placeholders={
                "orgs": [{"org_id": "asd", "name": "My Org"}],
            },
            errors=errors,
        )

    async def async_select_org(seld, org_id):

        config = self.hass.data[DATA_INCONTROL2_IMPL].copy()
        config["callback_url"] = self._cb_url()

        return self.async_create_entry(title="InControl2", data=config)

    async def _get_token_info(self, code):
        oauth = self._generate_oauth()
        try:
            token_info = await oauth.get_access_token(code)
        except incontrol2.InControl2OauthError:
            _LOGGER.error("Failed to get access token", exc_info=True)
            return None

        store = self.hass.helpers.storage.Store(STORAGE_VERSION, STORAGE_KEY)
        await store.async_save(token_info)

        return token_info

    def _generate_view(self):
        self.hass.http.register_view(Incontrol2AuthCallbackView())
        self._registered_view = True

    def _generate_oauth(self):
        config = self.hass.data[DATA_INCONTROL2_IMPL]
        clientsession = async_get_clientsession(self.hass)
        callback_url = self._cb_url()

        oauth = incontrol2.InControl2OAuth(
            config.get(CONF_CLIENT_ID),
            config.get(CONF_CLIENT_SECRET),
            callback_url,
            clientsession,
        )
        return oauth

    def _cb_url(self):
        return f"{self.hass.config.api.base_url}{AUTH_CALLBACK_PATH}"

    async def _get_authorize_url(self):
        oauth = self._generate_oauth()
        return oauth.get_authorize_url()


class Incontrol2AuthCallbackView(HomeAssistantView):
    """Incontrol2 Authorization Callback View."""

    requires_auth = False
    url = AUTH_CALLBACK_PATH
    name = AUTH_CALLBACK_NAME

    async def get(self, request):
        """Receive authorization token."""
        code = request.query.get("code")
        if code is None:
            return "No code"
        hass = request.app["hass"]
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN, context={"source": "code"}, data=code
            )
        )
        return "OK!"
