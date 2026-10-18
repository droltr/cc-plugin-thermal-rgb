"""Perceptual colour gradients for temperature lighting.

Colours are interpolated in OKLCH (the polar form of OKLab), where equal steps look
equally different. Interpolating in sRGB would pass through muddy greys between
blue and yellow.

The OKLab matrices follow Björn Ottosson, https://bottosson.github.io/posts/oklab/ (public domain).
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

RGB = tuple[int, int, int]


@dataclass(frozen=True)
class ColorStop:
    temp_c: float
    rgb: RGB


def hex_to_rgb(value: str) -> RGB:
    text = value.strip().lstrip("#")
    if len(text) != 6 or any(c not in "0123456789abcdefABCDEF" for c in text):
        raise ValueError(f"Invalid hex colour: {value!r}")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def _srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _linear_to_srgb(c: float) -> float:
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


def rgb_to_oklch(rgb: RGB) -> tuple[float, float, float]:
    r, g, b = (_srgb_to_linear(v / 255) for v in rgb)
    l_ = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m_ = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s_ = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (math.copysign(abs(v) ** (1 / 3), v) for v in (l_, m_, s_))
    lightness = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    return lightness, math.hypot(a, bb), math.degrees(math.atan2(bb, a)) % 360


def oklch_to_rgb(lightness: float, chroma: float, hue: float) -> RGB:
    a = chroma * math.cos(math.radians(hue))
    bb = chroma * math.sin(math.radians(hue))
    l_ = (lightness + 0.3963377774 * a + 0.2158037573 * bb) ** 3
    m_ = (lightness - 0.1055613458 * a - 0.0638541728 * bb) ** 3
    s_ = (lightness - 0.0894841775 * a - 1.2914855480 * bb) ** 3
    r = 4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_
    g = -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_
    b = -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_
    return tuple(  # type: ignore[return-value]
        round(min(1.0, max(0.0, _linear_to_srgb(min(1.0, max(0.0, v))))) * 255) for v in (r, g, b)
    )


def _mix_hue(h1: float, h2: float, t: float) -> float:
    """Interpolate hue along the shorter arc."""
    delta = ((h2 - h1 + 180) % 360) - 180
    return (h1 + delta * t) % 360


def mix_oklch(c1: RGB, c2: RGB, t: float) -> RGB:
    """Blend two colours in OKLCH; t=0 gives c1, t=1 gives c2."""
    t = min(1.0, max(0.0, t))
    l1, ch1, h1 = rgb_to_oklch(c1)
    l2, ch2, h2 = rgb_to_oklch(c2)
    # Achromatic endpoints have no meaningful hue; borrow the other one.
    if ch1 < 1e-4:
        h1 = h2
    if ch2 < 1e-4:
        h2 = h1
    return oklch_to_rgb(l1 + (l2 - l1) * t, ch1 + (ch2 - ch1) * t, _mix_hue(h1, h2, t))


def gradient(temp_c: float, stops: Sequence[ColorStop]) -> RGB:
    """Colour for temp_c; holds the first/last stop colour outside the range."""
    if not stops:
        raise ValueError("At least one colour stop is required")
    ordered = sorted(stops, key=lambda s: s.temp_c)
    if temp_c <= ordered[0].temp_c:
        return ordered[0].rgb
    if temp_c >= ordered[-1].temp_c:
        return ordered[-1].rgb
    for low, high in zip(ordered, ordered[1:], strict=False):
        if low.temp_c <= temp_c <= high.temp_c:
            span = high.temp_c - low.temp_c
            return mix_oklch(low.rgb, high.rgb, (temp_c - low.temp_c) / span if span else 1.0)
    return ordered[-1].rgb  # unreachable for sorted, finite stops
