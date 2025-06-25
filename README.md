# Home Assistant Neewer Light Integration

This repository contains a custom component for Home Assistant that provides control over Neewer LED lights via Bluetooth Low Energy (BLE).

## Features

*   Control Neewer lights (on/off, brightness, color temperature, RGB, scenes).
*   Supports various Neewer light models.
*   Utilizes Home Assistant's Bluetooth integration for reliable communication.

## Installation

### HACS (Recommended)

1.  Open HACS in your Home Assistant instance.
2.  Go to "Integrations" and click the three dots in the top right corner, then select "Custom repositories".
3.  Add this repository's URL (`https://github.com/your-github-username/hass-neewer`) as a "Integration" type.
4.  Search for "Neewer Light" in HACS and install it.
5.  Restart Home Assistant.

### Manual Installation

1.  Copy the `custom_components/neewer` folder from this repository into your Home Assistant `config/custom_components` directory.
2.  Restart Home Assistant.

## Configuration

1.  After installation and restarting Home Assistant, go to "Configuration" -> "Integrations".
2.  Click the "+ Add Integration" button.
3.  Search for "Neewer Light" and follow the on-screen instructions to set up your Neewer lights.
    *   The integration will discover compatible Neewer lights via Bluetooth.
    *   You may need to provide the MAC address for some advanced features, though basic control will attempt to work without it.

## Supported Devices

This integration aims to support a wide range of Neewer lights. Capabilities (RGB, CCT, scenes, etc.) are determined by a remote database of device specifications.

## Development

### Project Structure

File | Purpose | Documentation
-- | -- | --
`.devcontainer.json` | Used for development/testing with Visual Studio Code. | [Documentation](https://code.visualstudio.com/docs/remote/containers)
`.github/ISSUE_TEMPLATE/*.yml` | Templates for the issue tracker | [Documentation](https://help.github.com/en/github/building-a-strong-community/configuring-issue-templates-for-your-repository)
`custom_components/neewer/*` | Integration files for Neewer lights. | [Documentation](https://developers.home-assistant.io/docs/creating_component_index)
`CONTRIBUTING.md` | Guidelines on how to contribute. | [Documentation](https://help.github.com/en/github/building-a-strong-community/setting-guidelines-for-repository-contributors)
`LICENSE` | The license file for the project. | [Documentation](https://help.github.com/en/github/creating-cloning-and-archiving-repositories/licensing-a-repository)
`README.md` | The file you are reading now, contains info about the integration, installation and configuration instructions. | [Documentation](https://help.github.com/en/github/writing-on-github/basic-writing-and-formatting-syntax)
`requirements.txt` | Python packages used for development/lint/testing this integration. | [Documentation](https://pip.pypa.io/en/stable/user_guide/#requirements-files)

### Getting Started with Development

1.  Clone this repository.
2.  Open the repository in a Visual Studio Code devcontainer (Preferably with the "`Dev Containers: Clone Repository in Named Container Volume...`" option).
3.  Run the `scripts/develop` to start Home Assistant and test out the integration.

## Contributing

Contributions are welcome! Please see `CONTRIBUTING.md` for guidelines.

## Next Steps

*   Add more comprehensive tests for various light models and command types.
*   Improve MAC address discovery reliability across different platforms.
*   Enhance scene control and parameter handling for advanced effects.
*   Add brand images (logo/icon) to https://github.com/home-assistant/brands.
*   Create your first release.
*   Share your integration on the [Home Assistant Forum](https://community.home-assistant.io/).
*   Submit your integration to [HACS](https://hacs.xyz/docs/publish/start).
