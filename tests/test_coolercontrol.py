import io
import json
import urllib.error
from unittest.mock import patch

import pytest

from thermal_rgb.coolercontrol import CoolerControlClient, CoolerControlError, find_temp

STATUS = {
    "devices": [
        {
            "type": "GPU",
            "uid": "gpu",
            "status_history": [{"temps": [{"name": "GPU Temp", "temp": 50}]}],
        },
        {
            "type": "CPU",
            "uid": "cpu",
            "status_history": [
                {"temps": [{"name": "temp1", "temp": 40.0}]},
                {"temps": [{"name": "temp1", "temp": 42.5}, {"name": "temp3", "temp": 35}]},
            ],
        },
        {"type": "Hwmon", "uid": "empty", "status_history": []},
    ]
}


def test_find_temp_uses_latest_sample() -> None:
    assert find_temp(STATUS, "cpu", "temp1") == 42.5


@pytest.mark.parametrize(("uid", "name"), [("cpu", "temp9"), ("nope", "temp1"), ("empty", "temp1")])
def test_find_temp_missing(uid: str, name: str) -> None:
    with pytest.raises(CoolerControlError):
        find_temp(STATUS, uid, name)


class _Response(io.BytesIO):
    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


def test_client_reads_temp_with_token() -> None:
    seen = {}

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        seen["auth"] = request.get_header("Authorization")
        seen["url"] = request.full_url
        return _Response(json.dumps(STATUS).encode())

    with patch("urllib.request.urlopen", fake_urlopen):
        client = CoolerControlClient("http://cc/", "tok")
        assert client.read_temp("cpu", "temp1") == 42.5
        assert client.first_cpu_uid() == "cpu"
    assert seen == {"auth": "Bearer tok", "url": "http://cc/status"}


def test_client_errors_are_wrapped() -> None:
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
        with pytest.raises(CoolerControlError):
            CoolerControlClient("http://cc", "").status()


def test_unexpected_payload() -> None:
    with patch("urllib.request.urlopen", lambda r, timeout: _Response(b'{"error": "x"}')):
        with pytest.raises(CoolerControlError):
            CoolerControlClient("http://cc", "").status()


def test_no_cpu_device() -> None:
    payload = {"devices": [{"type": "GPU", "uid": "g"}]}
    with patch(
        "urllib.request.urlopen", lambda r, timeout: _Response(json.dumps(payload).encode())
    ):
        with pytest.raises(CoolerControlError):
            CoolerControlClient("http://cc", "").first_cpu_uid()
