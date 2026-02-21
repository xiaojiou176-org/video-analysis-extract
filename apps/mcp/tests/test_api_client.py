from __future__ import annotations

from typing import Any

import httpx
import pytest

from apps.mcp.server import ApiClient, ApiConfig, ApiError, _normalize_error_details


class _DummyClient:
    def __init__(self, response: httpx.Response | None = None, exc: Exception | None = None) -> None:
        self._response = response
        self._exc = exc

    def __enter__(self) -> "_DummyClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def request(self, **kwargs: Any) -> httpx.Response:
        if self._exc is not None:
            raise self._exc
        assert self._response is not None
        return self._response


def _response(
    *,
    status_code: int = 200,
    json_body: Any | None = None,
    text: str = "",
    content_type: str = "application/json",
) -> httpx.Response:
    request = httpx.Request("GET", "http://example.test/path")
    if json_body is not None:
        return httpx.Response(
            status_code=status_code,
            json=json_body,
            headers={"content-type": content_type},
            request=request,
        )
    return httpx.Response(
        status_code=status_code,
        text=text,
        headers={"content-type": content_type},
        request=request,
    )


def test_api_client_returns_json_dict(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "apps.mcp.server.httpx.Client",
        lambda timeout: _DummyClient(response=_response(json_body={"ok": True})),
    )
    client = ApiClient(ApiConfig(base_url="http://api", timeout_sec=2, api_key=None))

    payload = client.request("GET", "/healthz")

    assert payload["ok"] is True


def test_api_client_wraps_non_json_as_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "apps.mcp.server.httpx.Client",
        lambda timeout: _DummyClient(
            response=_response(
                text="plain text body",
                content_type="text/plain",
            )
        ),
    )
    client = ApiClient(ApiConfig(base_url="http://api", timeout_sec=2, api_key=None))

    payload = client.request("GET", "/plain")

    assert payload["text"] == "plain text body"


def test_api_client_raises_api_error_for_http_500(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "apps.mcp.server.httpx.Client",
        lambda timeout: _DummyClient(
            response=_response(status_code=500, json_body={"message": "server exploded"})
        ),
    )
    client = ApiClient(ApiConfig(base_url="http://api", timeout_sec=2, api_key=None))

    with pytest.raises(ApiError) as exc_info:
        client.request("GET", "/boom")

    err = exc_info.value
    assert err.code == "UPSTREAM_HTTP_ERROR"
    assert err.message == "server exploded"
    assert err.details["status_code"] == 500


def test_api_client_maps_timeout_to_upstream_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    timeout_exc = httpx.TimeoutException("timed out")
    monkeypatch.setattr(
        "apps.mcp.server.httpx.Client",
        lambda timeout: _DummyClient(exc=timeout_exc),
    )
    client = ApiClient(ApiConfig(base_url="http://api", timeout_sec=2, api_key=None))

    with pytest.raises(ApiError) as exc_info:
        client.request("POST", "/slow")

    err = exc_info.value
    assert err.code == "UPSTREAM_TIMEOUT"
    assert err.details["path"] == "/slow"


def test_normalize_error_details_keeps_expected_fields_only() -> None:
    normalized = _normalize_error_details(
        {
            "method": "GET",
            "path": "/x",
            "status_code": 503,
            "error": {"reason": "timeout"},
            "body": {"detail": "bad"},
            "ignored": "x",
        }
    )

    assert normalized["method"] == "GET"
    assert normalized["status_code"] == 503
    assert "timeout" in normalized["error"]
    assert "bad" in normalized["body"]
    assert "ignored" not in normalized
