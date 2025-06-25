"""Config flow for Neewer Light integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.bluetooth import (
    BluetoothServiceInfoBleak,
    async_discovered_service_info,
)
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN
from .data import NeewerLightData

_LOGGER = logging.getLogger(__name__)


class NeewerLightConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Neewer Light."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._discovered_device: BluetoothServiceInfoBleak | None = None

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle the bluetooth discovery step."""
        _LOGGER.debug(
            "[BLUETOOTH DISCOVERY] Device found - Name: %s, Address: %s, Connectable: %s",
            discovery_info.name,
            discovery_info.address,
            discovery_info.connectable,
        )
        _LOGGER.debug(
            "[BLUETOOTH DISCOVERY] Device details - RSSI: %s, Service UUIDs: %s, Manufacturer data: %s",
            discovery_info.rssi,
            discovery_info.service_uuids,
            discovery_info.manufacturer_data,
        )

        await self.async_set_unique_id(discovery_info.address)
        _LOGGER.debug(
            "[BLUETOOTH DISCOVERY] Set unique_id to: %s", discovery_info.address
        )
        self._abort_if_unique_id_configured()
        _LOGGER.debug(
            "[BLUETOOTH DISCOVERY] Unique ID check passed, device not already configured"
        )

        # Check if the device is a Neewer light based on its name
        is_neewer = NeewerLightData.is_neewer_light(discovery_info.name)
        _LOGGER.debug(
            "[BLUETOOTH DISCOVERY] Device name check - Name: '%s', Is Neewer: %s",
            discovery_info.name,
            is_neewer,
        )
        if not is_neewer:
            _LOGGER.debug(
                "[BLUETOOTH DISCOVERY] Aborting - device name doesn't match Neewer patterns"
            )
            return self.async_abort(reason="not_neewer_light")

        self._discovered_device = discovery_info
        _LOGGER.debug(
            "[BLUETOOTH DISCOVERY] Device validated, proceeding to confirmation step"
        )
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""
        _LOGGER.debug(
            "[BLUETOOTH CONFIRM] Called with user_input: %s, discovered_device: %s",
            user_input is not None,
            self._discovered_device.name if self._discovered_device else None,
        )
        if user_input is not None:
            # Ensure _discovered_device is not None before creating entry
            assert self._discovered_device is not None
            _LOGGER.debug(
                "[BLUETOOTH CONFIRM] Creating config entry - Title: %s, Address: %s",
                self._discovered_device.name,
                self._discovered_device.address,
            )
            entry = self.async_create_entry(
                title=self._discovered_device.name,
                data={"address": self._discovered_device.address},
            )
            _LOGGER.debug("[BLUETOOTH CONFIRM] Config entry created successfully")
            return entry

        assert self._discovered_device is not None
        self._set_confirm_only()
        _LOGGER.debug(
            "[BLUETOOTH CONFIRM] Showing confirmation form for device: %s (%s)",
            self._discovered_device.name,
            self._discovered_device.address,
        )
        return self.async_show_form(
            step_id="bluetooth_confirm",
            description_placeholders={
                "name": self._discovered_device.name,
                "address": self._discovered_device.address,
            },
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the user step to start discovery."""
        _LOGGER.debug(
            "[USER DISCOVERY] Manual discovery started, user_input: %s",
            user_input is not None,
        )
        # This step is primarily for manual configuration, but for Bluetooth
        # integrations, we mostly rely on auto-discovery.
        # We can use this to list discovered devices if needed.
        if user_input is not None:
            _LOGGER.debug(
                "[USER DISCOVERY] User input received, proceeding with discovery"
            )
            # No user input needed for discovery

        # Attempt to discover devices if not already discovered via bluetooth_confirm
        current_addresses = self._async_current_ids()
        _LOGGER.debug(
            "[USER DISCOVERY] Current configured addresses: %s", current_addresses
        )

        discovered_devices = list(
            async_discovered_service_info(self.hass, connectable=False)
        )
        _LOGGER.debug(
            "[USER DISCOVERY] Found %d total Bluetooth devices", len(discovered_devices)
        )

        for discovery_info in discovered_devices:
            _LOGGER.debug(
                "[USER DISCOVERY] Checking device - Name: '%s', Address: %s, Already configured: %s",
                discovery_info.name,
                discovery_info.address,
                discovery_info.address in current_addresses,
            )

            if discovery_info.address not in current_addresses:
                is_neewer = NeewerLightData.is_neewer_light(discovery_info.name)
                _LOGGER.debug(
                    "[USER DISCOVERY] Device name check - Name: '%s', Is Neewer: %s",
                    discovery_info.name,
                    is_neewer,
                )

                if is_neewer:
                    _LOGGER.debug(
                        "[USER DISCOVERY] Found suitable Neewer device, setting up config"
                    )
                    await self.async_set_unique_id(discovery_info.address)
                    _LOGGER.debug(
                        "[USER DISCOVERY] Set unique_id to: %s", discovery_info.address
                    )
                    self._abort_if_unique_id_configured()
                    _LOGGER.debug("[USER DISCOVERY] Unique ID check passed")
                    self._discovered_device = discovery_info
                    _LOGGER.debug("[USER DISCOVERY] Proceeding to confirmation step")
                    return await self.async_step_bluetooth_confirm()

        # If no device is discovered, show a form indicating that.
        # If a device was discovered and confirmed, this step won't be reached.
        _LOGGER.debug("[USER DISCOVERY] No suitable Neewer devices found")
        return self.async_show_form(
            step_id="user",
            description_placeholders={"message": "No Neewer lights discovered yet."},
        )
