"""Scene effects parameter handling for Neewer lights."""

from __future__ import annotations

import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)

# Effect ID constants
EFFECT_LIGHTNING = 0x01
EFFECT_PAPARAZZI = 0x02
EFFECT_DEFECTIVE_BULB = 0x03
EFFECT_EXPLOSION = 0x04
EFFECT_WELDING = 0x05
EFFECT_CCT_FLASH = 0x06
EFFECT_HUE_FLASH = 0x07
EFFECT_CCT_PULSE = 0x08
EFFECT_HUE_PULSE = 0x09
EFFECT_COP_CAR = 0x0A
EFFECT_CANDLELIGHT = 0x0B
EFFECT_HUE_LOOP = 0x0C
EFFECT_CCT_LOOP = 0x0D
EFFECT_INT_LOOP = 0x0E
EFFECT_TV_SCREEN = 0x0F
EFFECT_FIREWORK = 0x10
EFFECT_PARTY = 0x11

# Advanced scene parameter definitions
ADVANCED_SCENE_PARAMS = {
    EFFECT_LIGHTNING: {  # Lightning
        "name": "Lightning",
        "params": ["brightness", "cct", "gm", "speed"],
        "defaults": {"brightness": 100, "cct": 50, "gm": 50, "speed": 5},
    },
    EFFECT_PAPARAZZI: {  # Paparazzi
        "name": "Paparazzi",
        "params": ["brightness", "cct", "gm", "speed"],
        "defaults": {"brightness": 100, "cct": 50, "gm": 50, "speed": 5},
    },
    EFFECT_DEFECTIVE_BULB: {  # Defective bulb
        "name": "Defective Bulb",
        "params": ["brightness", "cct", "gm", "speed"],
        "defaults": {"brightness": 100, "cct": 50, "gm": 50, "speed": 5},
    },
    EFFECT_EXPLOSION: {  # Explosion
        "name": "Explosion",
        "params": ["brightness", "cct", "gm", "speed", "sparks"],
        "defaults": {"brightness": 100, "cct": 50, "gm": 50, "speed": 5, "sparks": 5},
    },
    EFFECT_WELDING: {  # Welding
        "name": "Welding",
        "params": ["brightness_low", "brightness_high", "cct", "gm", "speed"],
        "defaults": {
            "brightness_low": 20,
            "brightness_high": 100,
            "cct": 50,
            "gm": 50,
            "speed": 5,
        },
    },
    EFFECT_CCT_FLASH: {  # CCT flash
        "name": "CCT Flash",
        "params": ["brightness", "cct", "gm", "speed"],
        "defaults": {"brightness": 100, "cct": 50, "gm": 50, "speed": 5},
    },
    EFFECT_HUE_FLASH: {  # HUE flash
        "name": "HUE Flash",
        "params": ["brightness", "hue", "saturation", "speed"],
        "defaults": {"brightness": 100, "hue": 180, "saturation": 100, "speed": 5},
    },
    EFFECT_CCT_PULSE: {  # CCT pulse
        "name": "CCT Pulse",
        "params": ["brightness", "cct", "gm", "speed"],
        "defaults": {"brightness": 100, "cct": 50, "gm": 50, "speed": 5},
    },
    EFFECT_HUE_PULSE: {  # HUE pulse
        "name": "HUE Pulse",
        "params": ["brightness", "hue", "saturation", "speed"],
        "defaults": {"brightness": 100, "hue": 180, "saturation": 100, "speed": 5},
    },
    EFFECT_COP_CAR: {  # Cop Car
        "name": "Cop Car",
        "params": ["brightness", "color_mode", "speed"],
        "defaults": {"brightness": 100, "color_mode": 2, "speed": 5},
    },
    EFFECT_CANDLELIGHT: {  # Candlelight
        "name": "Candlelight",
        "params": ["brightness_low", "brightness_high", "cct", "gm", "speed", "sparks"],
        "defaults": {
            "brightness_low": 20,
            "brightness_high": 80,
            "cct": 27,
            "gm": 50,
            "speed": 3,
            "sparks": 3,
        },
    },
    EFFECT_HUE_LOOP: {  # HUE Loop
        "name": "HUE Loop",
        "params": ["brightness", "hue_low", "hue_high", "speed"],
        "defaults": {"brightness": 100, "hue_low": 0, "hue_high": 360, "speed": 5},
    },
    EFFECT_CCT_LOOP: {  # CCT Loop
        "name": "CCT Loop",
        "params": ["brightness", "cct_low", "cct_high", "speed"],
        "defaults": {"brightness": 100, "cct_low": 27, "cct_high": 65, "speed": 5},
    },
    EFFECT_INT_LOOP: {  # INT loop
        "name": "INT Loop",
        "params": ["brightness_low", "brightness_high", "hue", "speed"],
        "defaults": {
            "brightness_low": 10,
            "brightness_high": 100,
            "hue": 180,
            "speed": 5,
        },
    },
    EFFECT_TV_SCREEN: {  # TV Screen
        "name": "TV Screen",
        "params": ["brightness", "cct", "gm", "speed"],
        "defaults": {"brightness": 100, "cct": 50, "gm": 50, "speed": 8},
    },
    EFFECT_FIREWORK: {  # Firework
        "name": "Firework",
        "params": ["brightness", "color_mode", "speed", "sparks"],
        "defaults": {"brightness": 100, "color_mode": 1, "speed": 5, "sparks": 7},
    },
    EFFECT_PARTY: {  # Party
        "name": "Party",
        "params": ["brightness", "color_mode", "speed"],
        "defaults": {"brightness": 100, "color_mode": 1, "speed": 7},
    },
}


