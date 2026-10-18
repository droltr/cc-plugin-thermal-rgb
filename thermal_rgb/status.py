"""Runtime status for the settings page.

CoolerControl plugin pages can only read the plugin's config.json, so the plugin writes a read-only
"_status" block into it: state, version, connection details and the zones it resolved. The page
shows it on the Info tab. The block is rewritten only when it changes.
"""

import json
import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from . import __version__
from .config import Config, write_json
from .openrgb_link import ResolvedZone

LOG = logging.getLogger(__name__)

_MAX_ERROR_CHARS = 200


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _base(cfg: Config, state: str) -> dict[str, Any]:
    return {
        "state": state,
        "version": __version__,
        "token_stored": bool(cfg.coolercontrol_token),
        "write_leds": cfg.write_leds,
        "openrgb": {"host": cfg.openrgb_host, "port": cfg.openrgb_port},
        "temp_name": cfg.temp_name,
        "updated": _now(),
    }


def running_status(
    cfg: Config, zones: Sequence[ResolvedZone], temp_device_uid: str
) -> dict[str, Any]:
    resolved = {z.ref.name for z in zones}
    status = _base(cfg, "running")
    status["temp_device_uid"] = temp_device_uid
    status["zones"] = [
        {"name": z.ref.name, "device": z.ref.device, "zone": z.ref.zone, "leds": z.led_count}
        for z in zones
    ]
    status["zones_unresolved"] = [z.name for z in cfg.zones if z.name not in resolved]
    return status


def waiting_status(cfg: Config, error: str) -> dict[str, Any]:
    status = _base(cfg, "waiting")
    status["error"] = error[:_MAX_ERROR_CHARS]
    return status


def stopped_status(cfg: Config) -> dict[str, Any]:
    return _base(cfg, "stopped")


def publish_status(path: Path | None, status: dict[str, Any]) -> bool:
    """Write status into config.json; returns True when the file was changed."""
    if path is None:
        return False
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            return False
        old = raw.get("_status")
        if isinstance(old, dict) and _same(old, status):
            return False
        write_json(path, {**raw, "_status": status})
    except (OSError, json.JSONDecodeError) as err:
        LOG.debug("Could not publish status to %s: %s", path.name, err)
        return False
    return True


def _same(old: dict[str, Any], new: dict[str, Any]) -> bool:
    """Compare ignoring the timestamp, so a repeated waiting error does not rewrite the file."""
    return {k: v for k, v in old.items() if k != "updated"} == {
        k: v for k, v in new.items() if k != "updated"
    }
