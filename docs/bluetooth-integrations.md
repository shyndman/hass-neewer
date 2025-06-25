# Bluetooth Integrations

## Best practices for integration authors

- Integrations that need to use a Bluetooth adapter should add `bluetooth_adapters` in [`dependencies`](https://developers.home-assistant.io/docs/creating_integration_manifest#dependencies) in their [`manifest.json`](https://developers.home-assistant.io/docs/creating_integration_manifest). The [`manifest.json`](https://developers.home-assistant.io/docs/creating_integration_manifest) entry ensures that all supported remote adapters are connected before the integration tries to use them.
- Call the `bluetooth.async_get_scanner` API to get a `BleakScanner` instance and pass it to your library. The returned scanner avoids the overhead of running multiple scanners, which is significant. Additionally, the wrapped scanner will continue functioning if the user changes the Bluetooth adapter settings.
- Avoid reusing a `BleakClient` between connections since this will make connecting less reliable.
- Use a connection timeout of at least ten (10) seconds as `BlueZ` must resolve services when connecting to a new or updated device for the first time. Transient connection errors are frequent when connecting, and connections are not always successful on the first attempt. The `bleak-retry-connector` PyPI package can take the guesswork out of quickly and reliably establishing a connection to a device.

## Connectable and non-connectable Bluetooth controllers

Home Assistant has support for remote Bluetooth controllers. Some controllers only support listening for advertisement data and do not support connecting to devices. Since many devices only need to receive advertisements, we have the concept of connectable devices and non-connectable devices. Suppose the device does not require an active connection. In that case, the `connectable` argument should be set to `False` to opt-in on receiving data from controllers that do not support making outgoing connections. When `connectable` is set to `False`, data from `connectable` and non-connectable controllers will be provided.

The default value for `connectable` is `True`. If the integration has some devices that require connections and some devices that do not, the `manifest.json` should set the flag appropriately for the device. If it is impossible to construct a matcher to differentiate between similar devices, check the `connectable` property in the config flow discovery `BluetoothServiceInfoBleak` and reject flows for devices needing outgoing connections.

# Fetching Bluetooth Data

## Choosing a method to fetch data

If the device's primary method to notify of updates is Bluetooth advertisements and its primary function is a sensor, binary sensor, or firing events:

- If all sensors are updated via Bluetooth advertisements: [`PassiveBluetoothProcessorCoordinator`](https://developers.home-assistant.io/docs/core/bluetooth/#passivebluetoothprocessorcoordinator)
- If active connection are needed for some sensors: [`ActiveBluetoothProcessorCoordinator`](https://developers.home-assistant.io/docs/core/bluetooth/#activebluetoothprocessorcoordinator)

If the device's primary method to notify of updates is Bluetooth advertisements and its primary function is **not** a sensor, binary sensor, or firing events:

- If all entities are updated via Bluetooth advertisements: [`PassiveBluetoothCoordinator`](https://developers.home-assistant.io/docs/core/bluetooth/#passivebluetoothcoordinator)
- If active connections are needed: [`ActiveBluetoothCoordinator`](https://developers.home-assistant.io/docs/core/bluetooth/#activebluetoothcoordinator)

If your device only communicates with an active Bluetooth connection and does not use Bluetooth advertisements:

- [`DataUpdateCoordinator`](https://developers.home-assistant.io/docs/integration_fetching_data)

## BluetoothProcessorCoordinator

The `ActiveBluetoothProcessorCoordinator` and `PassiveBluetoothProcessorCoordinator` significantly reduce the code needed for creating integrations that primary function as sensor, binary sensors, or fire events. By formatting the data fed into the processor coordinators into a `PassiveBluetoothDataUpdate` object, the frameworks can take care of creating the entities on demand and allow for minimal `sensor` and `binary_sensor` platform implementations.

These frameworks require the data coming from the library to be formatted into a `PassiveBluetoothDataUpdate` as shown below:

```python
@dataclasses.dataclass(frozen=True)
class PassiveBluetoothEntityKey:
    """Key for a passive bluetooth entity.

    Example:
    key: temperature
    device_id: outdoor_sensor_1
    """

    key: str
    device_id: str | None

@dataclasses.dataclass(frozen=True)
class PassiveBluetoothDataUpdate(Generic[_T]):
    """Generic bluetooth data."""

    devices: dict[str | None, DeviceInfo] = dataclasses.field(default_factory=dict)
    entity_descriptions: Mapping[
        PassiveBluetoothEntityKey, EntityDescription
    ] = dataclasses.field(default_factory=dict)
    entity_names: Mapping[PassiveBluetoothEntityKey, str | None] = dataclasses.field(
        default_factory=dict
    )
    entity_data: Mapping[PassiveBluetoothEntityKey, _T] = dataclasses.field(
        default_factory=dict
    )
```

### PassiveBluetoothProcessorCoordinator

Example `async_setup_entry` for an integration `__init__.py` using a `PassiveBluetoothProcessorCoordinator`:

Example `sensor.py`:

```python
from homeassistant import config_entries
from homeassistant.components.bluetooth.passive_update_processor import (
    PassiveBluetoothDataProcessor,
    PassiveBluetoothDataUpdate,
    PassiveBluetoothEntityKey,
    PassiveBluetoothProcessorCoordinator,
    PassiveBluetoothProcessorEntity,
)
from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

def sensor_update_to_bluetooth_data_update(parsed_data):
    """Convert a sensor update to a Bluetooth data update."""
    # This function must convert the parsed_data
    # from your library's update_method to a \`PassiveBluetoothDataUpdate\`
    # See the structure above
    return PassiveBluetoothDataUpdate(
        devices={},
        entity_descriptions={},
        entity_data={},
        entity_names={},
    )

async def async_setup_entry(
    hass: HomeAssistant,
    entry: config_entries.ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the example BLE sensors."""
    coordinator: PassiveBluetoothProcessorCoordinator = hass.data[DOMAIN][
        entry.entry_id
    ]
    processor = PassiveBluetoothDataProcessor(sensor_update_to_bluetooth_data_update)
    entry.async_on_unload(
        processor.async_add_entities_listener(
            ExampleBluetoothSensorEntity, async_add_entities
        )
    )
    entry.async_on_unload(coordinator.async_register_processor(processor))

class ExampleBluetoothSensorEntity(PassiveBluetoothProcessorEntity, SensorEntity):
    """Representation of an example BLE sensor."""

    @property
    def native_value(self) -> float | int | str | None:
        """Return the native value."""
        return self.processor.entity_data.get(self.entity_key)
```

### ActiveBluetoothProcessorCoordinator

An `ActiveBluetoothProcessorCoordinator` functions nearly the same as a `PassiveBluetoothProcessorCoordinator` but will also make an active connection to poll for data based on `needs_poll_method` and a `poll_method` function which are called when the device's Bluetooth advertisement changes. The `sensor.py` implementation is the same as the `PassiveBluetoothProcessorCoordinator`.

Example `async_setup_entry` for an integration `__init__.py` using an `ActiveBluetoothProcessorCoordinator`:

```python
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import CoreState, HomeAssistant
from homeassistant.components.bluetooth import BluetoothScanningMode

from homeassistant.components.bluetooth import (
    BluetoothScanningMode,
    BluetoothServiceInfoBleak,
    async_ble_device_from_address,
)
from homeassistant.const import Platform

from homeassistant.components.bluetooth.active_update_processor import (
    ActiveBluetoothProcessorCoordinator,
)
PLATFORMS: list[Platform] = [Platform.SENSOR]

from your_library import DataParser

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up example BLE device from a config entry."""
    address = entry.unique_id
    assert address is not None
    data = DataParser()

    def _needs_poll(
        service_info: BluetoothServiceInfoBleak, last_poll: float | None
    ) -> bool:
        return (
            hass.state == CoreState.running
            and data.poll_needed(service_info, last_poll)
            and bool(
                async_ble_device_from_address(
                    hass, service_info.device.address, connectable=True
                )
            )
        )

    async def _async_poll(service_info: BluetoothServiceInfoBleak):
        if service_info.connectable:
            connectable_device = service_info.device
        elif device := async_ble_device_from_address(
            hass, service_info.device.address, True
        ):
            connectable_device = device
        else:
            # We have no Bluetooth controller that is in range of
            # the device to poll it
            raise RuntimeError(
                f"No connectable device found for {service_info.device.address}"
            )
        return await data.async_poll(connectable_device)

    coordinator = hass.data.setdefault(DOMAIN, {})[
        entry.entry_id
    ] = ActiveBluetoothProcessorCoordinator(
        hass,
        _LOGGER,
        address=address,
        mode=BluetoothScanningMode.PASSIVE,
        update_method=data.update,
        needs_poll_method=_needs_poll,
        poll_method=_async_poll,
        # We will take advertisements from non-connectable devices
        # since we will trade the BLEDevice for a connectable one
        # if we need to poll it
        connectable=False,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(
        # only start after all platforms have had a chance to subscribe
        coordinator.async_start()
    )
    return True
```

## BluetoothCoordinator

The `ActiveBluetoothCoordinator` and `PassiveBluetoothCoordinator` coordinators function similar to `DataUpdateCoordinators` except they are driven by incoming advertisement data instead of polling.

### PassiveBluetoothCoordinator

Below is an example of a `PassiveBluetoothDataUpdateCoordinator`. Incoming data is received via `_async_handle_bluetooth_event` and processed by the integration's library.

### ActiveBluetoothCoordinator

Below is an example of an `ActiveBluetoothDataUpdateCoordinator`. Incoming data is received via `_async_handle_bluetooth_event` and processed by the integration's library.

The method passed to `needs_poll_method` is called each time the Bluetooth advertisement changes to determine if the method passed to `poll_method` should be called to make an active connection to the device to obtain additional data.

```python
import logging
from typing import TYPE_CHECKING

from homeassistant.components import bluetooth
from homeassistant.components.bluetooth.active_update_coordinator import (
    ActiveBluetoothDataUpdateCoordinator,
)
from homeassistant.core import CoreState, HomeAssistant, callback

if TYPE_CHECKING:
    from bleak.backends.device import BLEDevice

class ExampleActiveBluetoothDataUpdateCoordinator(
    ActiveBluetoothDataUpdateCoordinator[None]
):
    """Class to manage fetching example data."""

    def __init__(
        self,
        hass: HomeAssistant,
        logger: logging.Logger,
        ble_device: BLEDevice,
        device: YourLibDevice,
    ) -> None:
        """Initialize example data coordinator."""
        super().__init__(
            hass=hass,
            logger=logger,
            address=ble_device.address,
            needs_poll_method=self._needs_poll,
            poll_method=self._async_update,
            mode=bluetooth.BluetoothScanningMode.ACTIVE,
            connectable=True,
        )
        self.device = device

    @callback
    def _needs_poll(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        seconds_since_last_poll: float | None,
    ) -> bool:
        # Only poll if hass is running, we need to poll,
        # and we actually have a way to connect to the device
        return (
            self.hass.state == CoreState.running
            and self.device.poll_needed(seconds_since_last_poll)
            and bool(
                bluetooth.async_ble_device_from_address(
                    self.hass, service_info.device.address, connectable=True
                )
            )
        )

    async def _async_update(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Poll the device."""

    @callback
    def _async_handle_unavailable(
        self, service_info: bluetooth.BluetoothServiceInfoBleak
    ) -> None:
        """Handle the device going unavailable."""

    @callback
    def _async_handle_bluetooth_event(
        self,
        service_info: bluetooth.BluetoothServiceInfoBleak,
        change: bluetooth.BluetoothChange,
    ) -> None:
        """Handle a Bluetooth event."""
        # Your device should process incoming advertisement data
```

# Bluetooth APIs

### Subscribing to Bluetooth discoveries

Some integrations may need to know when a device is discovered right away. The Bluetooth integration provides a registration API to receive callbacks when a new device is discovered that matches specific key values. The same format for `bluetooth` in [`manifest.json`](https://developers.home-assistant.io/docs/creating_integration_manifest#bluetooth) is used for matching. In addition to the matchers used in the `manifest.json`, `address` can also be used as a matcher.

The function `bluetooth.async_register_callback` is provided to enable this ability. The function returns a callback that will cancel the registration when called.

The below example shows registering to get callbacks when a Switchbot device is nearby.

The below example shows registering to get callbacks for HomeKit devices.

The below example shows registering to get callbacks for Nespresso Prodigios.

The below example shows registering to get callbacks for a device with the address `44:33:11:22:33:22`.

### Fetch the shared BleakScanner instance

Integrations that need an instance of a `BleakScanner` should call the `bluetooth.async_get_scanner` API. This API returns a wrapper around a single `BleakScanner` that allows integrations to share without overloading the system.

```python
from homeassistant.components import bluetooth

scanner = bluetooth.async_get_scanner(hass)
```

### Determine if a scanner is running

The Bluetooth integration may be set up but has no connectable adapters or remotes. The `bluetooth.async_scanner_count` API can be used to determine if there is a scanner running that will be able to receive advertisements or generate `BLEDevice` s that can be used to connect to the device. An integration may want to raise a more helpful error during setup if there are no scanners that will generate connectable `BLEDevice` objects.

```python
from homeassistant.components import bluetooth

count = bluetooth.async_scanner_count(hass, connectable=True)
```

### Subscribing to unavailable callbacks

To get a callback when the Bluetooth stack can no longer see a device, call the `bluetooth.async_track_unavailable` API. For performance reasons, it may take up to five minutes to get a callback once the device is no longer seen.

If the `connectable` argument is set to `True`, if any `connectable` controller can reach the device, the device will be considered available. If only non-connectable controllers can reach the device, the device will be considered unavailable. If the argument is set to `False`, the device will be considered available if any controller can see it.

### Finding out the availability timeout

Availability is based on the time since the device's last known broadcast. This timeout is learned automatically based on the device's regular broadcasting pattern. You can find out this with the `bluetooth.async_get_learned_advertising_interval` API.

```python
from homeassistant.components import bluetooth

learned_interval = bluetooth.async_get_learned_advertising_interval(hass, "44:44:33:11:23:42")
```

If the advertising interval is not yet known, this will return `None`. In that case, unavailability tracking will try the fallback interval for that address. The below example returns the interval that has been set manually by an integration:

```python
from homeassistant.components import bluetooth

bluetooth.async_set_fallback_availability_interval(hass, "44:44:33:11:23:42", 64.0)

fallback_interval = bluetooth.async_get_fallback_availability_interval(hass, "44:44:33:11:23:42")
```

If there is no learned interval or fallback interval for the device, a hardcoded safe default interval is used:

### Fetching the bleak BLEDevice from the address

Integrations should avoid the overhead of starting an additional scanner to resolve the address by calling the `bluetooth.async_ble_device_from_address` API, which returns a `BLEDevice` for the nearest configured `bluetooth` adapter that can reach the device. If no adapters can reach the device, the `bluetooth.async_ble_device_from_address` API, will return `None`.

Suppose the integration wants to receive data from `connectable` and non-connectable controllers. In that case, it can exchange the `BLEDevice` for a `connectable` one when it wants to make an outgoing connection as long as at least one `connectable` controller is in range.

```python
from homeassistant.components import bluetooth

ble_device = bluetooth.async_ble_device_from_address(hass, "44:44:33:11:23:42", connectable=True)
```

### Fetching the latest BluetoothServiceInfoBleak for a device

The latest advertisement and device data are available with the `bluetooth.async_last_service_info` API, which returns a `BluetoothServiceInfoBleak` from the scanner with the best RSSI of the requested connectable type.

```python
from homeassistant.components import bluetooth

service_info = bluetooth.async_last_service_info(hass, "44:44:33:11:23:42", connectable=True)
```

### Checking if a device is present

To determine if a device is still present, call the `bluetooth.async_address_present` API. This call is helpful if your integration needs the device to be present to consider it available.

```python
from homeassistant.components import bluetooth

bluetooth.async_address_present(hass, "44:44:33:11:23:42", connectable=True)
```

### Fetching all discovered devices

To access the list of previous discoveries, call the `bluetooth.async_discovered_service_info` API. Only devices that are still present will be in the cache.

```python
from homeassistant.components import bluetooth

service_infos = bluetooth.async_discovered_service_info(hass, connectable=True)
```

To access the list of previous discoveries and advertisement data received by each adapter independently, call the `bluetooth.async_scanner_devices_by_address` API. The call returns a list of `BluetoothScannerDevice` objects. The same device and advertisement data may appear multiple times, once per Bluetooth adapter that reached it.

### Triggering rediscovery of devices

When a configuration entry or device is removed from Home Assistant, trigger rediscovery of its address to make sure they are available to be set up without restarting Home Assistant. You can make use of the Bluetooth connection property of the device registry if your integration manages multiple devices per configuration entry.

```python
from homeassistant.components import bluetooth

bluetooth.async_rediscover_address(hass, "44:44:33:11:23:42")
```

To wait for a specific advertisement, call the `bluetooth.async_process_advertisements` API.

Integrations that provide a Bluetooth adapter should add `bluetooth` in [`dependencies`](https://developers.home-assistant.io/docs/creating_integration_manifest#dependencies) in their [`manifest.json`](https://developers.home-assistant.io/docs/creating_integration_manifest) and be added to [`after_dependencies`](https://developers.home-assistant.io/docs/creating_integration_manifest#after-dependencies) to the `bluetooth_adapters` integration.

To register an external scanner, call the `bluetooth.async_register_scanner` API. The scanner must inherit from `BaseHaScanner`.

If the scanner needs connection slot management to avoid overloading the adapter, pass the number of connection slots as an integer value via the `connection_slots` argument.

The scanner will need to feed advertisement data to the central Bluetooth manager in the form of `BluetoothServiceInfoBleak` objects. The callback needed to send the data to the central manager can be obtained with the `bluetooth.async_get_advertisement_callback` API.

### Removing an external scanner

To permanently remove an external scanner, call the `bluetooth.async_remove_scanner` API with the `source` (MAC address) of the scanner. This will remove any advertisement history associated with the scanner.

```python
from homeassistant.components import bluetooth

bluetooth.async_remove_scanner(hass, source)
```