def build_advanced_scene_command(
    effect_id: int, mac_bytes: list[int], brightness: int = 100, **params: Any
) -> list[int]:
    """
    Build advanced scene command with parameters.

    Args:
        effect_id: Scene effect ID (0x01-0x11)
        mac_bytes: Device MAC address bytes
        brightness: Base brightness (0-100)
        **params: Additional scene parameters

    Returns:
        Command bytes list

    """
    if effect_id not in ADVANCED_SCENE_PARAMS:
        msg = f"Unknown advanced scene effect ID: {effect_id}"
        raise ValueError(msg)

    scene_info = ADVANCED_SCENE_PARAMS[effect_id]
    defaults = scene_info["defaults"].copy()

    # Override defaults with provided parameters
    defaults.update(params)
    defaults["brightness"] = brightness

    # Build command based on effect type
    command_data = [0x91]  # Advanced scene command tag

    if effect_id in [
        EFFECT_LIGHTNING,
        EFFECT_PAPARAZZI,
        EFFECT_DEFECTIVE_BULB,
        EFFECT_CCT_FLASH,
        EFFECT_CCT_PULSE,
        EFFECT_TV_SCREEN,
    ]:
        # Command: [0x91, 0x0E, MAC[6], 0x8B, EFFECT_ID, BRR, CCT, GM, SPEED, 0x00]
        command_data.extend(
            [
                0x0E,
                *mac_bytes,
                0x8B,
                effect_id,
                defaults["brightness"],
                defaults["cct"],
                defaults["gm"],
                defaults["speed"],
                0x00,
            ]
        )

    elif effect_id in [EFFECT_HUE_FLASH, EFFECT_HUE_PULSE]:
        # Command format for HUE effects
        hue = defaults["hue"]
        hue_low = hue & 0xFF
        hue_high = (hue >> 8) & 0xFF
        command_data.extend(
            [
                0x0F,
                *mac_bytes,
                0x8B,
                effect_id,
                defaults["brightness"],
                hue_low,
                hue_high,
                defaults["saturation"],
                defaults["speed"],
                0x00,
            ]
        )

    elif effect_id == EFFECT_EXPLOSION:
        # [0x91, 0x0F, MAC[6], 0x8B, EFFECT_ID, BRR, CCT, GM, SPEED, SPARKS, 0x00]
        command_data.extend(
            [
                0x0F,
                *mac_bytes,
                0x8B,
                effect_id,
                defaults["brightness"],
                defaults["cct"],
                defaults["gm"],
                defaults["speed"],
                defaults["sparks"],
                0x00,
            ]
        )

    elif effect_id in [EFFECT_WELDING, EFFECT_CANDLELIGHT]:
        if effect_id == EFFECT_WELDING:
            # Command format for Welding effect
            command_data.extend(
                [
                    0x0F,
                    *mac_bytes,
                    0x8B,
                    effect_id,
                    defaults["brightness_low"],
                    defaults["brightness_high"],
                    defaults["cct"],
                    defaults["gm"],
                    defaults["speed"],
                    0x00,
                ]
            )
        else:  # Candlelight
            # Command format for Candlelight effect
            command_data.extend(
                [
                    0x10,
                    *mac_bytes,
                    0x8B,
                    effect_id,
                    defaults["brightness_low"],
                    defaults["brightness_high"],
                    defaults["cct"],
                    defaults["gm"],
                    defaults["speed"],
                    defaults["sparks"],
                    0x00,
                ]
            )

    elif effect_id in [EFFECT_COP_CAR, EFFECT_PARTY]:
        # [0x91, 0x0E, MAC[6], 0x8B, EFFECT_ID, BRR, COLOR_MODE, SPEED, 0x00, 0x00]
        command_data.extend(
            [
                0x0E,
                *mac_bytes,
                0x8B,
                effect_id,
                defaults["brightness"],
                defaults["color_mode"],
                defaults["speed"],
                0x00,
                0x00,
            ]
        )

    elif effect_id == EFFECT_HUE_LOOP:
        # Command format for HUE Loop effect
        hue_low = defaults["hue_low"]
        hue_high = defaults["hue_high"]
        command_data.extend(
            [
                0x11,
                *mac_bytes,
                0x8B,
                effect_id,
                defaults["brightness"],
                hue_low & 0xFF,
                (hue_low >> 8) & 0xFF,
                hue_high & 0xFF,
                (hue_high >> 8) & 0xFF,
                defaults["speed"],
                0x00,
            ]
        )

    elif effect_id == EFFECT_CCT_LOOP:
        # Command format for CCT Loop effect
        command_data.extend(
            [
                0x0E,
                *mac_bytes,
                0x8B,
                effect_id,
                defaults["brightness"],
                defaults["cct_low"],
                defaults["cct_high"],
                defaults["speed"],
                0x00,
            ]
        )

    elif effect_id == EFFECT_INT_LOOP:
        # [0x91, 0x0F, MAC[6], 0x8B, EFFECT_ID, BRR_LOW, BRR_HIGH, HUE[2], SPEED, 0x00]
        hue = defaults["hue"]
        hue_low = hue & 0xFF
        hue_high = (hue >> 8) & 0xFF
        command_data.extend(
            [
                0x0F,
                *mac_bytes,
                0x8B,
                effect_id,
                defaults["brightness_low"],
                defaults["brightness_high"],
                hue_low,
                hue_high,
                defaults["speed"],
                0x00,
            ]
        )

    elif effect_id == EFFECT_FIREWORK:
        # Command format for Firework effect
        command_data.extend(
            [
                0x0F,
                *mac_bytes,
                0x8B,
                effect_id,
                defaults["brightness"],
                defaults["color_mode"],
                defaults["speed"],
                defaults["sparks"],
                0x00,
                0x00,
            ]
        )

    return command_data


