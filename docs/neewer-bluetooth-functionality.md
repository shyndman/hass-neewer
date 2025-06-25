# Neewer Light Bluetooth Protocol Documentation

This document provides comprehensive details for implementing Neewer light control via Bluetooth Low Energy (BLE) in any programming language.

## Bluetooth Service & Characteristics

### Service UUID
```
69400001-B5A3-F393-E0A9-E50E24DCCA99
```

### Characteristics
1. **Device Control Characteristic (Write)**
   - UUID: `69400002-B5A3-F393-E0A9-E50E24DCCA99`
   - Properties: Write with/without response
   - Used for: Sending commands to the light

2. **GATT Characteristic (Notify)**
   - UUID: `69400003-B5A3-F393-E0A9-E50E24DCCA99`
   - Properties: Notify
   - Used for: Receiving notifications from the light

## Device Discovery

### Valid Device Names
Neewer lights can be identified by device names containing:
- `nwr`
- `neewer`
- `sl`
- Starting with `nw-`
- Starting with `neewer-`
- `nee`

All name comparisons are case-insensitive.

## Command Structure

All commands follow this format:
```
[PREFIX] [COMMAND_TAG] [DATA_LENGTH] [DATA...] [CHECKSUM]
```

### Command Components
- **PREFIX**: Always `0x78` (120 decimal)
- **COMMAND_TAG**: 1 byte command identifier
- **DATA_LENGTH**: 1 byte length of data payload
- **DATA**: Variable length payload
- **CHECKSUM**: 1 byte checksum (sum of all previous bytes & 0xFF)

### Checksum Calculation
```pseudocode
checksum = 0
for each byte in command (excluding checksum byte):
    checksum += byte
checksum = checksum & 0xFF
```

### Command Timing
- **Critical**: Wait 15ms between commands to prevent BLE jamming
- Commands should be sent sequentially, not in parallel

## Power Commands

### Old Format Power Commands
```
Power ON:  [0x78, 0x81, 0x01, 0x01, 0xFB]
Power OFF: [0x78, 0x81, 0x01, 0x02, 0xFC]
```

### New Format Power Commands (with MAC address)
```
Power ON:  [0x78, 0x8D, 0x08, MAC[6], 0x81, 0x01, CHECKSUM]
Power OFF: [0x78, 0x8D, 0x08, MAC[6], 0x81, 0x02, CHECKSUM]
```

Where:
- `MAC[6]` = 6 bytes of device MAC address
- `0x81` = Sub-tag
- `0x01/0x02` = Power on/off

### Determining Power Command Format
Check device database for `newPowerLightCommand` property to determine which format to use.

## CCT (Color Temperature) Commands

### Basic CCT Command (Tag: 0x87)
```
[0x78, 0x87, 0x02, BRIGHTNESS, CCT_VALUE, CHECKSUM]
```

### CCT with GM (Green/Magenta) Support (Tag: 0x90)
```
[0x78, 0x90, 0x0C, MAC[6], 0x87, BRIGHTNESS, CCT_VALUE, GM_VALUE, 0x04, CHECKSUM]
```

### CCT-Only Lights (Separate Commands)
For lights that only support CCT (no RGB):
```
Brightness: [0x78, 0x82, 0x01, BRIGHTNESS, CHECKSUM]
CCT:        [0x78, 0x83, 0x01, CCT_VALUE, CHECKSUM]
```

### CCT Parameters
- **BRIGHTNESS**: 0-100 (0x00-0x64)
- **CCT_VALUE**: Device-specific range (typically 32-56 for 3200K-5600K)
- **GM_VALUE**: -50 to +50, transmitted as 0-100 (add 50 to actual value)

## RGB/HSI Commands

### Old RGB Command (Tag: 0x86)
```
[0x78, 0x86, 0x04, HUE_LOW, HUE_HIGH, SATURATION, BRIGHTNESS, CHECKSUM]
```

