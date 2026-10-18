import pytest

from thermal_rgb.colors import (
    ColorStop,
    gradient,
    hex_to_rgb,
    mix_oklch,
    oklch_to_rgb,
    rgb_to_oklch,
)

STOPS = [
    ColorStop(50, (0x20, 0x60, 0xFF)),
    ColorStop(60, (0xFF, 0xD0, 0x00)),
    ColorStop(70, (0xFF, 0x7A, 0x00)),
    ColorStop(80, (0xFF, 0x00, 0x00)),
]


def test_hex_to_rgb() -> None:
    assert hex_to_rgb("#2060ff") == (0x20, 0x60, 0xFF)
    assert hex_to_rgb("FF0000") == (255, 0, 0)


@pytest.mark.parametrize("value", ["#12345", "#gggggg", "", "#1234567"])
def test_hex_to_rgb_rejects_invalid(value: str) -> None:
    with pytest.raises(ValueError):
        hex_to_rgb(value)


@pytest.mark.parametrize("rgb", [(0, 0, 0), (255, 255, 255), (32, 96, 255), (255, 122, 0)])
def test_oklch_round_trip(rgb: tuple[int, int, int]) -> None:
    back = oklch_to_rgb(*rgb_to_oklch(rgb))
    assert all(abs(a - b) <= 1 for a, b in zip(rgb, back, strict=True))


def test_gradient_hits_stops_exactly() -> None:
    for stop in STOPS:
        assert gradient(stop.temp_c, STOPS) == stop.rgb


def test_gradient_holds_outside_range() -> None:
    assert gradient(20, STOPS) == STOPS[0].rgb
    assert gradient(105, STOPS) == STOPS[-1].rgb


def test_gradient_ignores_stop_order() -> None:
    assert gradient(65, list(reversed(STOPS))) == gradient(65, STOPS)


def test_gradient_requires_stops() -> None:
    with pytest.raises(ValueError):
        gradient(50, [])


def test_blue_to_yellow_midpoint_is_not_grey() -> None:
    # In sRGB the midpoint of blue and yellow is a grey; OKLCH keeps it saturated.
    r, g, b = gradient(55, STOPS)
    assert max(r, g, b) - min(r, g, b) > 80


def test_mix_endpoints_and_clamp() -> None:
    assert mix_oklch((255, 0, 0), (0, 0, 255), 0) == (255, 0, 0)
    assert mix_oklch((255, 0, 0), (0, 0, 255), 1) == (0, 0, 255)
    assert mix_oklch((255, 0, 0), (0, 0, 255), 2) == (0, 0, 255)


def test_mix_with_achromatic_endpoint() -> None:
    r, g, b = mix_oklch((128, 128, 128), (255, 0, 0), 0.5)
    assert r > g and r > b
