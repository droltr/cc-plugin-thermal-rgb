import json
import threading
from pathlib import Path
from unittest.mock import patch

from test_main import FakeCC, FakeClient

from thermal_rgb import __main__ as app
from thermal_rgb import __version__
from thermal_rgb.config import ZoneRef, parse_config
from thermal_rgb.openrgb_link import ResolvedZone
from thermal_rgb.status import publish_status, running_status, stopped_status, waiting_status


def _zones() -> list[ResolvedZone]:
    ref = ZoneRef("rear_1", "MSI MYSTIC LIGHT", "JARGB 1")
    return [ResolvedZone(ref, device_index=2, zone_index=1, led_count=8)]


def test_running_status_lists_resolved_and_missing_zones() -> None:
    cfg = parse_config({"coolercontrol_token": "cc_x"})
    status = running_status(cfg, _zones(), "uid-1")
    assert status["state"] == "running"
    assert status["version"] == __version__
    assert status["token_stored"] is True
    assert status["write_leds"] is True
    assert status["temp_device_uid"] == "uid-1"
    assert status["zones"] == [
        {"name": "rear_1", "device": "MSI MYSTIC LIGHT", "zone": "JARGB 1", "leds": 8}
    ]
    assert status["zones_unresolved"] == ["rear_2", "ram_1", "ram_2", "front"]
    assert "cc_x" not in json.dumps(status)


def test_waiting_status_truncates_error() -> None:
    status = waiting_status(parse_config({}), "x" * 500)
    assert status["state"] == "waiting"
    assert len(status["error"]) == 200
    assert status["token_stored"] is False


def test_stopped_status() -> None:
    assert stopped_status(parse_config({}))["state"] == "stopped"


def test_publish_writes_once_and_keeps_other_keys(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"temp_name": "temp3"}), encoding="utf-8")
    status = stopped_status(parse_config({}))
    assert publish_status(path, status) is True
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["temp_name"] == "temp3" and data["_status"]["state"] == "stopped"
    assert path.stat().st_mode & 0o777 == 0o600
    assert (
        publish_status(path, {**status, "updated": "later"}) is False
    )  # only the timestamp differs
    assert publish_status(path, {**status, "state": "running"}) is True


def test_publish_ignores_missing_unreadable_or_foreign_files(tmp_path: Path) -> None:
    status = stopped_status(parse_config({}))
    assert publish_status(None, status) is False
    assert publish_status(tmp_path / "missing.json", status) is False
    bad = tmp_path / "bad.json"
    bad.write_text("{oops", encoding="utf-8")
    assert publish_status(bad, status) is False
    listy = tmp_path / "list.json"
    listy.write_text("[1]", encoding="utf-8")
    assert publish_status(listy, status) is False


def test_run_publishes_running_status(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{}", encoding="utf-8")
    stop = threading.Event()
    stop.wait = lambda timeout=None: stop.set() or True  # type: ignore[method-assign]
    with (
        patch.object(app, "CoolerControlClient", FakeCC),
        patch.object(app, "connect", lambda h, p: FakeClient()),
    ):
        assert app.run(parse_config({}), stop, path) == 0
    status = json.loads(path.read_text(encoding="utf-8"))["_status"]
    assert status["state"] == "running"
    assert [z["name"] for z in status["zones"]] == ["rear_1", "rear_2", "ram_1", "ram_2", "front"]


def test_main_publishes_waiting_then_stopped(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{}", encoding="utf-8")
    seen: list[str] = []
    calls = {"n": 0}

    def fake_run(cfg: object, stop: threading.Event, status_path: Path | None = None) -> int:
        calls["n"] += 1
        if calls["n"] == 1:
            raise ConnectionError("openrgb not up")
        seen.append(json.loads(path.read_text(encoding="utf-8"))["_status"]["state"])
        return 0

    with (
        patch("sys.argv", ["thermal_rgb", "--config", str(path)]),
        patch.object(app, "run", fake_run),
        patch("threading.Event.wait", return_value=False),
    ):
        assert app.main() == 0
    assert seen == ["waiting"]
    final = json.loads(path.read_text(encoding="utf-8"))["_status"]
    assert final["state"] == "stopped"
