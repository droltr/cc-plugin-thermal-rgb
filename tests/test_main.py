import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from thermal_rgb import __main__ as app
from thermal_rgb.config import parse_config
from thermal_rgb.coolercontrol import CoolerControlError


class FakeZone:
    def __init__(self, zone_id: int, name: str) -> None:
        self.id, self.name, self.leds = zone_id, name, [0] * 8
        self.colors: list[tuple[int, int, int]] = []

    def set_color(self, color: object) -> None:
        self.colors.append((color.red, color.green, color.blue))  # type: ignore[attr-defined]


class FakeDevice:
    def __init__(self, index: int, name: str, location: str, zones: list[str], mode: str) -> None:
        self.id, self.name = index, name
        self.metadata = SimpleNamespace(location=location)
        self.modes = [SimpleNamespace(name=mode), SimpleNamespace(name="Direct")]
        self.active_mode = 0
        self.zones = [FakeZone(i, z) for i, z in enumerate(zones)]
        self.leds = [0] * 8
        self.colors: list[tuple[int, int, int]] = []
        self.mode_set: str | None = None

    def set_color(self, color: object) -> None:
        self.colors.append((color.red, color.green, color.blue))  # type: ignore[attr-defined]

    def set_mode(self, mode: str) -> None:
        self.mode_set = mode


class FakeClient:
    def __init__(self) -> None:
        self.devices = [
            FakeDevice(0, "ENE DRAM", "address 0x71", ["DRAM"], "Static"),
            FakeDevice(1, "ENE DRAM", "address 0x73", ["DRAM"], "Direct"),
            FakeDevice(
                2, "MSI MYSTIC LIGHT", "HID", ["JAF", "JARGB 1", "JARGB 2", "JARGB 3"], "Direct"
            ),
        ]
        self.disconnected = False

    def disconnect(self) -> None:
        self.disconnected = True


class FakeCC:
    temps = [45.0, 75.0, 75.0]

    def __init__(self, *_: object) -> None:
        self._i = 0

    def first_cpu_uid(self) -> str:
        return "cpu"

    def read_temp(self, uid: str, name: str) -> float:
        value = self.temps[min(self._i, len(self.temps) - 1)]
        self._i += 1
        return value


def _run(cfg_raw: dict, iterations: int = 3) -> FakeClient:
    client = FakeClient()
    stop = threading.Event()
    calls = {"n": 0}
    real_wait = stop.wait

    def fake_wait(timeout: float | None = None) -> bool:
        calls["n"] += 1
        if calls["n"] >= iterations:
            stop.set()
        return real_wait(0)

    stop.wait = fake_wait  # type: ignore[method-assign]
    with (
        patch.object(app, "CoolerControlClient", FakeCC),
        patch.object(app, "connect", lambda h, p: client),
    ):
        assert app.run(parse_config(cfg_raw), stop) == 0
    return client


def test_run_dry_does_not_write() -> None:
    client = _run({"write_leds": False, "smoothing_tau_s": 0})
    assert client.disconnected
    assert all(not d.colors and d.mode_set is None for d in client.devices)


def test_run_writes_colors_and_sets_direct_mode() -> None:
    client = _run({"write_leds": True, "smoothing_tau_s": 0})
    ram_1, ram_2, msi = client.devices
    assert ram_1.mode_set == "direct" and ram_2.mode_set is None
    assert ram_1.colors[0] == (0x20, 0x60, 0xFF)  # 45 °C: blue
    assert msi.zones[3].colors[-1] == ram_2.colors[-1]  # all zones follow the same colour
    assert msi.zones[0].colors == []  # JAF is not configured
    assert len(msi.zones[1].colors) == 2  # 45 °C then 75 °C; the repeat is skipped


def test_run_survives_temperature_errors() -> None:
    class FailingCC(FakeCC):
        def read_temp(self, uid: str, name: str) -> float:
            raise CoolerControlError("down")

    client = FakeClient()
    stop = threading.Event()
    stop.wait = lambda timeout=None: stop.set() or True  # type: ignore[method-assign]
    with (
        patch.object(app, "CoolerControlClient", FailingCC),
        patch.object(app, "connect", lambda h, p: client),
    ):
        assert app.run(parse_config({}), stop) == 0
    assert client.disconnected


def test_list_mode(capsys: pytest.CaptureFixture[str]) -> None:
    client = FakeClient()
    with (
        patch.object(app, "CoolerControlClient", FakeCC),
        patch.object(app, "connect", lambda h, p: client),
    ):
        assert app.list_mode(parse_config({})) == 0
    out = capsys.readouterr().out
    assert "45.0 °C" in out and "front    -> device 2 zone 3" in out
    assert "ram_1    -> device 0 whole device" in out


