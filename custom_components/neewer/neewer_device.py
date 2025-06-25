"""Neewer device library for Home Assistant integration."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from bleak.exc import BleakError
from bleak_retry_connector import BleakClientWithServiceCache, establish_connection

from .const import (
    COMMAND_DELAY_MS,
    CONTROL_CHARACTERISTIC_UUID,
    MIN_NOTIFICATION_LENGTH,
    NOTIFICATION_CHANNEL_TAG,
    NOTIFY_CHARACTERISTIC_UUID,
    PREFIX,
    SERVICE_UUID,
)
from .scene_effects import build_advanced_scene_command, validate_scene_parameters

if TYPE_CHECKING:
    from collections.abc import Callable

    from bleak import BleakClient
    from bleak.backends.characteristic import BleakGATTCharacteristic
    from bleak.backends.device import BLEDevice

_LOGGER = logging.getLogger(__name__)


class NeewerDeviceError(Exception):
    """Base exception for Neewer device communication."""


class NeewerConnectionError(NeewerDeviceError):
    """Exception for connection errors."""


class NeewerCommandError(NeewerDeviceError):
    """Exception for command errors."""


class NeewerDevice:
    """Represents a Neewer light device for library-style integration."""

    def __init__(
        self,
        ble_device: BLEDevice,
        capabilities: dict[str, Any],
        disconnect_callback: Callable[[BLEDevice], None] | None = None,
    ) -> None:
        """Initialize the Neewer device."""
        self._ble_device = ble_device
        self._capabilities = capabilities
        self._disconnect_callback = disconnect_callback
        self._client: BleakClient | None = None
        self._last_command_time: float = 0.0
        self._notification_callbacks: list[Callable[[bytes], None]] = []

        # Device state
        self._is_on: bool = False
        self._brightness: int = 0
        self._cct: int = 0
        self._hue: int = 0
        self._saturation: int = 0
        self._effect: int = 0
        self._gm: int = 0  # Green/Magenta adjustment

        # MAC address for advanced commands
        self._mac_address = capabilities.get("mac_address")

    @property
    def ble_device(self) -> BLEDevice:
        """Return the BLE device."""
        return self._ble_device

    @property
    def name(self) -> str:
        """Return the device name."""
        return self._ble_device.name or self._ble_device.address

    @property
    def address(self) -> str:
        """Return the device address."""
        return self._ble_device.address

    @property
    def capabilities(self) -> dict[str, Any]:
        """Return device capabilities."""
        return self._capabilities

    @property
    def is_connected(self) -> bool:
        """Return true if device is connected."""
        return self._client is not None and self._client.is_connected

    @property
    def is_on(self) -> bool:
        """Return true if the light is on."""
        return self._is_on

    @property
    def brightness(self) -> int:
        """Return brightness (0-100)."""
        return self._brightness

    @property
    def cct(self) -> int:
        """Return color temperature (device units)."""
        return self._cct

    @property
    def hue(self) -> int:
        """Return hue (0-360)."""
        return self._hue

    @property
    def saturation(self) -> int:
        """Return saturation (0-100)."""
        return self._saturation

    @property
    def effect(self) -> int:
        """Return current effect ID."""
        return self._effect

    @property
    def gm(self) -> int:
        """Return Green/Magenta adjustment (-50 to +50)."""
        return self._gm - 50  # Convert from 0-100 to -50 to +50

    def set_ble_device(self, ble_device: BLEDevice) -> None:
        """Update the BLE device."""
        self._ble_device = ble_device

    def add_notification_callback(self, callback: Callable[[bytes], None]) -> None:
        """Add a notification callback."""
        self._notification_callbacks.append(callback)

    def remove_notification_callback(self, callback: Callable[[bytes], None]) -> None:
        """Remove a notification callback."""
        if callback in self._notification_callbacks:
            self._notification_callbacks.remove(callback)

    async def connect(self) -> None:
        """Connect to the device."""
        if self.is_connected:
            return

        try:
            self._client = await establish_connection(
                BleakClientWithServiceCache,
                self._ble_device,
                self._ble_device.address,
                disconnected_callback=self._on_disconnect,
                services=[SERVICE_UUID],
            )
            _LOGGER.debug("Connected to %s", self.name)

            # Enable notifications
            _LOGGER.debug(
                "Enabling notifications on characteristic %s",
                NOTIFY_CHARACTERISTIC_UUID,
            )
            try:
                await self._client.start_notify(
                    NOTIFY_CHARACTERISTIC_UUID, self._notification_handler
                )
                _LOGGER.debug("Notifications enabled successfully")
            except Exception as e:
                _LOGGER.error("Failed to enable notifications: %s", e)
                # List available characteristics for debugging
                services = self._client.services
                for service in services:
                    _LOGGER.debug("Service: %s", service.uuid)
                    for char in service.characteristics:
                        _LOGGER.debug(
                            "  Characteristic: %s, properties: %s",
                            char.uuid,
                            char.properties,
                        )

            # Wait a bit for the device to be ready
            await asyncio.sleep(0.1)

            # Send initial read request
            _LOGGER.debug("Sending initial status query")
            await self._send_command([0x84, 0x00])

            # Wait for response
            await asyncio.sleep(0.5)
            _LOGGER.debug(
                "Initial connection sequence completed - is_on=%s, brightness=%s",
                self._is_on,
                self._brightness,
            )

        except BleakError as err:
            msg = f"Failed to connect to {self.name}: {err}"
            raise NeewerConnectionError(msg) from err

    async def disconnect(self) -> None:
        """Disconnect from the device."""
        if self._client and self._client.is_connected:
            try:
                await self._client.stop_notify(NOTIFY_CHARACTERISTIC_UUID)
                await self._client.disconnect()
            except BleakError as err:
                _LOGGER.warning("Error during disconnect: %s", err)
            finally:
                self._client = None
                _LOGGER.debug("Disconnected from %s", self.name)

    def _on_disconnect(self, _client: BleakClient) -> None:
        """Handle disconnect callback."""
        _LOGGER.warning("Device %s disconnected", self.name)
        self._client = None
        if self._disconnect_callback:
            self._disconnect_callback(self._ble_device)

    def _notification_handler(
        self, _characteristic: BleakGATTCharacteristic, data: bytearray
    ) -> None:
        """Handle incoming notifications."""
        _LOGGER.debug(
            "Notification from %s: %s (len=%d)", self.name, data.hex(), len(data)
        )

        # Validate checksum
        if len(data) >= MIN_NOTIFICATION_LENGTH and data[0] == PREFIX:
            expected_checksum = self._calculate_checksum(data[:-1])
            if expected_checksum != data[-1]:
                _LOGGER.warning(
                    "Checksum mismatch in notification from %s. Expected %s, got %s",
                    self.name,
                    expected_checksum,
                    data[-1],
                )
                return
        else:
            _LOGGER.debug(
                "Notification doesn't match expected format (prefix=%s, len=%d)",
                data[0] if data else "none",
                len(data),
            )

        # Parse different notification types
        if len(data) >= MIN_NOTIFICATION_LENGTH and data[0] == PREFIX:
            notification_type = data[1] if len(data) > 1 else 0
            _LOGGER.debug("Processing notification type: 0x%02x", notification_type)

            if data[1] == NOTIFICATION_CHANNEL_TAG and len(data) == 5:
                # Channel update notification: [0x78, 0x01, 0x01, CHANNEL, CHECKSUM]
                channel = data[3] + 1  # Convert 0-based to 1-based
                # Clamp channel to valid range (1 to 17 for effects)
                channel = max(1, min(17, channel))
                self._effect = channel
                _LOGGER.debug("Channel/Effect updated to: %s", self._effect)
            else:
                _LOGGER.debug(
                    "Unknown notification type: 0x%02x, data: %s", data[1], data.hex()
                )

        # Notify callbacks
        for callback in self._notification_callbacks:
            try:
                callback(bytes(data))
            except Exception:
                _LOGGER.exception("Error in notification callback")

    async def _send_command(self, data: list[int]) -> None:
        """Send a command to the device."""
        if not self.is_connected:
            msg = f"Not connected to {self.name}"
            raise NeewerConnectionError(msg)

        # Respect command timing
        current_time = asyncio.get_event_loop().time()
        time_since_last = (current_time - self._last_command_time) * 1000
        if time_since_last < COMMAND_DELAY_MS:
            await asyncio.sleep((COMMAND_DELAY_MS - time_since_last) / 1000)

        # Build command with prefix and checksum
        full_command = [PREFIX, *data]
        checksum = self._calculate_checksum(full_command)
        full_command.append(checksum)

        _LOGGER.debug("Sending command to %s: %s", self.name, bytes(full_command).hex())

        try:
            assert self._client is not None, "Client is not initialized"
            _LOGGER.debug("Writing to characteristic %s", CONTROL_CHARACTERISTIC_UUID)
            await self._client.write_gatt_char(
                CONTROL_CHARACTERISTIC_UUID, bytes(full_command), response=True
            )
            _LOGGER.debug("Command written successfully")
            self._last_command_time = asyncio.get_event_loop().time()
        except BleakError as err:
            msg = f"Failed to send command to {self.name}: {err}"
            raise NeewerCommandError(msg) from err

    def _calculate_checksum(self, data: bytes | bytearray | list[int]) -> int:
        """Calculate command checksum."""
        return sum(data) & 0xFF

    def _get_mac_bytes(self) -> list[int] | None:
        """Get MAC address bytes if available."""
        # First try the discovered MAC address
        mac_address = self._mac_address or self._ble_device.address

        try:
            if mac_address and ":" in mac_address:
                mac_bytes = bytes.fromhex(mac_address.replace(":", ""))
                return list(mac_bytes)
        except (ValueError, AttributeError):
            pass
        return None

    async def set_power(self, *, on: bool) -> None:
        """Turn the light on or off."""
        mac_bytes = self._get_mac_bytes()

        # Try new format first if device supports it and we have MAC
        if self._capabilities.get("newPowerLightCommand") and mac_bytes:
            try:
                command = [0x8D, 0x08, *mac_bytes, 0x81, 0x01 if on else 0x02]
                await self._send_command(command)
                self._is_on = on
            except NeewerCommandError as err:
                _LOGGER.warning(
                    "New power command failed, falling back to old format: %s", err
                )
            else:
                return

        # Fallback to old format
        try:
            command = [0x81, 0x01, 0x01 if on else 0x02]
            await self._send_command(command)
            self._is_on = on
        except NeewerCommandError:
            _LOGGER.exception("Power command failed")
            raise

    async def set_brightness(self, brightness: int) -> None:
        """Set brightness (0-100)."""
        brightness = max(0, min(100, brightness))

        # For CCT-only lights, use dedicated brightness command
        if not self._capabilities.get("supportRGB"):
            command = [0x82, 0x01, brightness]
            await self._send_command(command)
        else:
            # For RGB lights, brightness must be sent with color data
            # Use current hue and saturation values
            await self.set_hsi(self._hue, self._saturation, brightness)
            return  # set_hsi will update _brightness

        self._brightness = brightness

    async def set_cct(
        self, cct_kelvin: int, brightness: int | None = None, gm: int = 0
    ) -> None:
        """Set color temperature in Kelvin with optional brightness and GM."""
        if brightness is None:
            brightness = self._brightness

        brightness = max(0, min(100, brightness))
        gm_value = max(-50, min(50, gm)) + 50  # Convert to 0-100 range

        # Convert Kelvin to device CCT range
        cct_range = self._capabilities.get("cctRange", {"min": 32, "max": 56})
        min_cct, max_cct = cct_range["min"], cct_range["max"]

        device_cct = round(
            min_cct + (cct_kelvin - 2700) * (max_cct - min_cct) / (6500 - 2700)
        )
        device_cct = max(min_cct, min(max_cct, device_cct))

        mac_bytes = self._get_mac_bytes()

        # Try CCT with GM support first if available
        if self._capabilities.get("supportCCTGM") and mac_bytes:
            try:
                command = [
                    0x90,
                    0x0C,
                    *mac_bytes,
                    0x87,
                    brightness,
                    device_cct,
                    gm_value,
                    0x04,
                ]
                await self._send_command(command)
                self._brightness = brightness
                self._cct = device_cct
                self._gm = gm_value
            except NeewerCommandError as err:
                _LOGGER.warning(
                    "CCT+GM command failed, falling back to basic CCT: %s", err
                )
            else:
                return

        # Fallback to basic CCT
        try:
            command = [0x87, 0x02, brightness, device_cct]
            await self._send_command(command)
            self._brightness = brightness
            self._cct = device_cct
            # Don't update GM value when using basic command
        except NeewerCommandError:
            _LOGGER.exception("CCT command failed")
            raise

    async def set_hsi(
        self, hue: float, saturation: float, brightness: int | None = None
    ) -> None:
        """Set HSI color."""
        if brightness is None:
            brightness = self._brightness

        hue = max(0, min(360, int(hue)))
        saturation = max(0, min(100, int(saturation)))
        brightness = max(0, min(100, brightness))

        hue_low = hue & 0xFF
        hue_high = (hue >> 8) & 0xFF

        mac_bytes = self._get_mac_bytes()

        # Try new RGB command format first if available
        if self._capabilities.get("newRGBLightCommand") and mac_bytes:
            try:
                command = [
                    0x8F,
                    0x0C,
                    *mac_bytes,
                    0x86,
                    hue_low,
                    hue_high,
                    saturation,
                    brightness,
                    0x00,
                ]
                await self._send_command(command)
                self._hue = hue
                self._saturation = saturation
                self._brightness = brightness
            except NeewerCommandError as err:
                _LOGGER.warning(
                    "New RGB command failed, falling back to old format: %s", err
                )
            else:
                return

        # Fallback to old RGB command format
        try:
            command = [0x86, 0x04, hue_low, hue_high, saturation, brightness]
            await self._send_command(command)
            self._hue = hue
            self._saturation = saturation
            self._brightness = brightness
        except NeewerCommandError:
            _LOGGER.exception("RGB command failed")
            raise

    async def set_effect(
        self, effect_id: int, brightness: int | None = None, **params: Any
    ) -> None:
        """Set scene/effect with parameters."""
        if brightness is None:
            brightness = self._brightness

        brightness = max(0, min(100, brightness))

        # Check if device supports advanced effects and we have MAC address
        if self._capabilities.get("support17FX"):
            mac_bytes = self._get_mac_bytes()
            if mac_bytes:
                try:
                    # Validate and build advanced scene command
                    validated_params = validate_scene_parameters(effect_id, **params)
                    command = build_advanced_scene_command(
                        effect_id, mac_bytes, brightness, **validated_params
                    )
                    await self._send_command(command)
                    self._effect = effect_id
                    self._brightness = brightness
                except (ValueError, KeyError) as err:
                    _LOGGER.warning("Failed to build advanced scene command: %s", err)
                    # Fall through to basic command
                else:
                    return
            else:
                _LOGGER.debug(
                    "Advanced effects require MAC address, falling back to basic"
                )

        # Basic scene command (9-effect lights or fallback)
        command = [0x88, 0x02, brightness, effect_id]
        await self._send_command(command)
        self._effect = effect_id
        self._brightness = brightness