def get_scene_parameters(effect_id: int) -> dict[str, Any]:
    """Get parameter definitions for a scene effect."""
    return ADVANCED_SCENE_PARAMS.get(effect_id, {})


def validate_scene_parameters(effect_id: int, **params: Any) -> dict[str, Any]:
    """Validate and normalize scene parameters."""
    if effect_id not in ADVANCED_SCENE_PARAMS:
        return {}

    scene_info = ADVANCED_SCENE_PARAMS[effect_id]
    validated = {}

    for param_name in scene_info["params"]:
        if param_name in params:
            value = params[param_name]

            # Validate ranges
            if param_name in ["brightness", "brightness_low", "brightness_high"]:
                validated[param_name] = max(0, min(100, int(value)))
            elif param_name in ["cct", "cct_low", "cct_high"]:
                validated[param_name] = max(27, min(65, int(value)))
            elif param_name == "gm":
                validated[param_name] = max(0, min(100, int(value)))
            elif param_name in ["hue", "hue_low", "hue_high"]:
                validated[param_name] = max(0, min(360, int(value)))
            elif param_name == "saturation":
                validated[param_name] = max(0, min(100, int(value)))
            elif param_name in ["speed", "sparks"]:
                validated[param_name] = max(1, min(10, int(value)))
            elif param_name == "color_mode":
                validated[param_name] = max(0, min(4, int(value)))
            else:
                validated[param_name] = value

    return validated
