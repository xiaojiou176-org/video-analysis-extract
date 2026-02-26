#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any
from urllib import error, parse, request

DEFAULT_IMPORT_FEED_URL = "https://miniflux.app/feed.xml"
DEFAULT_SYNC_LIMIT = 20


def env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing env: {name}")
    return value


def build_headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json", "Accept": "application/json", "User-Agent": "video-digestor/1.0"}
    token = os.getenv("MINIFLUX_API_TOKEN", "").strip()
    if token:
        headers["X-Auth-Token"] = token
        return headers

    user = os.getenv("MINIFLUX_ADMIN_USERNAME", "admin").strip()
    password = os.getenv("MINIFLUX_ADMIN_PASSWORD", "").strip()
    if not password:
        raise RuntimeError("MINIFLUX_API_TOKEN missing and MINIFLUX_ADMIN_PASSWORD empty")
    basic = base64.b64encode(f"{user}:{password}".encode("utf-8")).decode("ascii")
    headers["Authorization"] = f"Basic {basic}"
    return headers


def http_json(method: str, url: str, headers: dict[str, str], payload: dict[str, Any] | None = None) -> Any:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = request.Request(url=url, data=data, method=method, headers=headers)
    try:
        with request.urlopen(req, timeout=20) as resp:  # nosec B310
            body = resp.read().decode("utf-8")
            if not body:
                return None
            return json.loads(body)
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code} {method} {url}: {body[:500]}") from exc


def ensure_category_and_feed(base: str, headers: dict[str, str]) -> int:
    seed_feed_url = DEFAULT_IMPORT_FEED_URL
    categories = http_json("GET", f"{base}/v1/categories", headers) or []
    category_id = None
    for c in categories:
        if str(c.get("title", "")).strip().lower() == "video digestor":
            category_id = int(c["id"])
            break
    if category_id is None:
        created = http_json("POST", f"{base}/v1/categories", headers, {"title": "Video Digestor"}) or {}
        category_id = int(created.get("id"))

    feeds = http_json("GET", f"{base}/v1/feeds", headers) or []
    for f in feeds:
        if str(f.get("feed_url", "")).strip() == seed_feed_url:
            return int(f["id"])

    created_feed = http_json(
        "POST",
        f"{base}/v1/feeds",
        headers,
        {
            "feed_url": seed_feed_url,
            "category_id": category_id,
            "crawler": True,
            "disabled": False,
        },
    ) or {}
    feed_id = created_feed.get("feed_id", created_feed.get("id"))
    if feed_id is not None:
        return int(feed_id)

    # Compatibility fallback for Miniflux responses that omit id fields.
    feeds = http_json("GET", f"{base}/v1/feeds", headers) or []
    for f in feeds:
        if str(f.get("feed_url", "")).strip() == seed_feed_url:
            return int(f["id"])
    raise RuntimeError("failed to resolve feed id after feed creation")


def get_feed_items(api_base: str, limit: int) -> list[dict[str, Any]]:
    query = parse.urlencode({"limit": limit})
    with request.urlopen(f"{api_base}/api/v1/feed/digests?{query}", timeout=20) as resp:  # nosec B310
        payload = json.loads(resp.read().decode("utf-8"))
    return list(payload.get("items", []))


def to_unix(ts: str) -> int:
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        dt = datetime.now(timezone.utc)
    return int(dt.timestamp())


def import_entries(base: str, headers: dict[str, str], feed_id: int, items: list[dict[str, Any]]) -> int:
    imported = 0
    for item in items:
        job_id = str(item.get("job_id") or "").strip()
        title = str(item.get("title") or "").strip() or f"AI Digest {job_id or int(time.time())}"
        summary = str(item.get("summary_md") or "").strip()
        url = str(item.get("video_url") or "").strip() or f"https://local.video-digestor/jobs/{job_id}"
        if not summary:
            continue
        payload = {
            "title": title,
            "url": url,
            "content": summary,
            "author": "Video Digestor",
            "status": "unread",
            "external_id": f"video-digestor:{job_id}",
            "published_at": to_unix(str(item.get("published_at") or "")),
        }
        http_json("POST", f"{base}/v1/feeds/{feed_id}/entries/import", headers, payload)
        imported += 1
    return imported


def main() -> int:
    miniflux_base = env("MINIFLUX_BASE_URL", "http://127.0.0.1:8080").rstrip("/")
    api_base = env("VD_API_BASE_URL", f"http://127.0.0.1:{os.getenv('API_PORT', '8000')}").rstrip("/")
    limit = DEFAULT_SYNC_LIMIT

    headers = build_headers()
    feed_id = ensure_category_and_feed(miniflux_base, headers)
    items = get_feed_items(api_base, limit)
    imported = import_entries(miniflux_base, headers, feed_id, items)

    print(json.dumps({"ok": True, "feed_id": feed_id, "imported": imported, "items_seen": len(items)}))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}), file=sys.stderr)
        raise
