"""Runtime status for the settings page.

CoolerControl plugin pages can only read the plugin's config.json, so the plugin writes a read-only
"_status" block into it: state, version, connection details and the zones it resolved. The page
shows it on the Info tab. The block is rewritten only when it changes.
"""

import importlib.metadata
import json
import logging
import platform
import threading
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
        "update_check": cfg.update_check,
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


def environment_info() -> dict[str, Any]:
    """Versions of what the plugin runs on; shown on the Info tab."""
    try:
        openrgb_python = importlib.metadata.version("openrgb-python")
    except importlib.metadata.PackageNotFoundError:
        openrgb_python = None
    return {
        "platform": platform.system(),
        "kernel": platform.release(),
        "python": platform.python_version(),
        "openrgb_python": openrgb_python,
    }


class StatusPublisher:
    """Publishes statuses and keeps extra blocks (update check, environment) in every one of them.

    The update check finishes at any time, even while the main loop is waiting for a dependency, so
    its result must survive the next publish of a different state.
    """

    def __init__(self, path: Path | None) -> None:
        self.path = path
        self._extras: dict[str, Any] = {}
        self._last: dict[str, Any] | None = None
        self._lock = threading.Lock()

    def publish(self, status: dict[str, Any]) -> bool:
        with self._lock:
            self._last = status
            return publish_status(self.path, {**status, **self._extras})

    def add(self, key: str, value: Any) -> None:
        with self._lock:
            self._extras[key] = value
            if self._last is not None:
                publish_status(self.path, {**self._last, **self._extras})