### New RGB Command (Tag: 0x8F)
```
[0x78, 0x8F, 0x0C, MAC[6], 0x86, HUE_LOW, HUE_HIGH, SATURATION, BRIGHTNESS, 0x00, CHECKSUM]
```

### RGB Parameters
- **HUE**: 0-360 degrees, split into low/high bytes (little-endian)
- **SATURATION**: 0-100 (0x00-0x64)
- **BRIGHTNESS**: 0-100 (0x00-0x64)

### Determining RGB Command Format
Check device database for `newRGBLightCommand` property.

## Scene/Effects Commands

### Basic Scene Command (Tag: 0x88)
```
[0x78, 0x88, 0x02, BRIGHTNESS, SCENE_ID, CHECKSUM]
```

### Advanced Scene Command (Tag: 0x91)
```
[0x78, 0x91, DATA_LENGTH, MAC[6], 0x8B, SCENE_ID, PARAMETERS..., CHECKSUM]
```

### Scene IDs (Basic 9-effect lights)
1. `0x01` - Squad Car
2. `0x02` - Ambulance
3. `0x03` - Fire Engine
4. `0x04` - Fireworks
5. `0x05` - Party
6. `0x06` - Candle Light
7. `0x07` - Paparazzi
8. `0x08` - Screen
9. `0x09` - Lightning

### Advanced Scene IDs (17-effect lights)
1. `0x01` - Lighting (BRR, CCT, SPEED)
2. `0x02` - Paparazzi (BRR, CCT, GM, SPEED)
3. `0x03` - Defective bulb (BRR, CCT, GM, SPEED)
4. `0x04` - Explosion (BRR, CCT, GM, SPEED, SPARKS)
5. `0x05` - Welding (BRR_LOW, BRR_HIGH, CCT, GM, SPEED)
6. `0x06` - CCT flash (BRR, CCT, GM, SPEED)
7. `0x07` - HUE flash (BRR, HUE[2], SAT, SPEED)
8. `0x08` - CCT pulse (BRR, CCT, GM, SPEED)
9. `0x09` - HUE pulse (BRR, HUE[2], SAT, SPEED)
10. `0x0A` - Cop Car (BRR, COLOR_MODE, SPEED)
11. `0x0B` - Candlelight (BRR_LOW, BRR_HIGH, CCT, GM, SPEED, SPARKS)
12. `0x0C` - HUE Loop (BRR, HUE_LOW[2], HUE_HIGH[2], SPEED)
13. `0x0D` - CCT Loop (BRR, CCT_LOW, CCT_HIGH, SPEED)
14. `0x0E` - INT loop (BRR_LOW, BRR_HIGH, HUE[2], SPEED)
15. `0x0F` - TV Screen (BRR, CCT, GM, SPEED)
16. `0x10` - Firework (BRR, COLOR_MODE, SPEED, SPARKS)
17. `0x11` - Party (BRR, COLOR_MODE, SPEED)

### Scene Parameter Types
- **BRR**: Brightness (0-100)
- **CCT**: Color temperature (device range)
- **GM**: Green/Magenta (-50 to +50, send as 0-100)
- **HUE[2]**: Hue as 2-byte little-endian (0-360)
- **SAT**: Saturation (0-100)
- **SPEED**: Effect speed (1-10)
- **SPARKS**: Spark intensity (1-10)
- **COLOR_MODE**: Color options (0-4 for Cop Car, 0-2 for Firework/Party)

## Control Modes

Lights operate in different modes:

1. **CCT Mode (0x01)**: Bi-color temperature control
2. **HSI Mode (0x02)**: RGB color control
3. **SCE Mode (0x03)**: Scene/effects mode
4. **SRC Mode (0x04)**: Light source presets

## Notifications

### Channel Update Notifications
Format: `[0x78, 0x01, 0x01, CHANNEL, CHECKSUM]`

- Received when light's channel/scene changes
- **CHANNEL**: 0-based channel (add 1 for 1-based scene ID)
- Must validate checksum before processing

