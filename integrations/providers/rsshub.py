from __future__ import annotations


def build_health_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/healthz"
