"""Constants for custom_components/neewer."""

from logging import Logger, getLogger

LOGGER: Logger = getLogger(__package__)

DOMAIN = "neewer"

# Bluetooth Protocol Constants
SERVICE_UUID = "69400001-B5A3-F393-E0A9-E50E24DCCA99"
CONTROL_CHARACTERISTIC_UUID = "69400002-B5A3-F393-E0A9-E50E24DCCA99"
NOTIFY_CHARACTERISTIC_UUID = "69400003-B5A3-F393-E0A9-E50E24DCCA99"

PREFIX = 0x78
COMMAND_DELAY_MS = 15
MIN_NOTIFICATION_LENGTH = 4
NOTIFICATION_CHANNEL_TAG = 0x01

# Database Constants
REMOTE_DB_URL = "https://raw.githubusercontent.com/keefo/NeewerLite/main/Database/lights.json"
CACHE_REFRESH_INTERVAL = 28800  # 8 hours in seconds
STORAGE_VERSION = 1
