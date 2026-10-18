"""Plugin configuration (config.json in the plugin folder, editable from CoolerControl)."""

import json
import logging
import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any

from .colors import ColorStop, hex_to_rgb

LOG = logging.getLogger(__name__)

# The settings page sends a new token in config.json; the plugin moves it to credentials.json
# and leaves this mask behind, so the page (which reads config.json verbatim) never sees it.
TOKEN_MASK = "***"

DEFAULT_STOPS = (
    {"temp_c": 50, "color": "#2060ff"},  # cold: blue
    {"temp_c": 60, "color": "#ffd000"},  # warm: yellow
    {"temp_c": 70, "color": "#ff7a00"},  # hot: orange
    {"temp_c": 80, "color": "#ff0000"},  # very hot: red
)

# Logical zones on the owner's system, ordered rear to front (used by wave themes).
DEFAULT_ZONES = (
    {"name": "rear_1", "device": "MSI MYSTIC LIGHT", "zone": "JARGB 1"},
    {"name": "rear_2", "device": "MSI MYSTIC LIGHT", "zone": "JARGB 2"},
    {"name": "ram_1", "device": "ENE DRAM", "location": "address 0x71"},
    {"name": "ram_2", "device": "ENE DRAM", "location": "address 0x73"},
    {"name": "front", "device": "MSI MYSTIC LIGHT", "zone": "JARGB 3"},
)


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ZoneRef:
    """Selects an OpenRGB zone by device name, optional location substring and zone name.

    Without a zone name the whole device is meant (e.g. a DRAM stick).
    """

    name: str
    device: str
    zone: str | None = None
    location: str | None = None


@dataclass(frozen=True)
class Config:
    coolercontrol_url: str = "http://127.0.0.1:11987"
    coolercontrol_token: str = ""
    temp_device_uid: str = ""
    temp_name: str = "temp1"
    openrgb_host: str = "127.0.0.1"
    openrgb_port: int = 6742
    poll_interval_s: float = 1.0
    smoothing_tau_s: float = 3.0
    write_leds: bool = True
    stops: tuple[ColorStop, ...] = field(default_factory=tuple)
    zones: tuple[ZoneRef, ...] = field(default_factory=tuple)


def _require(cond: bool, message: str) -> None:
    if not cond:
        raise ConfigError(message)


def parse_config(raw: dict[str, Any]) -> Config:
    _require(isinstance(raw, dict), "config must be a JSON object")
    stops_raw = raw.get("stops", DEFAULT_STOPS)
    zones_raw = raw.get("zones", DEFAULT_ZONES)
    _require(isinstance(stops_raw, list | tuple) and stops_raw, "stops must be a non-empty list")
    _require(isinstance(zones_raw, list | tuple), "zones must be a list")
    try:
        stops = tuple(ColorStop(float(s["temp_c"]), hex_to_rgb(s["color"])) for s in stops_raw)
        zones = tuple(
            ZoneRef(
                name=str(z["name"]),
                device=str(z["device"]),
                zone=z.get("zone"),
                location=z.get("location"),
            )
            for z in zones_raw
        )
    except (KeyError, TypeError) as err:
        raise ConfigError(f"invalid stop or zone entry: {err}") from err
    _require(len({z.name for z in zones}) == len(zones), "zone names must be unique")
    poll = float(raw.get("poll_interval_s", 1.0))
    _require(0.2 <= poll <= 60, "poll_interval_s must be between 0.2 and 60")
    port = int(raw.get("openrgb_port", 6742))
    _require(1024 <= port <= 65535, "openrgb_port must be between 1024 and 65535")
    return Config(
        coolercontrol_url=str(raw.get("coolercontrol_url", Config.coolercontrol_url)).rstrip("/"),
        coolercontrol_token=str(raw.get("coolercontrol_token", "")),
        temp_device_uid=str(raw.get("temp_device_uid", "")),
        temp_name=str(raw.get("temp_name", "temp1")),
        openrgb_host=str(raw.get("openrgb_host", "127.0.0.1")),
        openrgb_port=port,
        poll_interval_s=poll,
        smoothing_tau_s=float(raw.get("smoothing_tau_s", 3.0)),
        write_leds=bool(raw.get("write_leds", True)),
        stops=stops,
        zones=zones,
    )


def credentials_path(config_path: Path) -> Path:
    return config_path.with_name("credentials.json")


def _write_json(path: Path, data: dict[str, Any]) -> None:
    """Replace a JSON file atomically, keeping owner-only permissions."""
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    tmp.replace(path)


def _stored_token(path: Path) -> str:
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get("coolercontrol_token", ""))
    except (OSError, json.JSONDecodeError, AttributeError):
        return ""


def resolve_token(config_path: Path, raw: dict[str, Any]) -> str:
    """Return the CoolerControl token, moving a newly entered one into credentials.json."""
    entered = str(raw.get("coolercontrol_token", "")).strip()
    creds = credentials_path(config_path)
    if not entered or set(entered) == {"*"}:
        return _stored_token(creds)
    try:
        _write_json(creds, {"coolercontrol_token": entered})
        _write_json(config_path, {**raw, "coolercontrol_token": TOKEN_MASK})
        LOG.info("Stored the CoolerControl token in %s", creds.name)
    except OSError as err:
        LOG.warning("Could not move the token to %s (%s); using it from config", creds.name, err)
    return entered


def load_config(path: Path) -> Config:
    if not path.exists():
        return replace(parse_config({}), coolercontrol_token=_stored_token(credentials_path(path)))
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        raise ConfigError(f"{path}: {err}") from err
    cfg = parse_config(raw)
    return replace(cfg, coolercontrol_token=resolve_token(path, raw))
