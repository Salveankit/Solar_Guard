from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_API_URL = "http://localhost:8000"


class SolarGuardApiError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class SolarGuardApiClient:
    base_url: str = DEFAULT_API_URL
    timeout_seconds: float = 8.0
    retries: int = 1

    @classmethod
    def from_env(cls) -> SolarGuardApiClient:
        return cls(
            base_url=os.getenv("SOLARGUARD_API_URL", DEFAULT_API_URL).rstrip("/"),
            timeout_seconds=float(os.getenv("SOLARGUARD_API_TIMEOUT_SECONDS", "8")),
            retries=int(os.getenv("SOLARGUARD_API_RETRIES", "1")),
        )

    def get_json(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request_json("GET", path, params=params)

    def post_json(self, path: str, payload: dict[str, Any]) -> Any:
        return self._request_json("POST", path, payload=payload)

    def get_bytes(self, path: str, params: dict[str, Any] | None = None) -> bytes:
        return self._request("GET", path, params=params)

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        body = self._request(method, path, params=params, payload=payload)
        try:
            return json.loads(body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise SolarGuardApiError("The API returned an invalid response.") from exc

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> bytes:
        url = self._url(path, params)
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Content-Type": "application/json"} if payload is not None else {}
        request = Request(url, data=data, headers=headers, method=method)
        attempts = max(self.retries, 0) + 1
        last_error: Exception | None = None
        for attempt in range(attempts):
            try:
                with urlopen(request, timeout=self.timeout_seconds) as response:
                    return response.read()
            except HTTPError as exc:
                raise SolarGuardApiError(
                    self._http_error_message(exc),
                    status_code=exc.code,
                ) from exc
            except TimeoutError as exc:
                last_error = exc
            except URLError as exc:
                last_error = exc
            if attempt < attempts - 1:
                time.sleep(0.2 * (attempt + 1))
        raise SolarGuardApiError(
            "SolarGuard API is unavailable. Start FastAPI and retry."
        ) from last_error

    def _url(self, path: str, params: dict[str, Any] | None = None) -> str:
        suffix = path if path.startswith("/") else f"/{path}"
        query = ""
        if params:
            filtered = {key: value for key, value in params.items() if value is not None}
            query = f"?{urlencode(filtered)}" if filtered else ""
        return f"{self.base_url}{suffix}{query}"

    @staticmethod
    def _http_error_message(error: HTTPError) -> str:
        try:
            payload = json.loads(error.read().decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return f"API request failed with status {error.code}."
        detail = payload.get("error") or payload.get("detail")
        if isinstance(detail, dict):
            return str(detail.get("message") or detail.get("code") or "API request failed.")
        return str(detail or f"API request failed with status {error.code}.")
