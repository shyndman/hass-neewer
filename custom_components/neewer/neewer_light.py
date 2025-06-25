"""Bluetooth LE communication for Neewer lights."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from bleak import BleakClient
from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWith  # type: ignore[attr-defined]

from .const import (
    COMMAND_DELAY_MS,
    CONTROL_CHARACTERISTIC_UUID,
    MIN_NOTIFICATION_LENGTH,
    NOTIFICATION_CHANNEL_TAG,
    NOTIFY_CHARACTERISTIC_UUID,
    PREFIX,
    SERVICE_UUID,
)

_LOGGER = logging.getLogger(__name__)


class NeewerLightError(Exception):
    """Base exception for Neewer light communication."""


class NeewerLightConnectionError(NeewerLightError):
    """Exception for connection errors."""


class NeewerLightCommandError(NeewerLightError):
    """Exception for command errors."""


class NeewerLight:
    """Represents a single Neewer light and handles its BLE communication."""

    def __init__(
        self,
        ble_device: BLEDevice,
        address: str,
        capabilities: dict[str, Any],
    ) -> None:
        """Initialize the Neewer light."""
        self._ble_device = ble_device
        self._address = address
        self._capabilities = capabilities
        self._client: BleakClient | None = None
        self._is_on: bool = False
        self._brightness: int = 0
        self._cct: int = 0
        self._hue: int = 0
        self._saturation: int = 0
        self._effect: int = 0
        self._last_command_time: float = 0.0

    @property
    def is_connected(self) -> bool:
        """Return true if the light is connected."""
        return self._client is not None and self._client.is_connected

    @property
    def address(self) -> str:
        """Return the Bluetooth address of the device."""
        return self._address

    @property
    def name(self) -> str:
        """Return the name of the device."""
        return self._ble_device.name or self._ble_device.address

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return self._is_on

    @property
    def brightness(self) -> int:
        """Return the brightness of the light (0-100)."""
        return self._brightness

    @property
    def cct(self) -> int:
        """Return the color temperature of the light."""
        return self._cct

    @property
    def hue(self) -> int:
        """Return the hue of the light."""
        return self._hue

    @property
    def saturation(self) -> int:
        """Return the saturation of the light."""
        return self._saturation

    @property
    def effect(self) -> int:
        """Return the current effect ID."""
        return self._effect

    @property
    def capabilities(self) -> dict[str, Any]:
        """Return the capabilities of the light."""
        return self._capabilities

    async def connect(self) -> None:
        """Connect to the Neewer light."""
        try:
            self._client = await BleakClientWith(
                self._ble_device,
                disconnected_callback=self._on_disconnect,
                services=[SERVICE_UUID],
            )
            _LOGGER.debug("Connected to %s", self.name)
            await self._client.start_notify(
                NOTIFY_CHARACTERISTIC_UUID, self._notification_handler
            )
            # Send initial read request to get current state
            await self._send_command([0x84, 0x00])
        except BleakError as err:
            msg = f"Failed to connect to {self.name}: {err}"
            raise NeewerLightConnectionError(msg) from err

    async def disconnect(self) -> None:
        """Disconnect from the Neewer light."""
        if self._client and self._client.is_connected:
            await self._client.stop_notify(NOTIFY_CHARACTERISTIC_UUID)
            await self._client.disconnect()
            _LOGGER.debug("Disconnected from %s", self.name)
        self._client = None

    def _on_disconnect(self, _client: BleakClient) -> None:
        """Handle Bluetooth disconnect."""
        _LOGGER.warning("Disconnected from %s", self.name)
        # Implement re-connection logic in coordinator

    def _notification_handler(
        self, _characteristic: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        """Handle incoming notifications from the light."""
        _LOGGER.debug("Notification from %s: %s", self.name, data.hex())
        if len(data) >= MIN_NOTIFICATION_LENGTH and data[0] == PREFIX and data[1] == NOTIFICATION_CHANNEL_TAG:
            # Channel update notification: [0x78, 0x01, 0x01, CHANNEL, CHECKSUM]
            channel = data[3]
            checksum = self._calculate_checksum(data[0:3])
            if checksum == data[-1]:
                self._effect = channel
                _LOGGER.debug("Light %s channel updated to: %s", self.name, channel)
            else:
                _LOGGER.warning(
                    "Checksum mismatch in notification for %s. Expected %s, got %s",
                    self.name,
                    checksum,
                    data[-1],
                )
        # Add more notification parsing as needed for state updates

    async def _send_command(self, data: list[int]) -> None:
        """Send a command to the light, respecting timing."""
        current_time = asyncio.get_event_loop().time()
        time_since_last_command = (current_time - self._last_command_time) * 1000
        if time_since_last_command < COMMAND_DELAY_MS:
            await asyncio.sleep((COMMAND_DELAY_MS - time_since_last_command) / 1000)

        full_command = [PREFIX, *data]
        checksum = self._calculate_checksum(full_command)
        full_command.append(checksum)

        _LOGGER.debug("Sending command to %s: %s", self.name, bytes(full_command).hex())

        if not self.is_connected:
            msg = f"Not connected to {self.name}"
            raise NeewerLightConnectionError(msg)

        try:
            await self._client.write_gatt_char(
                CONTROL_CHARACTERISTIC_UUID, bytes(full_command), response=True
            )
            self._last_command_time = asyncio.get_event_loop().time()
        except BleakError as err:
            msg = f"Failed to send command to {self.name}: {err}"
            raise NeewerLightCommandError(msg) from err

    def _calculate_checksum(self, data: bytes | bytearray | list[int]) -> int:
        """Calculate the checksum for a command."""
        return sum(data) & 0xFF

    async def async_turn_on(self) -> None:
        """Turn the light on."""
        if self.capabilities.get("newPowerLightCommand") and self._ble_device.address:
            mac_bytes = bytes.fromhex(self._ble_device.address.replace(":", ""))
            command = [0x8D, 0x08, *list(mac_bytes), 0x81, 0x01]
        else:
            command = [0x81, 0x01]
        await self._send_command(command)
        self._is_on = True

    async def async_turn_off(self) -> None:
        """Turn the light off."""
        if self.capabilities.get("newPowerLightCommand") and self._ble_device.address:
            mac_bytes = bytes.fromhex(self._ble_device.address.replace(":", ""))
            command = [0x8D, 0x08, *list(mac_bytes), 0x81, 0x02]
        else:
            command = [0x81, 0x02]
        await self._send_command(command)
        self._is_on = False

    async def async_set_brightness(self, brightness: int) -> None:
        """Set the brightness of the light (0-255 Home Assistant -> 0-100 Neewer)."""
        neewer_brightness = round(brightness / 2.55)  # Scale 0-255 to 0-100
        neewer_brightness = max(0, min(100, neewer_brightness))

        # Determine the correct command based on light capabilities
        if self.capabilities.get("supportRGB"):
            # If RGB is supported, brightness is part of RGB/CCT commands
            # This needs to be handled in the HSI/CCT set methods
            _LOGGER.debug("Brightness will be set via HSI/CCT command for RGB light")
        else:
            # For CCT-only lights, there's a separate brightness command
            command = [0x82, 0x01, neewer_brightness]
            await self._send_command(command)
        self._brightness = neewer_brightness

    async def async_set_cct(
        self, cct_kelvin: int, brightness: int | None = None
    ) -> None:
        """Set the color temperature of the light (in Kelvin)."""
        # Convert Kelvin to Neewer's 32-56 or 27-65 range
        min_cct = self.capabilities.get("cctRange", {}).get("min", 32)
        max_cct = self.capabilities.get("cctRange", {}).get("max", 56)

        # Scale Kelvin to Neewer's internal CCT value (e.g., 2700K-6500K to 27-65)
        # Assuming a linear mapping for now, might need refinement
        neewer_cct = round(
            min_cct + (cct_kelvin - 2700) * (max_cct - min_cct) / (6500 - 2700)
        )
        neewer_cct = max(neewer_cct, min_cct)
        neewer_cct = min(neewer_cct, max_cct)

        neewer_brightness = self._brightness
        if brightness is not None:
            neewer_brightness = round(brightness / 2.55)

        if self.capabilities.get("supportCCTGM") and self._ble_device.address:
            mac_bytes = bytes.fromhex(self._ble_device.address.replace(":", ""))
            # GM value is 0 for now, needs to be implemented if supported
            command = [
                0x90,
                0x0C,
                *list(mac_bytes),
                0x87,
                neewer_brightness,
                neewer_cct,
                0x32,
                0x04,
            ]  # 0x32 is 50 for GM=0
        else:
            command = [0x87, 0x02, neewer_brightness, neewer_cct]
        await self._send_command(command)
        self._cct = neewer_cct
        self._brightness = neewer_brightness

    async def async_set_hsi(
        self, hue: float, saturation: float, brightness: int | None = None
    ) -> None:
        """Set the HSI color of the light."""
        neewer_hue = round(hue)
        neewer_saturation = round(saturation)  # Saturation is 0-100 in Neewer
        neewer_brightness = self._brightness
        if brightness is not None:
            neewer_brightness = round(brightness / 2.55)

        hue_low = neewer_hue & 0xFF
        hue_high = (neewer_hue >> 8) & 0xFF

        if self.capabilities.get("newRGBLightCommand") and self._ble_device.address:
            mac_bytes = bytes.fromhex(self._ble_device.address.replace(":", ""))
            command = [
                0x8F,
                0x0C,
                *list(mac_bytes),
                0x86,
                hue_low,
                hue_high,
                neewer_saturation,
                neewer_brightness,
                0x00,
            ]
        else:
            command = [
                0x86,
                0x04,
                hue_low,
                hue_high,
                neewer_saturation,
                neewer_brightness,
            ]
        await self._send_command(command)
        self._hue = neewer_hue
        self._saturation = neewer_saturation
        self._brightness = neewer_brightness

    async def async_set_effect(
        self, effect_id: int, brightness: int | None = None
    ) -> None:
        """Set a scene/effect on the light."""
        neewer_brightness = self._brightness
        if brightness is not None:
            neewer_brightness = round(brightness / 2.55)

        # This is a simplified implementation for basic 9-effect lights
        # Advanced 17-effect lights with parameters will need more complex logic
        command = [0x88, 0x02, neewer_brightness, effect_id]
        await self._send_command(command)
        self._effect = effect_id
        self._brightness = neewer_brightness
