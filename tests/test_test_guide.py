"""Tests for the user-test guide server (tools/test-guide/serve.py): safety rules, reports."""

import hashlib
import importlib.util
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import ModuleType

import pytest

SERVE = Path(__file__).resolve().parents[1] / "tools" / "test-guide" / "serve.py"
SESSION = "001-2026-01-01-demo"


@pytest.fixture
def serve(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    spec = importlib.util.spec_from_file_location("test_guide_serve", SERVE)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    project = tmp_path / "demo"
    (project / "tests" / "user" / SESSION).mkdir(parents=True)
    monkeypatch.setattr(module, "PROJECT", "demo")
    monkeypatch.setattr(module, "PROJECT_DIR", project)
    monkeypatch.setattr(module, "SESSIONS_DIR", project / "tests" / "user")
    monkeypatch.setattr(module, "REPORT_ROOT", project / ".private" / "test-reports")
    return module


def write_session(serve: ModuleType, **extra: object) -> Path:
    data = {
        "project": "demo",
        "title": "Demo",
        "target_version": "1.2.3",
        "sections": [
            {
                "id": "a",
                "title": "A",
                "tests": [{"id": "T1", "title": "t", "steps": [], "expected": "e"}],
            }
        ],
        **extra,
    }
    path = serve.SESSIONS_DIR / SESSION / "tests.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_argv_rules(serve: ModuleType) -> None:
    assert serve.argv_problem(["grep", "x", "file"]) is None
    assert serve.argv_problem(["systemctl", "is-active", "x"]) is None
    assert "not allowed" in serve.argv_problem(["sudo", "true"])
    assert "not allowed" in serve.argv_problem(["rm", "-rf", "/"])
    assert "may only be used" in serve.argv_problem(["systemctl", "restart", "x"])
    assert "may only be used" in serve.argv_problem(["git", "push"])
    assert serve.argv_problem([]) is not None
    assert serve.argv_problem("grep") is not None


def test_session_names_cannot_escape(serve: ModuleType) -> None:
    write_session(serve)
    assert serve.session_file(SESSION) is not None
    for bad in ("", "../x", "a/b", "..", "nope", None):
        assert serve.session_file(bad) is None


def test_list_sessions_newest_first(serve: ModuleType) -> None:
    write_session(serve)
    other = serve.SESSIONS_DIR / "002-2026-01-02-next"
    other.mkdir()
    (other / "tests.json").write_text(json.dumps({"sections": [{"tests": []}]}), encoding="utf-8")
    (serve.SESSIONS_DIR / "003-broken").mkdir()
    (serve.SESSIONS_DIR / "003-broken" / "tests.json").write_text("{oops", encoding="utf-8")
    assert [s["name"] for s in serve.list_sessions()] == ["002-2026-01-02-next", SESSION]


def test_check_results(serve: ModuleType) -> None:
    ok = serve.run_check(
        {
            "title": "v",
            "argv": ["python3", "-I", "-c", "print('1.2.3')"],
            "expect": "^{{target_version}}$",
        },
        "1.2.3",
    )
    assert ok["ok"] and ok["title"] == "v" and "1.2.3" in ok["detail"]
    wrong = serve.run_check({"argv": ["python3", "-I", "-c", "print('9')"], "expect": "^1$"}, "")
    assert not wrong["ok"] and "does not match" in wrong["detail"]
    failing = serve.run_check({"argv": ["python3", "-I", "-c", "raise SystemExit(3)"]}, "")
    assert not failing["ok"] and "exit code 3" in failing["detail"]
    expected_exit = serve.run_check(
        {"argv": ["python3", "-I", "-c", "raise SystemExit(3)"], "expect_exit": 3}, ""
    )
    assert expected_exit["ok"]
    info = serve.run_check(
        {"argv": ["python3", "-I", "-c", "raise SystemExit(1)"], "info": True}, ""
    )
    assert info["ok"] and info["info"]
    refused = serve.run_check({"argv": ["sudo", "-n", "true"]}, "")
    assert not refused["ok"] and "not allowed" in refused["detail"]
    nonempty = serve.run_check(
        {"argv": ["python3", "-I", "-c", "print('x')"], "expect_empty": True}, ""
    )
    assert not nonempty["ok"]
    slow = serve.run_check(
        {"argv": ["python3", "-I", "-c", "import time; time.sleep(5)"], "timeout": 1}, ""
    )
    assert not slow["ok"] and slow["detail"] == "timed out"
    missing = serve.run_check({"argv": ["ls", "/definitely/missing"]}, "")
    assert not missing["ok"]


def test_preflight_checks_project_identity(serve: ModuleType) -> None:
    write_session(serve, project="someone-else")
    result = serve.run_preflight(SESSION)
    assert not result["ok"]
    assert result["results"][0]["id"] == "project" and not result["results"][0]["ok"]


def test_preflight_aggregates_checks(serve: ModuleType, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(serve, "PROJECT_DIR", serve.PROJECT_DIR.parent / "demo")
    write_session(
        serve,
        preflight=[
            {
                "id": "a",
                "title": "A",
                "argv": ["python3", "-I", "-c", "print('1.2.3')"],
                "expect": "^{{target_version}}$",
            },
            {"id": "i", "title": "I", "info": True, "argv": ["ls", "/definitely/missing"]},
        ],
    )
    result = serve.run_preflight(SESSION)
    assert result["ok"] and result["target_version"] == "1.2.3"
    assert [r["id"] for r in result["results"]] == ["project", "a", "i"]


def make_report(serve: ModuleType, sha: str, **overrides: object) -> dict:
    return {
        "created": "2026-01-01T00:00:00Z",
        "guide": "g",
        "project": "demo",
        "project_path": str(serve.PROJECT_DIR),
        "session": SESSION,
        "tests_sha256": sha,
        "results": [
            {
                "section": "A",
                "tests": [
                    {"id": "T1", "title": "t", "expected": "e", "result": "pass", "note": "a|b"}
                ],
            }
        ],
        **overrides,
    }


def test_reports_are_numbered_and_never_overwritten(serve: ModuleType) -> None:
    path = write_session(serve)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    pre = {"ok": True, "results": []}
    first = serve.save_report({**make_report(serve, sha), "preflight": pre})
    second = serve.save_report({**make_report(serve, sha), "preflight": pre})
    assert first[0].endswith(f"demo__{SESSION}__run01.json")
    assert second[0].endswith(f"demo__{SESSION}__run02.json")
    run1 = json.loads((serve.PROJECT_DIR / first[0]).read_text(encoding="utf-8"))
    assert run1["run"] == 1
    markdown = (serve.PROJECT_DIR / second[1]).read_text(encoding="utf-8")
    assert "run 02" in markdown and "a\\|b" in markdown and "demo" in markdown


def test_numbering_skips_taken_files(serve: ModuleType) -> None:
    path = write_session(serve)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    out = serve.REPORT_ROOT / SESSION
    out.mkdir(parents=True)
    (out / f"demo__{SESSION}__run05.json").write_text("{}", encoding="utf-8")
    files = serve.save_report({**make_report(serve, sha), "preflight": {"ok": True, "results": []}})
    assert files[0].endswith("run06.json")


@pytest.fixture
def server(serve: ModuleType, monkeypatch: pytest.MonkeyPatch):
    httpd = ThreadingHTTPServer((serve.HOST, 0), serve.Handler)
    origin = f"http://{serve.HOST}:{httpd.server_address[1]}"
    monkeypatch.setattr(serve, "ORIGIN", origin)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield origin
    httpd.shutdown()
    httpd.server_close()


def parse(raw: bytes) -> dict:
    try:
        return json.loads(raw or b"{}")
    except ValueError:  # e.g. the HTML body of a plain 404
        return {}


def call(
    origin: str, path: str, body: object = None, headers: dict | None = None
) -> tuple[int, dict, dict]:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(origin + path, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, parse(response.read()), dict(response.headers)
    except urllib.error.HTTPError as err:
        return err.code, parse(err.read()), dict(err.headers)


def test_http_info_sessions_and_tests(serve: ModuleType, server: str) -> None:
    path = write_session(serve)
    assert call(server, "/api/info")[1]["project"] == "demo"
    assert call(server, "/api/sessions")[1][0]["name"] == SESSION
    status, _, headers = call(server, f"/tests.json?session={SESSION}")
    assert (
        status == 200 and headers["X-Tests-Sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    )
    assert call(server, "/tests.json?session=..%2F..%2Fetc")[0] == 404
    assert call(server, "/missing")[0] == 404


def test_http_report_rules(serve: ModuleType, server: str) -> None:
    path = write_session(serve)
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    own = {"Origin": server, "Content-Type": "application/json"}
    assert (
        call(server, "/api/report", make_report(serve, sha), {"Origin": "http://evil.example"})[0]
        == 403
    )
    assert call(server, "/api/report", make_report(serve, sha, project="other"), own)[0] == 409
    assert (
        call(server, "/api/report", make_report(serve, sha, project_path="/elsewhere"), own)[0]
        == 409
    )
    assert call(server, "/api/report", make_report(serve, "deadbeef"), own)[0] == 409
    assert call(server, "/api/report", make_report(serve, sha, session="zzz"), own)[0] == 400
    assert call(server, "/api/report", {"nonsense": True}, own)[0] == 400
    status, body, _ = call(server, "/api/report", make_report(serve, sha), own)
    assert (
        status == 200 and body["preflight_ok"] is True and body["files"][0].endswith("run01.json")
    )


def test_http_failed_preflight_needs_acknowledgement(serve: ModuleType, server: str) -> None:
    path = write_session(
        serve,
        preflight=[
            {"id": "x", "title": "X", "argv": ["python3", "-I", "-c", "print(1)"], "expect": "^2$"}
        ],
    )
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    own = {"Origin": server, "Content-Type": "application/json"}
    status, body, _ = call(server, "/api/preflight", {"session": SESSION}, own)
    assert status == 200 and body["ok"] is False
    assert call(server, "/api/preflight", {"session": "nope"}, own)[0] == 400
    assert call(server, "/api/report", make_report(serve, sha), own)[0] == 409
    status, body, _ = call(
        server, "/api/report", make_report(serve, sha, ack_preflight_failure=True), own
    )
    assert status == 200 and body["preflight_ok"] is False
    saved = json.loads((serve.PROJECT_DIR / body["files"][0]).read_text(encoding="utf-8"))
    assert saved["ack_preflight_failure"] is True and saved["preflight"]["ok"] is False


def test_http_rejects_bad_bodies(serve: ModuleType, server: str) -> None:
    write_session(serve)
    own = {"Origin": server}
    request = urllib.request.Request(server + "/api/report", data=b"{oops", headers=own)
    with pytest.raises(urllib.error.HTTPError) as err:
        urllib.request.urlopen(request, timeout=10)
    assert err.value.code == 400
    empty = urllib.request.Request(server + "/api/report", data=b"", headers=own)
    with pytest.raises(urllib.error.HTTPError) as empty_err:
        urllib.request.urlopen(empty, timeout=10)
    assert empty_err.value.code == 413
    assert call(server, "/api/other", {}, own)[0] == 404