def test_unresolved_zone_is_skipped() -> None:
    zones = app._resolve_zones(
        FakeClient().devices, parse_config({"zones": [{"name": "gpu", "device": "ZOTAC"}]})
    )
    assert zones == []


def test_main_rejects_invalid_config(tmp_path: Path) -> None:
    bad = tmp_path / "config.json"
    bad.write_text('{"stops": []}', encoding="utf-8")
    with patch("sys.argv", ["thermal_rgb", "--config", str(bad)]):
        assert app.main() == 2


def test_main_list(tmp_path: Path) -> None:
    with (
        patch("sys.argv", ["thermal_rgb", "--config", str(tmp_path / "none.json"), "--list"]),
        patch.object(app, "list_mode", return_value=0) as list_mode,
    ):
        assert app.main() == 0
    list_mode.assert_called_once()


def test_main_retries_until_ready(tmp_path: Path) -> None:
    attempts = {"n": 0}

    def fake_run(cfg: object, stop: threading.Event, status_path: object = None) -> int:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise ConnectionError("openrgb not up")
        return 0

    with (
        patch("sys.argv", ["thermal_rgb", "--config", str(tmp_path / "none.json")]),
        patch.object(app, "run", fake_run),
        patch("threading.Event.wait", return_value=False),
    ):
        assert app.main() == 0
    assert attempts["n"] == 2


def test_sweep_writes_gradient_and_restores(capsys: pytest.CaptureFixture[str]) -> None:
    client = FakeClient()
    with (
        patch.object(app, "CoolerControlClient", FakeCC),
        patch.object(app, "connect", lambda h, p: client),
    ):
        assert app.sweep_mode(parse_config({}), 48, 82, 2, 0, sleep=lambda s: None) == 0
    ram_1 = client.devices[0]
    assert ram_1.mode_set == "direct"
    assert len(ram_1.colors) == 18 + 1  # 48..82 step 2, plus the restore
    assert ram_1.colors[0] == (0x20, 0x60, 0xFF)  # 48 °C: below the first stop
    assert ram_1.colors[-2] == (0xFF, 0, 0)  # 82 °C: red
    assert ram_1.colors[-1] == (0x20, 0x60, 0xFF)  # restored for 45 °C
    assert client.disconnected
    assert "restored colour for current CPU 45.0" in capsys.readouterr().out


def test_sweep_restore_failure_is_reported(capsys: pytest.CaptureFixture[str]) -> None:
    class FailingCC(FakeCC):
        def read_temp(self, uid: str, name: str) -> float:
            raise CoolerControlError("down")

    with (
        patch.object(app, "CoolerControlClient", FailingCC),
        patch.object(app, "connect", lambda h, p: FakeClient()),
    ):
        assert app.sweep_mode(parse_config({}), 50, 50, 1, 0, sleep=lambda s: None) == 0
    assert "could not restore" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("argv", "expected"), [([], (45.0, 85.0)), (["60"], (60.0, 85.0)), (["55", "75"], (55.0, 75.0))]
)
def test_main_sweep_bounds(tmp_path: Path, argv: list[str], expected: tuple[float, float]) -> None:
    with (
        patch("sys.argv", ["thermal_rgb", "--config", str(tmp_path / "n.json"), "--sweep", *argv]),
        patch.object(app, "sweep_mode", return_value=0) as sweep,
    ):
        assert app.main() == 0
    assert sweep.call_args.args[1:] == expected


def test_show_holds_one_colour(capsys: pytest.CaptureFixture[str]) -> None:
    client = FakeClient()
    with patch.object(app, "connect", lambda h, p: client):
        assert app.show_mode(parse_config({}), (255, 255, 0)) == 0
    assert client.devices[0].colors == [(255, 255, 0)]
    assert client.devices[2].zones[3].colors == [(255, 255, 0)]
    assert "showing #ffff00" in capsys.readouterr().out


@pytest.mark.parametrize(("value", "code"), [("#ffff00", 0), ("yellow", 2)])
def test_main_show(tmp_path: Path, value: str, code: int) -> None:
    with (
        patch("sys.argv", ["thermal_rgb", "--config", str(tmp_path / "n.json"), "--show", value]),
        patch.object(app, "show_mode", return_value=0),
    ):
        assert app.main() == code
