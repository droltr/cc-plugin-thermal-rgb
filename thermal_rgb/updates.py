"""Update check: compares the running version with the latest GitHub release.

CoolerControl plugin pages cannot call external sites from their sandboxed iframe, so the plugin
does the check and publishes the result in its "_status" block. One anonymous GET to the public
releases API; only a User-Agent with the plugin name and version is sent. Disable it with
"update_check": false.
"""

import json
import logging
import re
import threading
import urllib.error
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from . import __version__

LOG = logging.getLogger(__name__)

REPO = "droltr/cc-plugin-thermal-rgb"
API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_URL = f"https://github.com/{REPO}/releases"
CHECK_INTERVAL_S = 12 * 60 * 60
TIMEOUT_S = 10

_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def parse_version(text: str) -> tuple[int, int, int] | None:
    """'v1.2.3' or '1.2.3' -> (1, 2, 3); anything else (pre-releases, junk) -> None."""
    match = _VERSION_RE.match(str(text).strip())
    return tuple(int(part) for part in match.groups()) if match else None  # type: ignore[return-value]


def compare(current: str, latest: str) -> str:
    """'update_available' | 'up_to_date' | 'ahead' (running a build newer than the last release)."""
    have, newest = parse_version(current), parse_version(latest)
    if have is None or newest is None:
        return "unknown"
    if newest > have:
        return "update_available"
    return "up_to_date" if newest == have else "ahead"


def fetch_latest(url: str = API_URL, timeout: float = TIMEOUT_S) -> dict[str, str]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"cc-plugin-thermal-rgb/{__version__}",
        },
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (fixed https URL)
        data = json.load(response)
    tag = str(data["tag_name"])
    return {"tag": tag, "url": str(data.get("html_url") or f"{RELEASES_URL}/tag/{tag}")}


def check_update(
    current: str = __version__,
    fetch: Callable[[], dict[str, str]] = fetch_latest,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> dict[str, Any]:
    """Result block for the status: never raises; failures become status 'unknown' with an error."""
    result: dict[str, Any] = {"checked_at": now().astimezone().isoformat(timespec="seconds")}
    try:
        latest = fetch()
        status = compare(current, latest["tag"])
        result.update(latest=latest["tag"], url=latest["url"], status=status)
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, OSError) as err:
        result.update(status="unknown", error=str(err)[:200])
    return result


def run_checks(
    stop: threading.Event,
    publish: Callable[[dict[str, Any]], None],
    check: Callable[[], dict[str, Any]] = check_update,
    interval_s: float = CHECK_INTERVAL_S,
) -> None:
    """Check now and then every interval until stop is set (meant for a daemon thread)."""
    while not stop.is_set():
        result = check()
        if result.get("status") == "unknown":
            LOG.info("Update check failed: %s", result.get("error"))
        else:
            LOG.info("Update check: %s (latest %s)", result["status"], result.get("latest"))
        publish(result)
        stop.wait(interval_s)
