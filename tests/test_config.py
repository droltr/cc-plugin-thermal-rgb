import json
from pathlib import Path

import pytest

from thermal_rgb.config import ConfigError, load_config, parse_config


def test_defaults_match_documented_values() -> None:
    cfg = parse_config({})
    assert [s.temp_c for s in cfg.stops] == [50, 60, 70, 80]
    assert cfg.stops[0].rgb == (0x20, 0x60, 0xFF)
    assert [z.name for z in cfg.zones] == ["rear_1", "rear_2", "ram_1", "ram_2", "front"]
    assert cfg.write_leds is True
    assert cfg.temp_name == "temp1"


def test_custom_values() -> None:
    cfg = parse_config(
        {
            "coolercontrol_url": "http://127.0.0.1:11987/",
            "write_leds": True,
            "poll_interval_s": 2,
            "stops": [{"temp_c": 40, "color": "#000000"}],
            "zones": [{"name": "a", "device": "D", "zone": "Z"}],
        }
    )
    assert cfg.coolercontrol_url == "http://127.0.0.1:11987"
    assert cfg.write_leds is True
    assert cfg.zones[0].zone == "Z"
    assert cfg.zones[0].location is None


@pytest.mark.parametrize(
    "raw",
    [
        {"stops": []},
        {"stops": [{"temp_c": 50}]},
        {"stops": [{"temp_c": 50, "color": "nope"}]},
        {"zones": [{"name": "x"}]},
        {"zones": [{"name": "x", "device": "D"}, {"name": "x", "device": "E"}]},
        {"poll_interval_s": 0.01},
        {"openrgb_port": 80},
        [],
    ],
)
def test_invalid_config_rejected(raw: object) -> None:
    with pytest.raises((ConfigError, ValueError)):
        parse_config(raw)  # type: ignore[arg-type]


def test_load_missing_file_gives_defaults(tmp_path: Path) -> None:
    assert load_config(tmp_path / "missing.json").write_leds is True


def test_load_file(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"temp_name": "temp3"}), encoding="utf-8")
    assert load_config(path).temp_name == "temp3"


def test_load_bad_json(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text("{oops", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(path)


def _write_config(tmp_path: Path, raw: dict[str, object]) -> Path:
    path = tmp_path / "config.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def test_new_token_moves_to_credentials_and_is_masked(tmp_path: Path) -> None:
    path = _write_config(tmp_path, {"coolercontrol_token": " cc_abc ", "temp_name": "temp3"})
    cfg = load_config(path)
    assert cfg.coolercontrol_token == "cc_abc"
    creds = tmp_path / "credentials.json"
    assert json.loads(creds.read_text(encoding="utf-8")) == {"coolercontrol_token": "cc_abc"}
    assert creds.stat().st_mode & 0o777 == 0o600
    rewritten = json.loads(path.read_text(encoding="utf-8"))
    assert rewritten == {"coolercontrol_token": "***", "temp_name": "temp3"}


@pytest.mark.parametrize("placeholder", ["***", "", "  "])
def test_mask_or_empty_keeps_stored_token(tmp_path: Path, placeholder: str) -> None:
    (tmp_path / "credentials.json").write_text(
        '{"coolercontrol_token": "cc_old"}', encoding="utf-8"
    )
    path = _write_config(tmp_path, {"coolercontrol_token": placeholder})
    assert load_config(path).coolercontrol_token == "cc_old"
    assert json.loads(path.read_text(encoding="utf-8"))["coolercontrol_token"] == placeholder


def test_new_token_replaces_stored_one(tmp_path: Path) -> None:
    (tmp_path / "credentials.json").write_text(
        '{"coolercontrol_token": "cc_old"}', encoding="utf-8"
    )
    path = _write_config(tmp_path, {"coolercontrol_token": "cc_new"})
    assert load_config(path).coolercontrol_token == "cc_new"
    assert load_config(path).coolercontrol_token == "cc_new"  # second start reads the mask


def test_no_token_anywhere_is_empty(tmp_path: Path) -> None:
    assert load_config(_write_config(tmp_path, {})).coolercontrol_token == ""


def test_missing_config_still_reads_credentials(tmp_path: Path) -> None:
    (tmp_path / "credentials.json").write_text('{"coolercontrol_token": "cc_x"}', encoding="utf-8")
    assert load_config(tmp_path / "config.json").coolercontrol_token == "cc_x"


def test_corrupt_credentials_gives_empty_token(tmp_path: Path) -> None:
    (tmp_path / "credentials.json").write_text("{oops", encoding="utf-8")
    assert load_config(_write_config(tmp_path, {})).coolercontrol_token == ""


def test_unwritable_folder_falls_back_to_config_token(tmp_path: Path) -> None:
    path = _write_config(tmp_path, {"coolercontrol_token": "cc_abc"})
    tmp_path.chmod(0o500)
    try:
        assert load_config(path).coolercontrol_token == "cc_abc"
    finally:
        tmp_path.chmod(0o700)
