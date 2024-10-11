"""Constants used by the InControl2 component."""

CONF_CLIENT_ID = "client_id"
CONF_CLIENT_SECRET = "client_secret"
CONF_SCAN_INTERVAL = "scan_interval"
DOMAIN = "incontrol2"
STORAGE_KEY = "incontrol2_auth"
STORAGE_VERSION = 1
DATA_INCONTROL2 = "incontrol2"

PEPLINK = "PepLink"
SIGNAL_UNITS = "dB"

AUTH_CALLBACK_NAME = "api:incontrol2"
AUTH_CALLBACK_PATH = "/api/incontrol2"
INCONTROL_URL = "https://incontrol2.peplink.com/"


class IncontrolIcons(object):
    ETHERNET_CONNECTED = "mdi:ethernet"
    ETHERNET_DISCONNECTED = "mdi:ethernet-off"
    WIFI_CONNECTED = "mdi:wifi-strength-outline"
    WIFI_DISCONNECTED = "mdi:wifi-strength-off-outline"
    WIFI_STRENGTH = [
        'mdi:wifi-strength-off-outline',
        'mdi:wifi-strength-outline',
        'mdi:wifi-strength-1',
        'mdi:wifi-strength-2',
        'mdi:wifi-strength-3',
        'mdi:wifi-strength-4'
    ]
    CELLULAR_CONNECTED = "mdi:network-strength-outline"
    CELLULAR_DISCONNECTED = "mdi:network-strength-off-outline"
    CELLULAR_STRENGTH = [
        'mdi:network-strength-off-outline',
        'mdi:network-strength-outline',
        'mdi:network-strength-1',
        'mdi:network-strength-2',
        'mdi:network-strength-3',
        'mdi:network-strength-4',
    ]
    SIGNAL_DEFAULT = "mdi:wifi-strength-alert-outline"
