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
        _LOGGER.debug("Discovered Bluetooth device: %s", discovery_info)
        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        # Check if the device is a Neewer light based on its name
        if not NeewerLightData.is_neewer_light(discovery_info.name):
            return self.async_abort(reason="not_neewer_light")

        self._discovered_device = discovery_info
        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm discovery."""
        if user_input is not None:
            # Ensure _discovered_device is not None before creating entry
            assert self._discovered_device is not None
            return self.async_create_entry(
                title=self._discovered_device.name,
                data={"address": self._discovered_device.address},
            )

        assert self._discovered_device is not None
        self._set_confirm_only()
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
        # This step is primarily for manual configuration, but for Bluetooth
        # integrations, we mostly rely on auto-discovery.
        # We can use this to list discovered devices if needed.
        if user_input is not None:
            pass  # No user input needed for discovery

        # Attempt to discover devices if not already discovered via bluetooth_confirm
        current_addresses = self._async_current_ids()
        for discovery_info in async_discovered_service_info(
            self.hass, connectable=False
        ):
            if (
                discovery_info.address not in current_addresses
                and NeewerLightData.is_neewer_light(discovery_info.name)
            ):
                self._discovered_device = discovery_info
                return await self.async_step_bluetooth_confirm()

        # If no device is discovered, show a form indicating that.
        # If a device was discovered and confirmed, this step won't be reached.
        return self.async_show_form(
            step_id="user",
            description_placeholders={"message": "No Neewer lights discovered yet."},
        )
