from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_MAPPING_FILE = Path(__file__).resolve().parents[4] / "data" / "subscriptions.up_names.json"


@lru_cache(maxsize=1)
def _load_mappings() -> dict[str, dict[str, str]]:
    try:
        payload = json.loads(_MAPPING_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    result: dict[str, dict[str, str]] = {}
    for source_type, values in payload.items():
        if not isinstance(source_type, str) or not isinstance(values, dict):
            continue
        normalized_values: dict[str, str] = {}
        for key, value in values.items():
            if isinstance(key, str) and isinstance(value, str):
                normalized_values[key.strip()] = value.strip()
        result[source_type.strip().lower()] = normalized_values
    return result


def resolve_source_name(*, source_type: str, source_value: str, fallback: str) -> str:
    mappings = _load_mappings()
    key = source_type.strip().lower()
    value = source_value.strip()
    if key and value:
        resolved = mappings.get(key, {}).get(value)
        if resolved:
            return resolved
    fallback_value = fallback.strip()
    return fallback_value or value or "Unknown"
