from __future__ import annotations

from urllib.parse import urlencode


def build_models_probe_url(api_key: str) -> str:
    return "https://generativelanguage.googleapis.com/v1beta/models?" + urlencode({"key": api_key})
