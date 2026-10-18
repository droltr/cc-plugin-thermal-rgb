import json
import threading
import urllib.error
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from thermal_rgb import __main__ as app
from thermal_rgb import updates
from thermal_rgb.config import parse_config
from thermal_rgb.status import StatusPublisher, environment_info, stopped_status


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1.2.3", (1, 2, 3)),
        ("v0.3.0", (0, 3, 0)),
        (" v10.0.1 ", (10, 0, 1)),
        ("1.2", None),
        ("1.2.3-rc1", None),
        ("latest", None),
        ("", None),
    ],
)
def test_parse_version(text: str, expected: object) -> None:
    assert updates.parse_version(text) == expected


@pytest.mark.parametrize(
    ("current", "latest", "expected"),
    [
        ("0.3.0", "v0.3.1", "update_available"),
        ("0.3.0", "v0.3.0", "up_to_date"),
        ("0.3.0", "v0.2.1", "ahead"),
        ("0.9.0", "v0.10.0", "update_available"),
        ("0.3.0", "weird", "unknown"),
        ("dev", "v1.0.0", "unknown"),
    ],
)
def test_compare(current: str, latest: str, expected: str) -> None:
    assert updates.compare(current, latest) == expected


def fixed_now() -> datetime:
    return datetime(2026, 10, 18, 12, 0, tzinfo=UTC)


def test_check_update_success_and_failures() -> None:
    ok = updates.check_update("0.3.0", lambda: {"tag": "v0.3.1", "url": "https://x/r"}, fixed_now)
    assert (
        ok["status"] == "update_available"
        and ok["latest"] == "v0.3.1"
        and ok["url"] == "https://x/r"
    )
    assert ok["checked_at"].startswith("2026-10-18")

    def offline() -> dict[str, str]:
        raise urllib.error.URLError("no route")

    failed = updates.check_update("0.3.0", offline, fixed_now)
    assert (
        failed["status"] == "unknown" and "no route" in failed["error"] and "latest" not in failed
    )

    def broken() -> dict[str, str]:
        raise KeyError("tag_name")

    assert updates.check_update("0.3.0", broken, fixed_now)["status"] == "unknown"


def test_fetch_latest_reads_release_json() -> None:
    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, *args: object) -> bytes:
            return json.dumps({"tag_name": "v1.4.0", "html_url": "https://example/rel"}).encode()

    seen = {}

    def fake_urlopen(request: object, timeout: float) -> Response:
        seen["agent"] = request.get_header("User-agent")  # type: ignore[attr-defined]
        seen["accept"] = request.get_header("Accept")  # type: ignore[attr-defined]
        return Response()

    with patch("urllib.request.urlopen", fake_urlopen):
        assert updates.fetch_latest() == {"tag": "v1.4.0", "url": "https://example/rel"}
    assert seen["agent"].startswith("cc-plugin-thermal-rgb/") and "github" in seen["accept"]

    class NoUrl(Response):
        def read(self, *args: object) -> bytes:
            return json.dumps({"tag_name": "v1.4.0"}).encode()

    with patch("urllib.request.urlopen", lambda r, timeout: NoUrl()):
        assert updates.fetch_latest()["url"].endswith("/releases/tag/v1.4.0")


def test_run_checks_repeats_until_stopped() -> None:
    stop = threading.Event()
    published: list[dict] = []
    calls = {"n": 0}

    def check() -> dict:
        calls["n"] += 1
        return (
            {"status": "unknown", "error": "x"}
            if calls["n"] == 1
            else {"status": "up_to_date", "latest": "v1"}
        )

    def publish(result: dict) -> None:
        published.append(result)
        if len(published) == 2:
            stop.set()

    updates.run_checks(stop, publish, check, interval_s=0)
    assert [p["status"] for p in published] == ["unknown", "up_to_date"]


def test_publisher_keeps_extras_in_every_state(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{}", encoding="utf-8")
    cfg = parse_config({})
    publisher = StatusPublisher(path)
    publisher.add("update", {"status": "up_to_date"})  # before any state: nothing to write yet
    assert "_status" not in json.loads(path.read_text(encoding="utf-8"))
    publisher.publish(stopped_status(cfg))
    status = json.loads(path.read_text(encoding="utf-8"))["_status"]
    assert status["state"] == "stopped" and status["update"] == {"status": "up_to_date"}
    publisher.add("update", {"status": "update_available", "latest": "v9.9.9"})
    status = json.loads(path.read_text(encoding="utf-8"))["_status"]
    assert status["state"] == "stopped" and status["update"]["latest"] == "v9.9.9"
    assert status["update_check"] is True
    assert StatusPublisher(None).publish(stopped_status(cfg)) is False


def test_environment_info() -> None:
    env = environment_info()
    assert set(env) == {"platform", "kernel", "python", "openrgb_python"}
    assert env["python"].count(".") >= 1


def test_update_check_can_be_disabled() -> None:
    assert parse_config({}).update_check is True
    assert parse_config({"update_check": False}).update_check is False


def run_main(tmp_path: Path, raw: dict) -> list[str]:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    started: list[str] = []

    class FakeThread:
        def __init__(self, *args: object, **kwargs: object) -> None:
            started.append(kwargs.get("name", ""))  # type: ignore[arg-type]

        def start(self) -> None:
            return None

    with (
        patch("sys.argv", ["thermal_rgb", "--config", str(path)]),
        patch.object(app, "run", lambda cfg, stop, publisher=None: 0),
        patch.object(app.threading, "Thread", FakeThread),
    ):
        assert app.main() == 0
    return started


def test_main_starts_update_thread_only_when_enabled(tmp_path: Path) -> None:
    assert run_main(tmp_path, {}) == ["update-check"]
    assert run_main(tmp_path, {"update_check": False}) == []