### Notification Setup
1. Enable notifications on GATT characteristic
2. Send read request: `[0x78, 0x84, 0x00, 0xFC]`

## Device Identification & Capabilities

### Device Name Parsing for Model Identification
Neewer lights follow consistent naming patterns for reliable model extraction:

**Parsing Rules:**
1. **"NWR" prefix**: Drop first 4 characters → project name
2. **"NEEWER" prefix**: Drop first 7 characters → project name
3. **"NW-YYYYMMDD&XXXXXXXX" format**: Extract date code, lookup in mapping table
4. **"NW-" prefix**: Drop first 3 characters → project name
5. **Other formats**: Use full name as project name

**Example Transformations:**
- `"NEEWER-SL90"` → `project_name = "SL90"`
- `"NW-20220014&00000000"` → `project_name = "CB60B"` (via date code lookup)
- `"NWR-RGB660 PRO"` → `project_name = "RGB660 PRO"`

**Nick Name Construction:**
`nick_name = project_name + "-" + last_6_chars_of_identifier`

### Light Type Mapping
After extracting the project name, map to a numeric Light Type ID using extensive pattern matching:

**Pattern Matching Examples:**
- Names containing "CB60 RGB" → Light Type 22
- Names containing "SL90 Pro" → Light Type 34
- Names containing "SL90" (not Pro) → Light Type 14
- Names containing "RGB1" → Light Type 8
- Names containing "MS60C" → Light Type 25

The complete mapping involves checking for specific model patterns in order of specificity, with fallback rules for disambiguation.

### Device Capabilities Database

**Primary Source: Remote GitHub Database**
- **URL**: `https://raw.githubusercontent.com/keefo/NeewerLite/main/Database/lights.json`
- **Local Cache**: Store in application data directory as `database.json`
- **Refresh Interval**: 8 hours (28800 seconds)
- **Fallback**: Use cached version if download fails

**Database Structure:**
```json
{
  "version": 2,
  "lights": [
    {
      "type": 22,
      "link": "https://neewer.com/products/...",
      "image": "https://example.com/light22.jpg",
      "supportRGB": true,
      "supportCCTGM": true,
      "supportMusic": false,
      "support17FX": true,
      "support9FX": false,
      "cctRange": {"min": 32, "max": 56},
      "newPowerLightCommand": true,
      "newRGBLightCommand": true
    }
  ]
}
```

**Key Capability Flags:**
- `supportRGB`: Device supports RGB color control
- `supportCCTGM`: Supports Green/Magenta adjustment in CCT mode
- `support17FX`: Advanced 17-effect scenes (vs `support9FX` for basic 9 effects)
- `newPowerLightCommand`: Use new MAC-based power command format
- `newRGBLightCommand`: Use new MAC-based RGB command format
- `cctRange`: Color temperature range in device-specific units (min/max)

**Scene Configuration Files**
Separate files (like `lights_db.json`) contain scene parameter definitions:
- **Purpose**: Define which parameters each scene effect requires
- **Key Structure**: `{"light_type_id": [scene_array]}`
- **Content**: Array of 17 scene objects for advanced lights
- **Usage**: Determine required parameters (brightness, CCT, GM, hue, etc.) per scene
- **Not primary capabilities**: This is scene-specific configuration, not device capabilities

### MAC Address Discovery & Critical Limitations

**Important: MAC addresses are NOT reliably discoverable on all platforms and devices.**

**Discovery Approach:**
1. Use platform-specific Bluetooth APIs to enumerate connected devices
2. Match device name to discover associated MAC address
3. Implement retry mechanism (recommended: up to 10 attempts)
4. Accept that discovery may fail even for compatible devices

**Platform-Specific Methods:**
- **macOS**: IOBluetooth framework (limited reliability)
- **Linux**: BlueZ D-Bus interface
- **Windows**: Windows Bluetooth APIs

**Known Limitations:**
- Source code includes comment: *"macOS Bluetooth Framework does not provide a way to get MAC"*
- MAC discovery failure is expected behavior, not an error condition
- Some newer devices require MAC for advanced features but may not expose it

