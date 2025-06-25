"""Data handling for Neewer Light integration."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self

import aiohttp
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

from .const import (
    CACHE_REFRESH_INTERVAL,
    DOMAIN,
    REMOTE_DB_URL,
    STORAGE_VERSION,
)

_LOGGER = logging.getLogger(__name__)

LIGHTS_DB_FILE = Path(__file__).parent / "lights.db.json"


class NeewerLightData:
    """Manages Neewer light device data and capabilities."""

    _instance: NeewerLightData | None = None
    _lights_db: dict[str, Any] | None = None
    _hass: HomeAssistant
    _store: Store
    _last_refresh: float = 0
    _date_code_map: dict[str, str] | None = None

    def __new__(cls, hass: HomeAssistant) -> Self:
        """Singleton pattern for NeewerLightData."""
        if cls._instance is None:
            instance = super().__new__(cls)
            instance._hass = hass
            instance._store = Store(hass, STORAGE_VERSION, f"{DOMAIN}_database")
            instance._init_date_code_map()
            cls._instance = instance
            # Don't load synchronously in __new__, will be loaded async
        return cls._instance  # type: ignore[return-value]

    def _init_date_code_map(self) -> None:
        """Initialize the date code to project name mapping."""
        self._date_code_map = {
            "20220014": "CB60B",
            "20220015": "SL90",
            "20220016": "RGB660 PRO",
            "20220017": "GL1 PRO",
            "20220018": "MS60C",
            "20220019": "TL60",
            "20220020": "GR18C",
            "20220021": "RGB176-A1",
            "20220022": "GL1C",
            "20220023": "RGB62",
            "20220024": "BH-30S",
            # Add more mappings as discovered
        }

    async def async_ensure_database_loaded(self) -> None:
        """Ensure the database is loaded and up to date."""
        if self._lights_db is None or self._needs_refresh():
            await self._async_refresh_database()

    def _needs_refresh(self) -> bool:
        """Check if database needs refresh."""
        return (time.time() - self._last_refresh) > CACHE_REFRESH_INTERVAL

    async def _async_refresh_database(self) -> None:
        """Refresh the database from remote source with fallback to cache."""
        _LOGGER.debug("Refreshing Neewer lights database")

        # Try to fetch from remote
        remote_db = await self._async_fetch_remote_database()
        if remote_db:
            self._lights_db = remote_db
            self._last_refresh = time.time()
            # Save to cache
            await self._store.async_save(
                {
                    "database": remote_db,
                    "last_refresh": self._last_refresh,
                }
            )
            _LOGGER.info("Successfully updated Neewer lights database from remote")
            return

        # Fallback to cached version
        cached_data = await self._store.async_load()
        if cached_data and cached_data.get("database"):
            self._lights_db = cached_data["database"]
            self._last_refresh = cached_data.get("last_refresh", 0)
            _LOGGER.info("Using cached Neewer lights database")
            return

        # Final fallback to local file
        await self._async_load_local_database()

    async def _async_fetch_remote_database(self) -> dict[str, Any] | None:
        """Fetch database from remote GitHub source."""
        session = async_get_clientsession(self._hass)
        try:
            timeout = aiohttp.ClientTimeout(total=30)
            async with session.get(REMOTE_DB_URL, timeout=timeout) as response:
                if response.status == 200:  # noqa: PLR2004
                    data = await response.json()
                    if self._validate_database(data):
                        return data
                    _LOGGER.warning("Remote database validation failed")
                else:
                    _LOGGER.warning(
                        "Failed to fetch remote database: HTTP %s", response.status
                    )
        except (TimeoutError, aiohttp.ClientError, json.JSONDecodeError) as e:
            _LOGGER.warning("Error fetching remote database: %s", e)
        return None

    async def _async_load_local_database(self) -> None:
        """Load the lights database from the local file as final fallback."""
        try:
            with LIGHTS_DB_FILE.open(encoding="utf-8") as f:
                data = json.load(f)
                if self._validate_database(data):
                    self._lights_db = data
                    _LOGGER.info("Loaded lights database from local file")
                else:
                    _LOGGER.error("Local database validation failed")
                    self._lights_db = {"version": 2, "lights": []}
        except FileNotFoundError:
            _LOGGER.exception("Lights database file not found: %s", LIGHTS_DB_FILE)
            self._lights_db = {"version": 2, "lights": []}
        except json.JSONDecodeError:
            _LOGGER.exception("Error decoding lights database JSON")
            self._lights_db = {"version": 2, "lights": []}

    def _validate_database(self, data: dict[str, Any]) -> bool:
        """Validate database structure."""
        if not isinstance(data, dict):
            return False
        if "lights" not in data or not isinstance(data["lights"], list):
            return False
        # Basic validation - check that lights have required fields
        for light in data["lights"]:
            if not isinstance(light, dict) or "type" not in light:
                return False
        return True

    @staticmethod
    def is_neewer_light(device_name: str) -> bool:
        """Check if a device name indicates a Neewer light."""
        name_lower = device_name.lower()
        return any(
            keyword in name_lower for keyword in ["nwr", "neewer", "sl", "nee"]
        ) or name_lower.startswith(("nw-", "neewer-"))

    async def async_get_light_capabilities(
        self, device_name: str, device_identifier: str = ""
    ) -> dict[str, Any] | None:
        """Get capabilities for a Neewer light based on its name."""
        await self.async_ensure_database_loaded()

        if not self._lights_db:
            _LOGGER.error("No lights database available")
            return None

        project_name = self._parse_project_name(device_name)
        if not project_name:
            _LOGGER.warning("Could not parse project name from device: %s", device_name)
            return None

        light_type_id = self._map_project_name_to_light_type(project_name)
        if light_type_id is None:
            _LOGGER.warning(
                "Could not map project name '%s' to light type ID", project_name
            )
            return None

        for light in self._lights_db.get("lights", []):
            if light.get("type") == light_type_id:
                # Add computed fields
                enhanced_capabilities = light.copy()
                enhanced_capabilities["model"] = project_name
                enhanced_capabilities["nick_name"] = self._construct_nick_name(
                    project_name, device_identifier
                )
                return enhanced_capabilities

        _LOGGER.warning("No capabilities found for light type ID: %s", light_type_id)
        return None

    def get_light_capabilities(
        self,
        device_name: str,
        device_identifier: str = "",  # noqa: ARG002
    ) -> dict[str, Any] | None:
        """Get light capabilities for backward compatibility."""
        # This is a temporary wrapper - all callers should migrate to async version
        _LOGGER.warning(
            "Using deprecated synchronous get_light_capabilities for %s", device_name
        )
        return None

    def _construct_nick_name(self, project_name: str, device_identifier: str) -> str:
        """Construct nick name as project_name + last 6 chars of identifier."""
        min_identifier_len = 6
        if len(device_identifier) >= min_identifier_len:
            last_6_chars = device_identifier[-6:].replace(":", "").upper()
            return f"{project_name}-{last_6_chars}"
        return project_name

    def _parse_project_name(self, device_name: str) -> str | None:
        """Parse the project name from the device name."""
        name_lower = device_name.lower()

        # "NWR" prefix: Drop first 4 characters
        if name_lower.startswith("nwr-"):
            return device_name[4:]

        # "NEEWER" prefix: Drop first 7 characters
        if name_lower.startswith("neewer-"):
            return device_name[7:]

        # "NW-YYYYMMDD&XXXXXXXX" format: Extract date code, lookup in mapping table
        min_device_name_len = 20
        if (
            name_lower.startswith("nw-")
            and len(device_name) >= min_device_name_len
            and "&" in device_name
            and self._date_code_map
        ):
            date_part = device_name[3:11]  # Extract YYYYMMDD
            if date_part in self._date_code_map:
                return self._date_code_map[date_part]

        # "NW-" prefix: Drop first 3 characters
        if name_lower.startswith("nw-"):
            return device_name[3:]

        # Fallback for other formats, use full name
        return device_name

    def _map_project_name_to_light_type(self, project_name: str) -> int | None:  # noqa: C901, PLR0911, PLR0912
        """Map project name to a numeric Light Type ID."""
        project_name_lower = project_name.lower()

        # Comprehensive pattern matching - most specific first
        if "cb60 rgb" in project_name_lower:
            return 22
        if "sl90 pro" in project_name_lower:
            return 34
        if "sl90" in project_name_lower and "pro" not in project_name_lower:
            return 14
        if "rgb660 pro" in project_name_lower:
            return 3
        if "gl1 pro" in project_name_lower:
            return 33
        if "gl1c" in project_name_lower:
            return 39
        if "ms60c" in project_name_lower:
            return 25
        if "rgb62" in project_name_lower:
            return 40
        if "bh-30s" in project_name_lower:
            return 42
        if "tl60" in project_name_lower:
            return 32
        if "gr18c" in project_name_lower:
            return 62
        if "rgb176-a1" in project_name_lower:
            return 5
        if "rgb176" in project_name_lower:
            return 20
        if "cb60b" in project_name_lower:
            return 22
        if "cb60" in project_name_lower:
            return 15
        if "rgb1" in project_name_lower:
            return 8
        if "660 pro" in project_name_lower:
            return 3
        if "480 pro" in project_name_lower:
            return 2
        if "530 pro" in project_name_lower:
            return 1
        if "gl1" in project_name_lower and "pro" not in project_name_lower:
            return 26
        if "tl-60" in project_name_lower:
            return 32
        if "ms150" in project_name_lower:
            return 41
        if "rgb168" in project_name_lower:
            return 6
        if "fs150" in project_name_lower:
            return 30
        if "sl80" in project_name_lower:
            return 35
        if "sl60" in project_name_lower:
            return 36
        if "sl140" in project_name_lower:
            return 37
        if "sl200" in project_name_lower:
            return 38

        # Fallback - try to parse as direct type ID
        try:
            return int(project_name)
        except ValueError:
            pass

        # Pattern-based fallbacks
        if "rgb" in project_name_lower and "660" in project_name_lower:
            return 3
        if "rgb" in project_name_lower and "530" in project_name_lower:
            return 1
        if "rgb" in project_name_lower and "480" in project_name_lower:
            return 2

        return None
