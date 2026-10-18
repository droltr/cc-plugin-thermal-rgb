"""Entry point.

python -m thermal_rgb --config /var/lib/coolercontrol/plugins/thermal-rgb/config.json
python -m thermal_rgb --list          # show OpenRGB zones, the temperature and the colour
"""

import argparse
import logging
import os
import signal
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from . import __version__
from .colors import RGB, hex_to_rgb
from .config import Config, ConfigError, load_config
from .coolercontrol import CoolerControlClient, CoolerControlError
from .engine import Ema, bands_color, color_changed
from .openrgb_link import ResolvedZone, ZoneResolutionError, connect, describe, resolve_zone
from .status import publish_status, running_status, stopped_status, waiting_status

LOG = logging.getLogger("thermal_rgb")
# CoolerControl passes its log level in CC_LOG (ERROR/WARN/INFO/DEBUG/TRACE).
_LEVELS = {
    "ERROR": logging.ERROR,
    "WARN": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "TRACE": logging.DEBUG,
}
DEFAULT_CONFIG = Path(__file__).resolve().parent.parent.parent / "config.json"


def _resolve_zones(devices: list[Any], cfg: Config) -> list[ResolvedZone]:
    zones = []
    for ref in cfg.zones:
        try:
            zones.append(resolve_zone(devices, ref))
        except ZoneResolutionError as err:
            LOG.warning("%s (skipped)", err)
    return zones


def _apply(client: Any, zones: list[ResolvedZone], color: RGB) -> None:
    from openrgb.utils import RGBColor

    rgb = RGBColor(*color)
    for zone in zones:
        device = client.devices[zone.device_index]
        if zone.zone_index is None:
            device.set_color(rgb)
        else:
            device.zones[zone.zone_index].set_color(rgb)


def _ensure_direct_mode(client: Any, zones: list[ResolvedZone]) -> None:
    for index in sorted({z.device_index for z in zones}):
        device = client.devices[index]
        if device.modes[device.active_mode].name.lower() != "direct":
            device.set_mode("direct")


def list_mode(cfg: Config) -> int:
    cc = CoolerControlClient(cfg.coolercontrol_url, cfg.coolercontrol_token)
    uid = cfg.temp_device_uid or cc.first_cpu_uid()
    temp = cc.read_temp(uid, cfg.temp_name)
    print(
        f"CPU {cfg.temp_name} ({uid[:8]}): {temp:.1f} °C -> colour {bands_color(temp, cfg.stops)}"
    )
    client = connect(cfg.openrgb_host, cfg.openrgb_port)
    try:
        print("\n".join(describe(client.devices)))
        for zone in _resolve_zones(client.devices, cfg):
            target = "whole device" if zone.zone_index is None else f"zone {zone.zone_index}"
            print(
                f"{zone.ref.name:8} -> device {zone.device_index} {target} ({zone.led_count} LEDs)"
            )
    finally:
        client.disconnect()
    return 0


