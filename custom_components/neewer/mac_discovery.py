"""MAC address discovery utilities for Neewer devices."""
from __future__ import annotations

import asyncio
import logging
import platform
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

MAX_DISCOVERY_ATTEMPTS = 10
DISCOVERY_RETRY_DELAY = 0.5  # seconds


class MacDiscoveryError(Exception):
    """Exception raised when MAC discovery fails."""


async def async_discover_mac_address(
    hass: HomeAssistant, device_name: str, known_address: str | None = None
) -> str | None:
    """
    Attempt to discover MAC address for a device.
    
    Args:
        hass: Home Assistant instance
        device_name: Name of the device to find
        known_address: Previously known address for validation
        
    Returns:
        MAC address if found, None if discovery failed
        
    Note:
        MAC discovery is not reliable on all platforms and may fail.
        This is expected behavior, not an error condition.
    """
    _LOGGER.debug("Attempting MAC discovery for device: %s", device_name)
    
    # If we already have a known address, validate it's still reachable
    if known_address:
        if await _validate_address(hass, known_address):
            _LOGGER.debug("Known address %s is still valid", known_address)
            return known_address
        _LOGGER.debug("Known address %s is no longer valid", known_address)
    
    # Try platform-specific discovery methods
    system = platform.system().lower()
    
    for attempt in range(MAX_DISCOVERY_ATTEMPTS):
        _LOGGER.debug("MAC discovery attempt %d/%d for %s", attempt + 1, MAX_DISCOVERY_ATTEMPTS, device_name)
        
        try:
            mac_address = None
            
            if system == "darwin":
                mac_address = await _discover_mac_macos(device_name)
            elif system == "linux":
                mac_address = await _discover_mac_linux(device_name)
            elif system == "windows":
                mac_address = await _discover_mac_windows(device_name)
            else:
                _LOGGER.warning("MAC discovery not supported on platform: %s", system)
                break
                
            if mac_address and await _validate_address(hass, mac_address):
                _LOGGER.info("Successfully discovered MAC address for %s: %s", device_name, mac_address)
                return mac_address
                
        except Exception as err:
            _LOGGER.debug("MAC discovery attempt %d failed: %s", attempt + 1, err)
            
        if attempt < MAX_DISCOVERY_ATTEMPTS - 1:
            await asyncio.sleep(DISCOVERY_RETRY_DELAY)
    
    _LOGGER.info("MAC discovery failed for %s after %d attempts", device_name, MAX_DISCOVERY_ATTEMPTS)
    return None


async def _validate_address(hass: HomeAssistant, address: str) -> bool:
    """Validate that an address is reachable via Home Assistant's Bluetooth."""
    try:
        from homeassistant.components import bluetooth
        
        # Check if HA's Bluetooth can see this address
        service_info = bluetooth.async_last_service_info(hass, address, connectable=True)
        return service_info is not None
        
    except Exception as err:
        _LOGGER.debug("Address validation failed for %s: %s", address, err)
        return False


async def _discover_mac_macos(device_name: str) -> str | None:
    """
    Attempt MAC discovery on macOS using system_profiler.
    
    Note: macOS Bluetooth Framework does not provide reliable MAC access.
    This method has limited success rate.
    """
    try:
        # Try system_profiler approach
        proc = await asyncio.create_subprocess_exec(
            "system_profiler", "SPBluetoothDataType", "-json",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            import json
            data = json.loads(stdout.decode())
            
            # Parse Bluetooth device data
            for item in data.get("SPBluetoothDataType", []):
                devices = item.get("device_connected", [])
                for device in devices:
                    if device.get("device_name", "").lower() == device_name.lower():
                        return device.get("device_address")
                        
    except Exception as err:
        _LOGGER.debug("macOS MAC discovery failed: %s", err)
        
    return None


async def _discover_mac_linux(device_name: str) -> str | None:
    """
    Attempt MAC discovery on Linux using bluetoothctl and hcitool.
    """
    try:
        # Try bluetoothctl devices
        proc = await asyncio.create_subprocess_exec(
            "bluetoothctl", "devices",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            lines = stdout.decode().split('\n')
            for line in lines:
                if device_name.lower() in line.lower():
                    # Format: "Device AA:BB:CC:DD:EE:FF Device Name"
                    parts = line.split()
                    if len(parts) >= 2 and parts[0] == "Device":
                        return parts[1]
                        
    except Exception as err:
        _LOGGER.debug("Linux bluetoothctl discovery failed: %s", err)
        
    try:
        # Try hcitool scan as fallback
        proc = await asyncio.create_subprocess_exec(
            "hcitool", "scan",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            lines = stdout.decode().split('\n')
            for line in lines:
                if device_name.lower() in line.lower():
                    # Format: "AA:BB:CC:DD:EE:FF	Device Name"
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        return parts[0].strip()
                        
    except Exception as err:
        _LOGGER.debug("Linux hcitool discovery failed: %s", err)
        
    return None


async def _discover_mac_windows(device_name: str) -> str | None:
    """
    Attempt MAC discovery on Windows using PowerShell.
    """
    try:
        # Use PowerShell to query Bluetooth devices
        powershell_cmd = (
            'Get-PnpDevice -Class Bluetooth | '
            'Where-Object {$_.FriendlyName -like "*' + device_name + '*"} | '
            'Select-Object -ExpandProperty InstanceId'
        )
        
        proc = await asyncio.create_subprocess_exec(
            "powershell", "-Command", powershell_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            output = stdout.decode().strip()
            # Extract MAC from instance ID (format varies)
            # Usually contains the MAC address in some form
            import re
            mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
            match = re.search(mac_pattern, output)
            if match:
                return match.group(0).replace('-', ':').upper()
                
    except Exception as err:
        _LOGGER.debug("Windows PowerShell discovery failed: %s", err)
        
    return None


def get_mac_from_address(address: str) -> str | None:
    """
    Extract MAC address from various address formats.
    
    Args:
        address: Device address in various formats
        
    Returns:
        Normalized MAC address or None if invalid
    """
    if not address:
        return None
        
    # Remove common prefixes and clean up
    address = address.replace("bluetooth://", "").replace("ble://", "")
    
    # Check if it's already a valid MAC address
    import re
    mac_pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    if re.match(mac_pattern, address):
        return address.replace('-', ':').upper()
        
    # Try to extract MAC from longer strings
    mac_search = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
    match = re.search(mac_search, address)
    if match:
        return match.group(0).replace('-', ':').upper()
        
    return None


async def async_get_enhanced_device_info(
    hass: HomeAssistant, device_name: str, device_address: str
) -> dict[str, Any]:
    """
    Get enhanced device information including MAC discovery.
    
    Returns:
        Dictionary with device info including mac_address if discoverable
    """
    info = {
        "device_name": device_name,
        "device_address": device_address,
        "mac_address": None,
        "mac_discovery_attempted": True,
        "mac_discovery_successful": False,
    }
    
    # Try to get MAC from address first
    mac_from_address = get_mac_from_address(device_address)
    if mac_from_address:
        info["mac_address"] = mac_from_address
        info["mac_discovery_successful"] = True
        info["mac_source"] = "address_parsing"
        return info
    
    # Attempt active MAC discovery
    discovered_mac = await async_discover_mac_address(hass, device_name, device_address)
    if discovered_mac:
        info["mac_address"] = discovered_mac
        info["mac_discovery_successful"] = True
        info["mac_source"] = "active_discovery"
    else:
        info["mac_source"] = "discovery_failed"
        
    return info