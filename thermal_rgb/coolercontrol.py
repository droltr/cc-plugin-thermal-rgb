"""Minimal read-only CoolerControl REST client (standard library only)."""

import json
import urllib.error
import urllib.request
from typing import Any


class CoolerControlError(RuntimeError):
    pass


class CoolerControlClient:
    def __init__(self, base_url: str, token: str, timeout_s: float = 3.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._token = token
        self._timeout_s = timeout_s

    def _get(self, path: str) -> Any:
        request = urllib.request.Request(f"{self._base_url}{path}")
        if self._token:
            request.add_header("Authorization", f"Bearer {self._token}")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_s) as response:
                return json.load(response)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as err:
            raise CoolerControlError(f"GET {path} failed: {err}") from err

    def status(self) -> dict[str, Any]:
        data = self._get("/status")
        if not isinstance(data, dict) or "devices" not in data:
            raise CoolerControlError(f"unexpected /status response: {str(data)[:200]}")
        return data

    def read_temp(self, device_uid: str, temp_name: str) -> float:
        return find_temp(self.status(), device_uid, temp_name)

    def first_cpu_uid(self) -> str:
        """UID of the first CPU device, used when no temp_device_uid is configured."""
        for device in self.status()["devices"]:
            if device.get("type") == "CPU":
                return str(device["uid"])
        raise CoolerControlError("no CPU device reported by CoolerControl")


def find_temp(status: dict[str, Any], device_uid: str, temp_name: str) -> float:
    for device in status.get("devices", []):
        if device.get("uid") != device_uid:
            continue
        history = device.get("status_history") or []
        if not history:
            break
        for temp in history[-1].get("temps", []):
            if temp.get("name") == temp_name:
                return float(temp["temp"])
        break
    raise CoolerControlError(f"temperature {temp_name!r} not found for device {device_uid[:8]}")
