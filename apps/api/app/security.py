from __future__ import annotations

import os
import re
import secrets

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

_bearer_security = HTTPBearer(auto_error=False)
_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

_SENSITIVE_TEXT_PATTERNS = (
    (re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE), "Bearer ***REDACTED***"),
    (re.compile(r"Basic\s+[A-Za-z0-9+/=._\-]+", re.IGNORECASE), "Basic ***REDACTED***"),
    (
        re.compile(r"([a-z][a-z0-9+.\-]*://)([^:@/\s]+):([^@/\s]+)@", re.IGNORECASE),
        r"\1***:***@",
    ),
    (re.compile(r"(sk-[A-Za-z0-9]{20,})"), "sk-***REDACTED***"),
    (re.compile(r"(ghp_[A-Za-z0-9]{20,})"), "ghp_***REDACTED***"),
    (re.compile(r"(AKIA[0-9A-Z]{16})"), "AKIA***REDACTED***"),
    (
        re.compile(
            r"([?&](?:api[_-]?key|apikey|key|token|access[_-]?token|refresh[_-]?token|id[_-]?token|oauth[_-]?token|jwt|secret|client[_-]?secret|password|passwd|session(?:id)?|auth(?:orization)?|signature)=)[^&\s]+",
            re.IGNORECASE,
        ),
        r"\1***REDACTED***",
    ),
)


def sanitize_exception_detail(exc: Exception, *, fallback: str = "internal_error", max_chars: int = 500) -> str:
    detail = str(exc).strip()
    if not detail:
        return fallback
    sanitized = detail
    for pattern, replacement in _SENSITIVE_TEXT_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)
    if len(sanitized) > max_chars:
        return f"{sanitized[:max_chars]}...[truncated]"
    return sanitized


def _configured_api_key() -> str | None:
    configured = os.getenv("VD_API_KEY")
    if configured is None:
        return None
    value = configured.strip()
    return value if value else None


def _allow_unauth_write() -> bool:
    raw = os.getenv("VD_ALLOW_UNAUTH_WRITE")
    if raw is None:
        return False
    value = raw.strip().lower()
    return value in {"1", "true", "yes", "on"}


def require_write_access(
    bearer: HTTPAuthorizationCredentials | None = Security(_bearer_security),
    api_key_header: str | None = Security(_api_key_header),
) -> None:
    expected = _configured_api_key()
    if expected is None:
        if _allow_unauth_write():
            return
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="write access token required",
        )

    provided: str | None = None
    if bearer is not None and bearer.scheme.lower() == "bearer":
        provided = bearer.credentials
    if provided is None and isinstance(api_key_header, str) and api_key_header.strip():
        provided = api_key_header.strip()

    if provided is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="write access token required",
        )
    if not secrets.compare_digest(provided, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="invalid write access token",
        )
