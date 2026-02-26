from __future__ import annotations

from typing import Any, Self

import httpx
import pytest

from apps.mcp.server import ApiClient, ApiConfig, ApiError, _normalize_error_details


class _DummyClient:
    def __init__(
        self, response: httpx.Response | None = None, exc: Exception | None = None
    ) -> None:
        self._response = response
        self._exc = exc

    def __enter__(self) -> Self:
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
            "body_preview": {"detail": "bad"},
            "size_bytes": 1024,
            "max_size_bytes": 256,
            "ignored": "x",
        }
    )

    assert normalized["method"] == "GET"
    assert normalized["status_code"] == 503
    assert "timeout" in normalized["error"]
    assert "bad" in normalized["body_preview"]
    assert normalized["size_bytes"] == 1024
    assert normalized["max_size_bytes"] == 256
    assert "ignored" not in normalized


def test_normalize_error_details_redacts_secrets() -> None:
    normalized = _normalize_error_details(
        {
            "method": "GET",
            "path": "/x",
            "error": "Authorization: Bearer super-secret-token",
            "body_preview": '{"token":"abc","api_key=secret-key"}',
        }
    )

    assert "super-secret-token" not in normalized["error"]
    assert "[REDACTED]" in normalized["error"]
    assert "secret-key" not in normalized["body_preview"]
    assert "[REDACTED]" in normalized["body_preview"]


def test_api_error_to_payload_redacts_message_and_json_style_secret() -> None:
    err = ApiError(
        "UPSTREAM_HTTP_ERROR",
        'upstream rejected {"token":"top-secret-token"}',
        details={"method": "GET", "path": "/x"},
    )
    payload = err.to_payload()

    assert payload["code"] == "UPSTREAM_HTTP_ERROR"
    assert "top-secret-token" not in payload["message"]
    assert "[REDACTED]" in payload["message"]


def test_api_client_rejects_invalid_absolute_or_empty_path() -> None:
    client = ApiClient(ApiConfig(base_url="http://api", timeout_sec=2, api_key=None))

    with pytest.raises(ApiError) as empty_path_error:
        client.request("GET", "")
    with pytest.raises(ApiError) as absolute_path_error:
        client.request("GET", "https://attacker.example/boom")

    assert empty_path_error.value.code == "INVALID_UPSTREAM_PATH"
    assert absolute_path_error.value.code == "INVALID_UPSTREAM_PATH"


def test_api_client_rejects_path_traversal_and_query_fragment_path() -> None:
    client = ApiClient(ApiConfig(base_url="http://api", timeout_sec=2, api_key=None))

    with pytest.raises(ApiError) as traversal_path_error:
        client.request("GET", "/api/v1/jobs/../../secrets")
    with pytest.raises(ApiError) as query_path_error:
        client.request("GET", "/api/v1/jobs?status=ok")
    with pytest.raises(ApiError) as fragment_path_error:
        client.request("GET", "/api/v1/jobs#frag")

    assert traversal_path_error.value.code == "INVALID_UPSTREAM_PATH"
    assert query_path_error.value.code == "INVALID_UPSTREAM_PATH"
    assert fragment_path_error.value.code == "INVALID_UPSTREAM_PATH"


def test_api_client_rejects_oversized_base64_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "apps.mcp.server.httpx.Client",
        lambda timeout: _DummyClient(
            response=_response(
                text="abc",
                content_type="application/octet-stream",
            )
        ),
    )
    client = ApiClient(
        ApiConfig(
            base_url="http://api",
            timeout_sec=2,
            api_key=None,
            max_base64_bytes=2,
        )
    )

    with pytest.raises(ApiError) as exc_info:
        client.request("GET", "/binary", return_bytes_base64=True)

    err = exc_info.value
    assert err.code == "PAYLOAD_TOO_LARGE"
    assert err.details["size_bytes"] == 3
    assert err.details["max_size_bytes"] == 2