**Graceful Degradation Strategy:**
When MAC address is unavailable:
1. Fall back to old command formats (without MAC)
2. Limit functionality to basic features
3. Some advanced scenes/effects may be unavailable
4. Power and basic color control should still work

**Command Format Selection Logic:**
```
if (device_capabilities.newPowerLightCommand AND mac_address_available):
    use new power command format
else:
    use old power command format

if (device_capabilities.newRGBLightCommand AND mac_address_available):
    use new RGB command format
else:
    use old RGB command format
```

### Implementation Workflow

1. **Device Discovery**: Scan for devices matching Neewer name patterns
2. **Model Extraction**: Parse device name using prefix rules to extract project name
3. **Light Type Mapping**: Apply pattern matching logic to determine numeric light type ID
4. **Capability Lookup**: Download and cache remote database, lookup capabilities by light type
5. **MAC Discovery**: Attempt platform-specific MAC discovery (expect potential failure)
6. **Command Selection**: Choose appropriate command formats based on capabilities and MAC availability
7. **Feature Limitation**: Gracefully handle reduced functionality when MAC unavailable

**Critical Notes:**
- Device capabilities cannot be queried from the device itself
- The remote database is the definitive source for all device capabilities
- MAC address discovery failure should not prevent basic light control
- Implement robust fallback mechanisms for maximum device compatibility

## Command Reference

### Command Tags
```
0x78 - Command prefix (all commands)
0x81 - Power control
0x82 - CCT-only brightness
0x83 - CCT-only temperature
0x84 - Read request
0x86 - RGB control (old format)
0x87 - CCT control
0x88 - Basic scene control
0x89 - HSV data (unused)
0x8D - New power control
0x8F - RGB control (new format)
0x90 - CCT with GM control
0x91 - Advanced scene control
```

### Sub-tags
```
0x81 - Power sub-tag
0x86 - RGB sub-tag (new format)
0x87 - CCT sub-tag (with GM)
0x8B - Scene sub-tag (advanced)
```

## Implementation Notes

### Connection Management
1. Scan for devices with valid names
2. Connect to device
3. Discover service and characteristics
4. Enable notifications on GATT characteristic
5. Send initial read request

### Error Handling
- Validate all incoming notifications with checksum
- Handle connection drops gracefully
- Implement retry logic for failed commands
- Respect 15ms command timing

### Device Database
Maintain database of device specifications:
- Light types and capabilities
- CCT ranges
- Supported features
- Command format preferences

### Testing
Use fake light configurations for development:
- Multiple device types
- Various capability combinations
- MAC address scenarios

## Example Implementation Pseudocode

```pseudocode
class NeewerLight:
    service_uuid = "69400001-B5A3-F393-E0A9-E50E24DCCA99"
    control_char_uuid = "69400002-B5A3-F393-E0A9-E50E24DCCA99"
    notify_char_uuid = "69400003-B5A3-F393-E0A9-E50E24DCCA99"

    def calculate_checksum(data):
        return sum(data) & 0xFF

    def send_power_on():
        cmd = [0x78, 0x81, 0x01, 0x01]
        cmd.append(calculate_checksum(cmd))
        write_to_control_characteristic(cmd)
        wait(15ms)

    def send_cct_command(brightness, cct):
        cmd = [0x78, 0x87, 0x02, brightness, cct]
        cmd.append(calculate_checksum(cmd))
        write_to_control_characteristic(cmd)
        wait(15ms)

    def send_rgb_command(brightness, hue, saturation):
        hue_low = hue & 0xFF
        hue_high = (hue >> 8) & 0xFF
        cmd = [0x78, 0x86, 0x04, hue_low, hue_high, saturation, brightness]
        cmd.append(calculate_checksum(cmd))
        write_to_control_characteristic(cmd)
        wait(15ms)
```

This documentation provides all necessary details to implement Neewer light control in any programming language with Bluetooth LE support.
