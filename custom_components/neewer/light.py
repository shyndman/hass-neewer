"""Platform for light integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_COLOR_TEMP_KELVIN,
    ATTR_EFFECT,
    ATTR_HS_COLOR,
    LightEntity,
)

# Custom attributes for GM (Green/Magenta) adjustment
ATTR_GM = "gm"  # Green/Magenta adjustment (-50 to +50)

from homeassistant.components.light.const import ColorMode, LightEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import NeewerDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .neewer_device import NeewerDevice

_LOGGER = logging.getLogger(__name__)

# Mapping of Neewer effect IDs to Home Assistant effect names
NEEWER_BASIC_EFFECTS = {
    0x01: "Squad Car",
    0x02: "Ambulance",
    0x03: "Fire Engine",
    0x04: "Fireworks",
    0x05: "Party",
    0x06: "Candle Light",
    0x07: "Paparazzi",
    0x08: "Screen",
    0x09: "Lightning",
}

NEEWER_ADVANCED_EFFECTS = {
    0x01: "Lightning",
    0x02: "Paparazzi",
    0x03: "Defective Bulb",
    0x04: "Explosion",
    0x05: "Welding",
    0x06: "CCT Flash",
    0x07: "HUE Flash",
    0x08: "CCT Pulse",
    0x09: "HUE Pulse",
    0x0A: "Cop Car",
    0x0B: "Candlelight",
    0x0C: "HUE Loop",
    0x0D: "CCT Loop",
    0x0E: "INT Loop",
    0x0F: "TV Screen",
    0x10: "Firework",
    0x11: "Party",
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: Any,  # Replace with actual type if available
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Neewer Light platform."""
    coordinator: NeewerDataUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([NeewerLightEntity(coordinator)])


