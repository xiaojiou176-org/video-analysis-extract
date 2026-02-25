from __future__ import annotations

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from apps.api.app.security import require_write_access


def test_require_write_access_rejects_when_api_key_not_configured_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VD_API_KEY", raising=False)
    monkeypatch.delenv("VD_ALLOW_UNAUTH_WRITE", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        require_write_access(
            bearer=None,
            api_key_header=None,
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "write access token required"


def test_require_write_access_allows_when_unauth_write_switch_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VD_API_KEY", raising=False)
    monkeypatch.setenv("VD_ALLOW_UNAUTH_WRITE", "true")
    require_write_access(
        bearer=None,
        api_key_header=None,
    )


def test_require_write_access_rejects_bearer_when_api_key_not_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VD_API_KEY", raising=False)
    monkeypatch.delenv("VD_ALLOW_UNAUTH_WRITE", raising=False)
    with pytest.raises(HTTPException) as exc_info:
        require_write_access(
            bearer=HTTPAuthorizationCredentials(scheme="Bearer", credentials="provided-token"),
            api_key_header=None,
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "write access token required"


def test_require_write_access_falls_back_to_x_api_key_when_auth_scheme_is_not_bearer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VD_API_KEY", "unit-test-token")
    require_write_access(
        bearer=HTTPAuthorizationCredentials(scheme="Basic", credentials="ignored"),
        api_key_header=" unit-test-token ",
    )


def test_require_write_access_rejects_when_no_usable_token_provided(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VD_API_KEY", "unit-test-token")
    with pytest.raises(HTTPException) as exc_info:
        require_write_access(
            bearer=HTTPAuthorizationCredentials(scheme="Digest", credentials="ignored"),
            api_key_header="   ",
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert exc_info.value.detail == "write access token required"


def test_require_write_access_prefers_bearer_and_rejects_mismatch_even_if_x_api_key_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VD_API_KEY", "unit-test-token")
    with pytest.raises(HTTPException) as exc_info:
        require_write_access(
            bearer=HTTPAuthorizationCredentials(scheme="Bearer", credentials="wrong-token"),
            api_key_header="unit-test-token",
        )

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert exc_info.value.detail == "invalid write access token"
