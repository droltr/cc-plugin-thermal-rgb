from types import SimpleNamespace

import pytest

from thermal_rgb.config import ZoneRef, parse_config
from thermal_rgb.engine import Ema, bands_color, color_changed
from thermal_rgb.openrgb_link import ZoneResolutionError, describe, resolve_zone


def test_ema_first_sample_and_convergence() -> None:
    ema = Ema(3.0)
    assert ema.update(40, 1) == 40
    for _ in range(60):
        value = ema.update(80, 1)
    assert 79 < value <= 80


def test_ema_step_follows_time_constant() -> None:
    ema = Ema(3.0)
    ema.update(0, 0)
    # After one time constant the EMA covers ~63 % of a step.
    assert ema.update(100, 3.0) == pytest.approx(63.2, abs=0.1)


def test_ema_zero_tau_passes_through() -> None:
    ema = Ema(0)
    ema.update(10, 1)
    assert ema.update(70, 1) == 70


def test_bands_color_uses_gradient() -> None:
    stops = parse_config({}).stops
    assert bands_color(30, stops) == (0x20, 0x60, 0xFF)
    assert bands_color(90, stops) == (0xFF, 0, 0)


def test_color_changed_threshold() -> None:
    assert color_changed(None, (1, 2, 3))
    assert not color_changed((10, 10, 10), (12, 10, 9))
    assert color_changed((10, 10, 10), (13, 10, 10))


def _device(index: int, name: str, location: str, zones: list[str]) -> SimpleNamespace:
    zone_objs = [SimpleNamespace(id=i, name=z, leds=[0] * 8) for i, z in enumerate(zones)]
    return SimpleNamespace(
        id=index,
        name=name,
        metadata=SimpleNamespace(location=location),
        modes=[SimpleNamespace(name="Direct")],
        zones=zone_objs,
        leds=[0] * (8 * len(zones)),
    )


DEVICES = [
    _device(0, "ENE DRAM", "I2C: /dev/i2c-13, address 0x71", ["DRAM"]),
    _device(1, "ENE DRAM", "I2C: /dev/i2c-13, address 0x73", ["DRAM"]),
    _device(2, "MSI MYSTIC LIGHT", "HID: /dev/hidraw12", ["JAF", "JARGB 1", "JARGB 2", "JARGB 3"]),
]


def test_default_zones_resolve() -> None:
    resolved = {z.name: resolve_zone(DEVICES, z) for z in parse_config({}).zones}
    assert (resolved["rear_1"].device_index, resolved["rear_1"].zone_index) == (2, 1)
    assert (resolved["front"].device_index, resolved["front"].zone_index) == (2, 3)
    assert (resolved["ram_2"].device_index, resolved["ram_2"].zone_index) == (1, None)


@pytest.mark.parametrize(
    "ref",
    [
        ZoneRef("x", "Nope"),
        ZoneRef("x", "MSI MYSTIC LIGHT", zone="JARGB 9"),
        ZoneRef("x", "ENE DRAM", location="address 0x99"),
    ],
)
def test_unresolvable_zone(ref: ZoneRef) -> None:
    with pytest.raises(ZoneResolutionError):
        resolve_zone(DEVICES, ref)


def test_describe_lists_devices_and_zones() -> None:
    text = "\n".join(describe(DEVICES))
    assert "MSI MYSTIC LIGHT" in text and "'JARGB 3'" in text and "address 0x73" in text