class NeewerLightEntity(CoordinatorEntity[NeewerDataUpdateCoordinator], LightEntity):
    """Representation of a Neewer Light."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(self, coordinator: NeewerDataUpdateCoordinator) -> None:
        """Initialize the Neewer Light entity."""
        super().__init__(coordinator)
        self._device: NeewerDevice = coordinator.device
        self._attr_unique_id = self._device.address
        self._attr_device_info = coordinator.device_info

        # Set supported color modes based on capabilities
        self._supported_color_modes: set[ColorMode] = {
            ColorMode.ONOFF,
            ColorMode.BRIGHTNESS,
        }
        if self._device.capabilities.get("supportRGB"):
            self._supported_color_modes.add(
                ColorMode.HS
            )  # Neewer uses HSI, HS is closest HA mode
        if self._device.capabilities.get("cctRange"):
            self._supported_color_modes.add(ColorMode.COLOR_TEMP)

        self._attr_supported_color_modes = self._supported_color_modes

        # Set supported features (effects)
        supported_features = LightEntityFeature(0)

        # Determine which effects to support based on device capabilities
        self._effect_map = {}
        if self._device.capabilities.get("support17FX"):
            self._effect_map = NEEWER_ADVANCED_EFFECTS
            supported_features |= LightEntityFeature.EFFECT
        elif self._device.capabilities.get("support9FX"):
            self._effect_map = NEEWER_BASIC_EFFECTS
            supported_features |= LightEntityFeature.EFFECT

        if self._effect_map:
            self._attr_effect_list = list(self._effect_map.values())

        # Add transition support
        supported_features |= LightEntityFeature.TRANSITION
        self._attr_supported_features = supported_features

    @property
    def is_on(self) -> bool | None:
        """Return true if the light is on."""
        return self._device.is_on

    @property
    def brightness(self) -> int | None:
        """Return the brightness of this light between 1..255."""
        # Scale Neewer's 0-100 brightness to Home Assistant's 0-255
        return round(self._device.brightness * 2.55)

    @property
    def color_mode(self) -> ColorMode | None:
        """Return the color mode of the light."""
        # Determine the current color mode based on the light's state
        if self._device.effect != 0:
            # When an effect is active, the color mode should reflect what can be adjusted
            # If brightness can be adjusted during effect, return BRIGHTNESS, else ONOFF
            if self._device.brightness != 0:
                return ColorMode.BRIGHTNESS
            return ColorMode.ONOFF
        if self._device.hue != 0 or self._device.saturation != 0:
            return ColorMode.HS
        if self._device.cct != 0:
            return ColorMode.COLOR_TEMP
        if self._device.brightness != 0:
            return ColorMode.BRIGHTNESS
        return ColorMode.ONOFF

    @property
    def hs_color(self) -> tuple[float, float] | None:
        """Return the hue and saturation color value [float, float]."""
        if self._device.capabilities.get("supportRGB"):
            return (float(self._device.hue), float(self._device.saturation))
        return None

    @property
    def color_temp_kelvin(self) -> int | None:
        """Return the color temperature in Kelvin."""
        if self._device.capabilities.get("cctRange"):
            min_cct = self._device.capabilities.get("cctRange", {}).get("min", 32)
            max_cct = self._device.capabilities.get("cctRange", {}).get("max", 56)
            # Scale Neewer's internal CCT value back to Kelvin
            return round(
                2700
                + (self._device.cct - min_cct) * (6500 - 2700) / (max_cct - min_cct)
            )
        return None

    @property
    def min_color_temp_kelvin(self) -> int:
        """Return the warmest color_temp_kelvin that this light supports."""
        return 2700

    @property
    def max_color_temp_kelvin(self) -> int:
        """Return the coldest color_temp_kelvin that this light supports."""
        return 6500

    @property
    def effect(self) -> str | None:
        """Return the current effect."""
        return self._effect_map.get(self._device.effect)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        attrs = {}

        # Add GM (Green/Magenta) attribute if device supports it
        if self._device.capabilities.get("supportCCTGM"):
            attrs[ATTR_GM] = self._device.gm

        # Add MAC discovery info for diagnostic purposes
        attrs["mac_address"] = self._device.capabilities.get("mac_address")
        attrs["mac_discovery_successful"] = self._device.capabilities.get("mac_discovery_successful", False)
        attrs["mac_source"] = self._device.capabilities.get("mac_source", "unknown")

        return attrs if attrs else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the light on."""
        _LOGGER.debug("Turning on light %s with kwargs: %s", self.entity_id, kwargs)

        # Turn on the light if it's not already on
        if not self.is_on:
            await self._device.set_power(True)

        brightness = kwargs.get(ATTR_BRIGHTNESS)
        hs_color = kwargs.get(ATTR_HS_COLOR)
        color_temp_kelvin = kwargs.get(ATTR_COLOR_TEMP_KELVIN)
        effect = kwargs.get(ATTR_EFFECT)
        gm = kwargs.get(ATTR_GM, 0)  # Green/Magenta adjustment

        # Convert brightness from HA scale (0-255) to Neewer scale (0-100)
        neewer_brightness = None
        if brightness is not None:
            neewer_brightness = round(brightness / 2.55)

        if effect is not None:
            # Find effect ID from name
            effect_id = next(
                (k for k, v in self._effect_map.items() if v == effect), None
            )
            if effect_id is not None:
                await self._device.set_effect(effect_id, neewer_brightness)
            else:
                _LOGGER.warning("Unknown effect: %s", effect)
        elif hs_color is not None and self._device.capabilities.get("supportRGB"):
            hue, saturation = hs_color
            await self._device.set_hsi(hue, saturation, neewer_brightness)
        elif color_temp_kelvin is not None and self._device.capabilities.get(
            "cctRange"
        ):
            await self._device.set_cct(color_temp_kelvin, neewer_brightness, gm)
        elif neewer_brightness is not None:
            await self._device.set_brightness(neewer_brightness)

        # Request an update to reflect the new state
        await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        _LOGGER.debug("Turning off light %s", self.entity_id)
        await self._device.set_power(False)
        await self.coordinator.async_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # State is automatically updated through device properties
        self.async_write_ha_state()
