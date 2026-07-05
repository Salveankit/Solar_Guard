from __future__ import annotations

import json
from io import BytesIO
from urllib.error import HTTPError, URLError

import pytest

from dashboard.api_client import SolarGuardApiClient, SolarGuardApiError


class _Response:
    def __init__(self, body: bytes) -> None:
        self.body = body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def test_api_client_handles_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(_request, timeout: float):
        assert timeout == 2
        return _Response(json.dumps({"status": "ok"}).encode())

    monkeypatch.setattr("dashboard.api_client.urlopen", fake_urlopen)
    client = SolarGuardApiClient("http://api", timeout_seconds=2, retries=0)

    assert client.get_json("/health") == {"status": "ok"}


def test_api_client_handles_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(_request, timeout: float):
        raise TimeoutError

    monkeypatch.setattr("dashboard.api_client.urlopen", fake_urlopen)
    client = SolarGuardApiClient("http://api", timeout_seconds=1, retries=0)

    with pytest.raises(SolarGuardApiError, match="unavailable"):
        client.get_json("/health")


def test_api_client_handles_backend_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    body = json.dumps({"detail": "No route plan is available"}).encode()

    def fake_urlopen(_request, timeout: float):
        raise HTTPError("http://api", 404, "not found", {}, BytesIO(body))

    monkeypatch.setattr("dashboard.api_client.urlopen", fake_urlopen)
    client = SolarGuardApiClient("http://api", retries=0)

    with pytest.raises(SolarGuardApiError) as exc:
        client.get_json("/api/routes/latest")
    assert exc.value.status_code == 404
    assert "No route plan" in str(exc.value)


def test_api_client_retries_connection_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    attempts = {"count": 0}

    def fake_urlopen(_request, timeout: float):
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise URLError("temporary")
        return _Response(b'{"status":"ok"}')

    monkeypatch.setattr("dashboard.api_client.urlopen", fake_urlopen)
    client = SolarGuardApiClient("http://api", retries=1)

    assert client.get_json("/health") == {"status": "ok"}
    assert attempts["count"] == 2
