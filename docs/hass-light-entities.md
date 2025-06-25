# Light Entity

A ==light== entity controls the brightness, hue and saturation color value, white value, color temperature and effects of a ==light== source. Derive platform entities from [`homeassistant.components.==light==.==Light==Entity`](https://github.com/home-assistant/core/blob/dev/homeassistant/components/light/__init__.py).

## Properties

| Name | Type | Default | Description |
| --- | --- | --- | --- |
| brightness | `int \| None` | `None` | The brightness of this ==light== between 1..255 |
| color\_mode | `ColorMode \| None` | `None` | The color mode of the ==light==. The returned color mode must be present in the `supported_color_modes` property unless the ==light== is rendering an effect. |
| color\_temp\_kelvin | `int \| None` | `None` | The CT color value in K. This property will be copied to the ==light== 's state attribute when the ==light== 's color mode is set to `ColorMode.COLOR_TEMP` and ignored otherwise. |
| effect | `str \| None` | `None` | The current effect. Should be `EFFECT_OFF` if the ==light== supports effects and no effect is currently rendered. |
| effect\_list | `list[str] \| None` | `None` | The list of supported effects. |
| hs\_color | `tuple[float, float] \| None` | `None` | The hue and saturation color value (float, float). This property will be copied to the ==light== 's state attribute when the ==light== 's color mode is set to `ColorMode.HS` and ignored otherwise. |
| is\_on | `bool \| None` | `None` | If the ==light== entity is on or not. |
| max\_color\_temp\_kelvin | `int \| None` | `None` | The coldest color\_temp\_kelvin that this ==light== supports. |
| min\_color\_temp\_kelvin | `int \| None` | `None` | The warmest color\_temp\_kelvin that this ==light== supports. |
| rgb\_color | `tuple[int, int, int] \| None` | `None` | The rgb color value (int, int, int). This property will be copied to the ==light== 's state attribute when the ==light== 's color mode is set to `ColorMode.RGB` and ignored otherwise. |
| rgbw\_color | `tuple[int, int, int, int] \| None` | `None` | The rgbw color value (int, int, int, int). This property will be copied to the ==light== 's state attribute when the ==light== 's color mode is set to `ColorMode.RGBW` and ignored otherwise. |
| rgbww\_color | `tuple[int, int, int, int, int] \| None` | `None` | The rgbww color value (int, int, int, int, int). This property will be copied to the ==light== 's state attribute when the ==light== 's color mode is set to `ColorMode.RGBWW` and ignored otherwise. |
| supported\_color\_modes | `set[ColorMode] \| None` | `None` | Flag supported color modes. |
| xy\_color | `tuple[float, float] \| None` | `None` | The xy color value (float, float). This property will be copied to the ==light== 's state attribute when the ==light== 's color mode is set to `ColorMode.XY` and ignored otherwise. |

## Color modes

New integrations must implement both `color_mode` and `supported_color_modes`. If an integration is upgraded to support color mode, both `color_mode` and `supported_color_modes` should be implemented.

Supported color modes are defined by using values in the `ColorMode` enum.

If a ==light== does not implement the `supported_color_modes`, the `==Light==Entity` will attempt deduce it based on deprecated flags in the `supported_features` property:

- Start with an empty set
- If `SUPPORT_COLOR_TEMP` is set, add `ColorMode.COLOR_TEMP`
- If `SUPPORT_COLOR` is set, add `ColorMode.HS`
- If `SUPPORT_WHITE_VALUE` is set, add `ColorMode.RGBW`
- If `SUPPORT_BRIGHTNESS` is set and no color modes have yet been added, add `ColorMode.BRIGHTNESS`
- If no color modes have yet been added, add `ColorMode.ONOFF`

If a ==light== does not implement the `color_mode`, the `==Light==Entity` will attempt to deduce it based on which of the properties are set and which are `None`:

- If `supported_color_modes` includes `ColorMode.RGBW` and `white_value` and `hs_color` are both not None: `ColorMode.RGBW`
- Else if `supported_color_modes` includes `ColorMode.HS` and `hs_color` is not None: `ColorMode.HS`
- Else if `supported_color_modes` includes `ColorMode.COLOR_TEMP` and `color_temp` is not None: `ColorMode.COLOR_TEMP`
- Else if `supported_color_modes` includes `ColorMode.BRIGHTNESS` and `brightness` is not None: `ColorMode.BRIGHTNESS`
- Else if `supported_color_modes` includes `ColorMode.ONOFF`: `ColorMode.ONOFF`
- Else: ColorMode.UNKNOWN

| Value | Description |
| --- | --- |
| `ColorMode.UNKNOWN` | The ==light== 's color mode is not known. |
| `ColorMode.ONOFF` | The ==light== can be turned on or off. This mode must be the only supported mode if supported by the ==light==. |
| `ColorMode.BRIGHTNESS` | The ==light== can be dimmed. This mode must be the only supported mode if supported by the ==light==. |
| `ColorMode.COLOR_TEMP` | The ==light== can be dimmed and its color temperature is present in the state. |
| `ColorMode.HS` | The ==light== can be dimmed and its color can be adjusted. The ==light== 's brightness can be set using the `brightness` parameter and read through the `brightness` property. The ==light== 's color can be set using the `hs_color` parameter and read through the `hs_color` property. `hs_color` is an (h, s) tuple (no brightness). |
| `ColorMode.RGB` | The ==light== can be dimmed and its color can be adjusted. The ==light== 's brightness can be set using the `brightness` parameter and read through the `brightness` property. The ==light== 's color can be set using the `rgb_color` parameter and read through the `rgb_color` property. `rgb_color` is an (r, g, b) tuple (not normalized for brightness). |
| `ColorMode.RGBW` | The ==light== can be dimmed and its color can be adjusted. The ==light== 's brightness can be set using the `brightness` parameter and read through the `brightness` property. The ==light== 's color can be set using the `rgbw_color` parameter and read through the `rgbw_color` property. `rgbw_color` is an (r, g, b, w) tuple (not normalized for brightness). |
| `ColorMode.RGBWW` | The ==light== can be dimmed and its color can be adjusted. The ==light== 's brightness can be set using the `brightness` parameter and read through the `brightness` property. The ==light== 's color can be set using the `rgbww_color` parameter and read through the `rgbww_color` property. `rgbww_color` is an (r, g, b, cw, ww) tuple (not normalized for brightness). |
| `ColorMode.WHITE` | The ==light== can be dimmed and its color can be adjusted. In addition, the ==light== can be set to white mode. The ==light== 's brightness can be set using the `brightness` parameter and read through the `brightness` property. The ==light== can be set to white mode by using the `white` parameter with the desired brightness as value. Note that there's no `white` property. If both `brighthness` and `white` are present in a service action call, the `white` parameter will be updated with the value of `brightness`. If this mode is supported, the ==light== *must* also support at least one of `ColorMode.HS`, `ColorMode.RGB`, `ColorMode.RGBW`, `ColorMode.RGBWW` or `ColorMode.XY` and *must not* support `ColorMode.COLOR_TEMP`. |
| `ColorMode.XY` | The ==light== can be dimmed and its color can be adjusted. The ==light== 's brightness can be set using the `brightness` parameter and read through the `brightness` property. The ==light== 's color can be set using the `xy_color` parameter and read through the `xy_color` property. `xy_color` is an (x, y) tuple. |

Note that in color modes `ColorMode.RGB`, `ColorMode.RGBW` and `ColorMode.RGBWW` there is brightness information both in the ==light== 's `brightness` property and in the color. As an example, if the ==light== 's brightness is 128 and the ==light== 's color is (192, 64, 32), the overall brightness of the ==light== is: 128/255 \* max(192, 64, 32)/255 = 38%.

If the ==light== is in mode `ColorMode.HS`, `ColorMode.RGB` or `ColorMode.XY`, the ==light== 's state attribute will contain the ==light== 's color expressed in `hs`, `rgb` and `xy` color format. Note that when the ==light== is in mode `ColorMode.RGB`, the `hs` and `xy` state attributes only hold the chromaticity of the `rgb` color as the `hs` and `xy` pairs do not hold brightness information.

If the ==light== is in mode `ColorMode.RGBW` or `ColorMode.RGBWW`, the ==light== 's state attribute will contain the ==light== 's color expressed in `hs`, `rgb` and `xy` color format. The color conversion is an approximation done by adding the white channels to the color.

### White color modes

There are two white color modes, `ColorMode.COLOR_TEMP` and `ColorMode.WHITE`. The difference between the two modes is that `ColorMode.WHITE` does not allow adjusting the color temperature whereas `ColorMode.COLOR_TEMP` does allow adjusting the color temperature.

A lamp with adjustable color temperature is typically implemented by at least two banks of LEDs, with different color temperature, typically one bank of warm-white LEDs and one bank of cold-white LEDs. A ==light== with non-adjustable color temperature typically only has a single bank of white LEDs.

### Color mode when rendering effects

When rendering an effect, the `color_mode` should be set according to the adjustments supported by the effect. If the effect does not support any adjustments, the `color_mode` should be set to `ColorMode.ONOFF`. If the effect allows adjusting the brightness, the `color_mode` should be set to `ColorMode.BRIGHTNESS`.

When rendering an effect, it's allowed to set the `color_mode` to a more restrictive mode than the color modes indicated by the `supported_color_mode` property:

- A ==light== which supports colors is allowed to set color\_mode to `ColorMode.ONOFF` or `ColorMode.BRIGHTNESS` when controlled by an effect
- A ==light== which supports brightness is allowed to set color\_mode to `ColorMode.ONOFF` when controlled by an effect

## Supported features

Supported features are defined by using values in the `==Light==EntityFeature` enum and are combined using the bitwise or (`|`) operator.

| Value | Description |
| --- | --- |
| `EFFECT` | Controls the effect a ==light== source shows |
| `FLASH` | Controls the duration of a flash a ==light== source shows |
| `TRANSITION` | Controls the duration of transitions between color and effects |

## Methods

### Turn on light device

```python
class MyLightEntity(LightEntity):
    def turn_on(self, **kwargs):
        """Turn the device on."""

    async def async_turn_on(self, **kwargs):
        """Turn device on."""
```

Note that there's no `color_mode` passed to the `async_turn_on` method, instead only a single color attribute is allowed. It is guaranteed that the integration will only receive a single color attribute in a `turn_on` call, which is guaranteed to be supported by the ==light== according to the ==light== 's `supported_color_modes` property. To ensure this, colors in the service action call will be translated before the entity's `async_turn_on` method is called if the ==light== doesn't support the corresponding color mode:

| Color type | Translation |
| --- | --- |
| color\_temp | Will be removed from the service action call if not supported and translated to `hs_color`, `rgb_color`, `rgbw_color`, `rgbww_color` or `xy_color` if supported by the ==light==. |
| hs\_color | Will be removed from the service action call if not supported and translated to `rgb_color`, `rgbw_color`, `rgbww_color` or `xy_color` if supported by the ==light==. |
| rgb\_color | Will be removed from the service action call if not supported and translated to `rgbw_color`, `rgbww_color`, `hs_color` or `xy_color` if supported by the ==light==. |
| rgbw\_color | Will be removed from the service action call if not supported. |
| rgbww\_color | Will be removed from the service action call if not supported. |
| xy\_color | Will be removed from the service action call if not supported and translated to `hs_color`, `rgb_color`, `rgbw_color` or `rgbww_color` if supported by the ==light==. |

### Turn Off Light Device

```python
class MyLightEntity(LightEntity):
    def turn_off(self, **kwargs):
        """Turn the device off."""

    async def async_turn_off(self, **kwargs):
        """Turn device off."""
```

-----

Related recent blog entry:

# Changes to light color mode when lights display an effect

## Background

The primary reason for introducing ==light== color modes was that a ==light== 's state should not be ambiguous. As an example, a ==light== which supports color and white with adjustable color temperature must be in either color mode `hs` (for example) or `color_temp`.

However, effects complicate this because when the same ==light== is rendering an effect, none of the `hs_color`, `color_temp`, or `brightness` state attributes may be meaningful.

## Changes

### Requirements on color\_mode are less strict when a light is rendering an effect

More restrictive color modes than what's otherwise supported by the ==light== are allowed when an effect is active:

- A ==light== which supports colors is allowed to indicate color modes `on_off` and `brightness` when controlled by an effect
- A ==light== which supports brightness is allowed to indicate color mode `on_off` when controlled by an effect.

For example, a ==light== which has its supported\_color\_modes set to `{"hs", "color_temp"}` is allowed to set its `color_mode` to `on_off` when rendering an effect which can't be adjusted and to `brightness` when rendering an effect which allows brightness to be controlled.

### A special effect EFFECT\_OFF which means no effect / turn off effect has been added

There was previously no standard way for a ==light== which supports effects to show that no effect is active. This has been solved by adding an the pre-defined effect `EFFECT_OFF` to indicate no effect is active.

More details can be found in the [documentation](https://developers.home-assistant.io/docs/core/entity/light#color-modes) and in [architecture discussion #960](https://github.com/home-assistant/architecture/discussions/960).
