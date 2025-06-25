"""DataUpdateCoordinator for Neewer Light integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.active_update_coordinator import (
    ActiveBluetoothDataUpdateCoordinator,
)
from homeassistant.core import CoreState, HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import UpdateFailed

from .const import DOMAIN
from .neewer_device import NeewerConnectionError, NeewerDevice

_LOGGER = logging.getLogger(__name__)


class NeewerDataUpdateCoordinator(ActiveBluetoothDataUpdateCoordinator[dict[str, Any]]):
    """Coordinator for Neewer Light."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        ble_device: bluetooth.BLEDevice,
        address: str,
        capabilities: dict[str, Any],
    ) -> None:
        """Initialize coordinator."""
        self._address = address
        self._capabilities = capabilities
        self.device = NeewerDevice(
            ble_device, capabilities, disconnect_callback=self._on_device_disconnect
        )

        super().__init__(
            hass=hass,
            logger=logger,
            mode=bluetooth.BluetoothScanningMode.ACTIVE,
            address=self._address,
            needs_poll_method=self._needs_poll,
            poll_method=self._async_poll_device,
            # We will take advertisements from non-connectable devices
            # since we will trade the BLEDevice for a connectable one
            # if we need to poll it
            connectable=False,
        )

        self.device_info = DeviceInfo(
            identifiers={(DOMAIN, address)},
            name=self.device.name,
            manufacturer="Neewer",
            model=capabilities.get("model", "Unknown"),
            sw_version=capabilities.get("version", "Unknown"),
        )

        # Add notification callback to trigger state updates
        self.device.add_notification_callback(self._on_notification)

    @callback
    def _needs_poll(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        _seconds_since_last_poll: float | None,
    ) -> bool:
        """Determine if a poll is needed."""
        # Only poll if HA is running, device is not connected, and we have a connectable device
        return (
            self.hass.state == CoreState.running
            and not self.device.is_connected
            and bool(
                bluetooth.async_ble_device_from_address(
                    self.hass, service_info.device.address, connectable=True
                )
            )
        )

    async def _async_poll_device(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> dict[str, Any]:
        """Poll the device to update state."""
        _LOGGER.debug("Polling Neewer device %s", self.device.name)

        # Get connectable device for active connection
        if service_info.connectable:
            connectable_device = service_info.device
        elif device := bluetooth.async_ble_device_from_address(
            self.hass, service_info.device.address, connectable=True
        ):
            connectable_device = device
        else:
            address = service_info.device.address
            msg = f"No connectable device found for {address}"
            raise UpdateFailed(msg)

        # Update device's BLE device reference
        self.device.set_ble_device(connectable_device)

        # Connect if not connected
        if not self.device.is_connected:
            try:
                await self.device.connect()
            except NeewerConnectionError as err:
                msg = f"Failed to connect: {err}"
                _LOGGER.warning(msg)
                raise UpdateFailed(msg) from err

        # Return current device state
        return {
            "is_on": self.device.is_on,
            "brightness": self.device.brightness,
            "cct": self.device.cct,
            "hue": self.device.hue,
            "saturation": self.device.saturation,
            "effect": self.device.effect,
            "gm": self.device.gm,
        }

    @callback
    def _on_notification(self, data: bytes) -> None:
        """Handle device notification."""
        _LOGGER.debug("Device notification received: %s", data.hex())
        # Trigger coordinator update when we receive notifications
        self.async_update_listeners()

    @callback
    def _on_device_disconnect(self, ble_device: bluetooth.BLEDevice) -> None:
        """Handle device disconnect."""
        _LOGGER.warning("Device %s disconnected", ble_device.name or ble_device.address)
        # Trigger a refresh to attempt reconnection
        self.async_update_listeners()

    @callback
    def _async_handle_bluetooth_event(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        _change: bluetooth.BluetoothChange,
    ) -> None:
        """Handle a Bluetooth event."""
        # Update the device's BLE device reference if it changed
        if service_info.address == self.device.address:
            if self.device.ble_device != service_info.device:
                self.device.set_ble_device(service_info.device)

            # Trigger updates when we see advertisements
            self.async_update_listeners()

    async def async_shutdown(self) -> None:
        """Shutdown the coordinator."""
        if self.device:
            await self.device.disconnect()
