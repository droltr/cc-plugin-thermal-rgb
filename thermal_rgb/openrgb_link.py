"""OpenRGB SDK access: connect, describe devices, resolve configured zones."""

from dataclasses import dataclass
from typing import Any

from .config import ZoneRef

CLIENT_NAME = "cc-plugin-thermal-rgb"


@dataclass(frozen=True)
class ResolvedZone:
    ref: ZoneRef
    device_index: int
    zone_index: int | None  # None: the whole device
    led_count: int


class ZoneResolutionError(LookupError):
    pass


def connect(host: str, port: int) -> Any:
    from openrgb import OpenRGBClient  # imported lazily so unit tests need no server

    return OpenRGBClient(host, port, CLIENT_NAME)


def describe(devices: list[Any]) -> list[str]:
    lines = []
    for device in devices:
        location = getattr(getattr(device, "metadata", None), "location", "") or ""
        modes = ", ".join(m.name for m in device.modes)
        lines.append(f"[{device.id}] {device.name} ({location}) modes: {modes}")
        for zone in device.zones:
            lines.append(f"      zone {zone.id}: {zone.name!r} leds={len(zone.leds)}")
    return lines


def resolve_zone(devices: list[Any], ref: ZoneRef) -> ResolvedZone:
    for index, device in enumerate(devices):
        if device.name != ref.device:
            continue
        location = getattr(getattr(device, "metadata", None), "location", "") or ""
        if ref.location and ref.location not in location:
            continue
        if ref.zone is None:
            return ResolvedZone(ref, index, None, len(device.leds))
        for zone_index, zone in enumerate(device.zones):
            if zone.name == ref.zone:
                return ResolvedZone(ref, index, zone_index, len(zone.leds))
    raise ZoneResolutionError(
        f"zone {ref.name!r} not found (device={ref.device!r}, zone={ref.zone!r}, "
        f"location={ref.location!r})"
    )
