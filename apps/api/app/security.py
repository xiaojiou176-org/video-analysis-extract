from __future__ import annotations

import re

_SENSITIVE_TEXT_PATTERNS = (
    (re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.IGNORECASE), "Bearer ***REDACTED***"),
    (re.compile(r"(sk-[A-Za-z0-9]{20,})"), "sk-***REDACTED***"),
    (re.compile(r"(ghp_[A-Za-z0-9]{20,})"), "ghp_***REDACTED***"),
    (re.compile(r"(AKIA[0-9A-Z]{16})"), "AKIA***REDACTED***"),
    (
        re.compile(
            r"([?&](?:api[_-]?key|apikey|key|token|secret|password|auth(?:orization)?|signature)=)[^&\s]+",
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