def sweep_mode(
    cfg: Config,
    start_c: float = 45.0,
    end_c: float = 85.0,
    step_c: float = 1.0,
    hold_s: float = 1.5,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Preview the gradient on the real LEDs without heating the CPU.

    Walks start_c → end_c, printing each temperature and colour, then restores the
    colour for the current CPU temperature. The running plugin only writes on change,
    so it does not fight the preview while the CPU temperature is steady.
    """
    client = connect(cfg.openrgb_host, cfg.openrgb_port)
    try:
        zones = _resolve_zones(client.devices, cfg)
        _ensure_direct_mode(client, zones)
        temp = start_c
        while temp <= end_c + 1e-9:
            color = bands_color(temp, cfg.stops)
            print(
                f"{temp:5.1f} °C -> #{color[0]:02x}{color[1]:02x}{color[2]:02x} {color}", flush=True
            )
            _apply(client, zones, color)
            sleep(hold_s)
            temp += step_c
        cc = CoolerControlClient(cfg.coolercontrol_url, cfg.coolercontrol_token)
        try:
            current = cc.read_temp(cfg.temp_device_uid or cc.first_cpu_uid(), cfg.temp_name)
            _apply(client, zones, bands_color(current, cfg.stops))
            print(f"restored colour for current CPU {current:.1f} °C")
        except CoolerControlError as err:
            print(f"could not restore current colour: {err}")
    finally:
        client.disconnect()
    return 0


def show_mode(cfg: Config, color: RGB) -> int:
    """Hold one colour on all configured zones (for judging colours by eye)."""
    client = connect(cfg.openrgb_host, cfg.openrgb_port)
    try:
        zones = _resolve_zones(client.devices, cfg)
        _ensure_direct_mode(client, zones)
        _apply(client, zones, color)
        print(f"showing #{color[0]:02x}{color[1]:02x}{color[2]:02x} {color} on {len(zones)} zones")
    finally:
        client.disconnect()
    return 0


def run(cfg: Config, stop: threading.Event, status_path: Path | None = None) -> int:
    cc = CoolerControlClient(cfg.coolercontrol_url, cfg.coolercontrol_token)
    uid = cfg.temp_device_uid or cc.first_cpu_uid()
    client = connect(cfg.openrgb_host, cfg.openrgb_port)
    zones = _resolve_zones(client.devices, cfg)
    LOG.info("Connected: %d zones resolved, write_leds=%s", len(zones), cfg.write_leds)
    publish_status(status_path, running_status(cfg, zones, uid))
    if cfg.write_leds and zones:
        _ensure_direct_mode(client, zones)
    ema = Ema(cfg.smoothing_tau_s)
    last_color: RGB | None = None
    last_tick = time.monotonic()
    last_summary = 0.0
    try:
        while not stop.is_set():
            now = time.monotonic()
            try:
                smoothed = ema.update(cc.read_temp(uid, cfg.temp_name), now - last_tick)
            except CoolerControlError as err:
                LOG.warning("Temperature read failed: %s", err)
                stop.wait(cfg.poll_interval_s * 5)
                continue
            last_tick = now
            color = bands_color(smoothed, cfg.stops)
            if color_changed(last_color, color):
                LOG.debug("%.1f °C -> %s", smoothed, color)
                if cfg.write_leds:
                    _apply(client, zones, color)
                last_color = color
            if now - last_summary >= 60:
                LOG.info("CPU %.1f °C (smoothed) -> colour %s", smoothed, color)
                last_summary = now
            stop.wait(cfg.poll_interval_s)
    finally:
        client.disconnect()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Temperature-driven RGB for CoolerControl")
    parser.add_argument(
        "--config", type=Path, default=Path(os.environ.get("THERMAL_RGB_CONFIG", DEFAULT_CONFIG))
    )
    parser.add_argument("--list", action="store_true", help="list zones and exit")
    parser.add_argument(
        "--sweep",
        nargs="*",
        type=float,
        metavar=("START", "END"),
        help="preview the gradient on the LEDs (default 45 to 85 °C), then exit",
    )
    parser.add_argument("--show", metavar="HEX", help="hold one colour on all zones, then exit")
    parser.add_argument("--version", action="version", version=__version__)
    args = parser.parse_args()
    logging.basicConfig(
        level=_LEVELS.get(os.environ.get("CC_LOG", "INFO").upper(), logging.INFO),
        format="%(levelname)s %(name)s: %(message)s",
    )
    try:
        cfg = load_config(args.config)
    except ConfigError as err:
        LOG.error("Invalid configuration: %s", err)
        return 2
    if args.list:
        return list_mode(cfg)
    if args.show:
        try:
            return show_mode(cfg, hex_to_rgb(args.show))
        except ValueError as err:
            LOG.error("%s", err)
            return 2
    if args.sweep is not None:
        start = args.sweep[0] if len(args.sweep) > 0 else 45.0
        end = args.sweep[1] if len(args.sweep) > 1 else 85.0
        return sweep_mode(cfg, start, end)
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    # Retry until the dependencies (CoolerControl API, OpenRGB server) are up.
    while not stop.is_set():
        try:
            code = run(cfg, stop, args.config)
            publish_status(args.config, stopped_status(cfg))
            return code
        except (CoolerControlError, ConnectionError, OSError) as err:
            LOG.warning("Not ready (%s); retrying in 10 s", err)
            publish_status(args.config, waiting_status(cfg, str(err)))
            stop.wait(10)
    publish_status(args.config, stopped_status(cfg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
