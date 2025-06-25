# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Setup and Installation
```bash
scripts/setup              # Install Python dependencies
```

### Development Server
```bash
scripts/develop            # Start Home Assistant with debug mode on http://localhost:8123
                          # Sets PYTHONPATH to load custom components from project directory
```

### Code Quality
```bash
scripts/lint              # Format with ruff and auto-fix issues
ruff format .             # Format code only
ruff check . --fix        # Lint and auto-fix only
```

## Architecture Overview

This is a **Home Assistant custom integration** for controlling **Neewer LED lights** via **Bluetooth Low Energy (BLE)**. The integration follows Home Assistant's standard patterns and uses the modern Python development stack.

### Core Architecture Components

**Integration Structure:**
- `custom_components/neewer/` - Main integration directory
- Uses Home Assistant's **config flow** pattern for UI-based setup
- Implements **ActiveBluetoothDataUpdateCoordinator** for BLE device management
- Single platform: **light** with full color/temperature/scene support

**Bluetooth Communication:**
- Service UUID: `69400001-B5A3-F393-E0A9-E50E24DCCA99`
- Manufacturer ID: 89 for device discovery
- Protocol: Custom Neewer BLE commands via `bleak-retry-connector==1.2.0`
- Auto-discovery and reconnection handling
- Robust command format selection with fallback mechanisms

**Device Capability Management:**
- Remote database from GitHub with 8-hour refresh cycle
- Local cache fallback with HA's storage system
- Type-based capability determination with comprehensive device name parsing
- MAC address discovery with platform-specific methods

### Key Files and Their Purposes

**Core Integration Files:**
- `__init__.py` - Entry point, coordinator setup, and service registration
- `config_flow.py` - Device discovery and configuration UI
- `coordinator.py` - BLE connection and data update management (ActiveBluetoothDataUpdateCoordinator)
- `light.py` - Home Assistant light platform with advanced features
- `neewer_device.py` - Modern device library with robust command handling
- `neewer_light.py` - Legacy device implementation (for reference)

**Advanced Features:**
- `data.py` - Dynamic database management with remote updates
- `mac_discovery.py` - Platform-specific MAC address discovery
- `scene_effects.py` - Advanced 17-effect scene parameter handling
- `services.yaml` - Custom services for GM adjustment and advanced effects

**Configuration:**
- `const.py` - Centralized constants for all modules
- `manifest.json` - Integration metadata, dependencies, and BLE service definitions
- `translations/en.json` - UI text translations

## Development Environment

**Technology Stack:**
- Python 3.13 (configured in .ruff.toml)
- Home Assistant 2025.2.4
- VS Code Dev Container with full HA development environment
- Ruff for linting/formatting (replaces Black, isort, flake8)

**Code Standards:**
- Ruff configuration based on Home Assistant core standards
- All lint rules enabled with specific ignores for formatter compatibility
- Max complexity: 25 (McCabe)
- Type hints required (Python 3.13 target)

**Development Setup:**
- Dev container automatically configures Python environment
- Port 8123 forwarded for Home Assistant web interface
- Custom components loaded via PYTHONPATH modification
- Debug mode enabled by default in development server

## Integration-Specific Patterns

**BLE Device Lifecycle:**
1. Discovery via service UUID and manufacturer ID
2. Enhanced device info gathering with MAC discovery
3. Connection establishment with retry logic via bleak-retry-connector
4. Capability detection via remote database lookup
5. Periodic polling and automatic reconnection
6. Graceful disconnection on shutdown

**Device Capability System:**
- Remote database fetched from GitHub with 8-hour refresh cycle
- Comprehensive device name parsing (NWR-, NEEWER-, NW- prefixes, date codes)
- Light type mapping to numeric IDs with extensive pattern matching
- Feature availability determines UI controls and commands
- MAC address discovery for advanced command support

**Command Format Selection:**
- Robust fallback mechanism (new format → old format)
- Error handling with automatic retry using alternative commands
- MAC-based commands when available, graceful degradation when not
- Platform-specific MAC discovery (macOS, Linux, Windows)

**Advanced Features:**
- Green/Magenta (GM) adjustment for CCT lights
- 17-effect advanced scenes with full parameter control
- Custom services for fine-grained control
- Comprehensive scene parameter validation and command building

**Home Assistant Integration:**
- Domain: `neewer`
- IoT class: `local_push` (local communication with push updates)
- Dependencies: Home Assistant's `bluetooth` integration
- ActiveBluetoothDataUpdateCoordinator pattern compliance
- Single light platform with full color/temperature/brightness/scene/GM support
- Custom services: `set_gm`, `set_advanced_effect`