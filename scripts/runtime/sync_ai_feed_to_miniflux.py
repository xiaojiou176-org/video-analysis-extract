#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from integrations.reader import miniflux as miniflux_integration

DEFAULT_IMPORT_FEED_URL = miniflux_integration.DEFAULT_IMPORT_FEED_URL
DEFAULT_SYNC_LIMIT = miniflux_integration.DEFAULT_SYNC_LIMIT
env = lambda name, default=None: miniflux_integration.env(name, os.getenv, default)  # noqa: E731
build_headers = lambda: miniflux_integration.build_headers(environ_get=os.getenv)  # noqa: E731
http_json = miniflux_integration.http_json
is_duplicate_entry_error = miniflux_integration.is_duplicate_entry_error
def ensure_category_and_feed(base: str, headers: dict[str, str]) -> int:
    return miniflux_integration.ensure_category_and_feed_with_http_json(
        base,
        headers,
        http_json_fn=http_json,
    )

get_feed_items = miniflux_integration.get_feed_items
to_unix = miniflux_integration.to_unix


def import_entries(
    base: str,
    headers: dict[str, str],
    feed_id: int,
    items: list[dict[str, object]],
) -> int:
    return miniflux_integration.import_entries_with_http_json(
        base,
        headers,
        feed_id,
        items,
        http_json_fn=http_json,
    )


def main() -> int:
    miniflux_base = env("MINIFLUX_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
    api_base = env("VD_API_BASE_URL", "http://127.0.0.1:9000").rstrip("/")
    limit = DEFAULT_SYNC_LIMIT

    headers = build_headers()
    feed_id = ensure_category_and_feed(miniflux_base, headers)
    items = get_feed_items(api_base, limit)
    imported = import_entries(miniflux_base, headers, feed_id, items)

    print(
        json.dumps({"ok": True, "feed_id": feed_id, "imported": imported, "items_seen": len(items)})
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        raise
