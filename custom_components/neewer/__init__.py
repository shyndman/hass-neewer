"""The Neewer Light integration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components import bluetooth
from homeassistant.const import Platform
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .coordinator import NeewerDataUpdateCoordinator
from .data import NeewerLightData
from .mac_discovery import async_get_enhanced_device_info

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LIGHT]

# Service schemas
SERVICE_SET_GM = "set_gm"
SERVICE_SET_ADVANCED_EFFECT = "set_advanced_effect"

SET_GM_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_ids,
    vol.Required("gm"): vol.Coerce(int),
})

SET_ADVANCED_EFFECT_SCHEMA = vol.Schema({
    vol.Required("entity_id"): cv.entity_ids,
    vol.Required("effect"): cv.string,
    vol.Optional("brightness", default=100): vol.Coerce(int),
    vol.Optional("speed", default=5): vol.Coerce(int),
    vol.Optional("cct"): vol.Coerce(int),
    vol.Optional("gm", default=50): vol.Coerce(int),
    vol.Optional("hue"): vol.Coerce(int),
    vol.Optional("saturation"): vol.Coerce(int),
    vol.Optional("sparks"): vol.Coerce(int),
})


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Neewer Light from a config entry."""
    address = entry.unique_id
    if not address:
        _LOGGER.error("Config entry unique ID (address) is missing.")
        return False

    # Get the BLEDevice from the address
    ble_device = bluetooth.async_ble_device_from_address(
        hass, address, connectable=True
    )
    if not ble_device:
        _LOGGER.warning(
            "BLEDevice not found for address %s, retrying discovery", address
        )
        # If device is not immediately available, try to discover it
        # This might happen if HA restarts and the device hasn't advertised yet
        bluetooth.async_rediscover_address(hass, address)
        return False  # Defer setup until device is discovered

    # Initialize NeewerLightData (singleton)
    neewer_data = NeewerLightData(hass)

    # Get enhanced device info including MAC discovery
    device_info = await async_get_enhanced_device_info(
        hass, ble_device.name or "Unknown", ble_device.address
    )

    capabilities = await neewer_data.async_get_light_capabilities(
        ble_device.name or ble_device.address, ble_device.address
    )

    if not capabilities:
        _LOGGER.error("Could not determine capabilities for device %s", ble_device.name)
        return False

    # Add MAC discovery results to capabilities
    capabilities.update({
        "mac_address": device_info.get("mac_address"),
        "mac_discovery_successful": device_info.get("mac_discovery_successful", False),
        "mac_source": device_info.get("mac_source", "unknown"),
    })

    coordinator = NeewerDataUpdateCoordinator(
        hass,
        _LOGGER,
        ble_device,
        address,
        capabilities,
    )
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Start the coordinator to connect and poll
    await coordinator.async_start()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    await _async_register_services(hass)

    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        coordinator: NeewerDataUpdateCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.async_shutdown()  # Ensure device is disconnected
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_services(hass: HomeAssistant) -> None:
    """Register integration services."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_GM):
        return  # Services already registered

    async def async_set_gm(call) -> None:
        """Handle set GM service call."""
        entity_ids = call.data["entity_id"]
        gm_value = call.data["gm"]

        # Validate GM range
        gm_value = max(-50, min(50, gm_value))

        for entity_id in entity_ids:
            entity = hass.states.get(entity_id)
            if entity and entity.domain == "light":
                # Get the coordinator for this entity
                for coordinator in hass.data.get(DOMAIN, {}).values():
                    if (
                        hasattr(coordinator, "device")
                        and coordinator.device.capabilities.get("supportCCTGM")
                    ):
                        # Set GM using current CCT values
                        current_cct = coordinator.device.cct or 50
                        current_brightness = coordinator.device.brightness or 100
                        await coordinator.device.set_cct(
                            # Convert device CCT back to Kelvin for the method
                            2700 + (current_cct - 27) * (6500 - 2700) / (65 - 27),
                            current_brightness,
                            gm_value
                        )
                        await coordinator.async_refresh()

    async def async_set_advanced_effect(call) -> None:
        """Handle set advanced effect service call."""
        entity_ids = call.data["entity_id"]
        effect_name = call.data["effect"]
        params = {
            k: v for k, v in call.data.items() if k not in ["entity_id", "effect"]
        }

        # Convert effect name to ID
        from .light import NEEWER_ADVANCED_EFFECTS
        effect_id = next(
            (k for k, v in NEEWER_ADVANCED_EFFECTS.items() if v == effect_name),
            None,
        )

        if effect_id is None:
            _LOGGER.error("Unknown advanced effect: %s", effect_name)
            return

        for entity_id in entity_ids:
            entity = hass.states.get(entity_id)
            if entity and entity.domain == "light":
                # Get the coordinator for this entity
                for coordinator in hass.data.get(DOMAIN, {}).values():
                    if (
                        hasattr(coordinator, "device")
                        and coordinator.device.capabilities.get("support17FX")
                    ):
                        await coordinator.device.set_effect(effect_id, **params)
                        await coordinator.async_refresh()

    hass.services.async_register(
        DOMAIN, SERVICE_SET_GM, async_set_gm, schema=SET_GM_SCHEMA
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SET_ADVANCED_EFFECT,
        async_set_advanced_effect,
        schema=SET_ADVANCED_EFFECT_SCHEMA,
    )
