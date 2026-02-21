from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

BILIBILI_API_BASE = "https://api.bilibili.com"
BILIBILI_VIDEO_TYPE = 1
BILIBILI_HOSTS = {"bilibili.com", "www.bilibili.com", "m.bilibili.com", "b23.tv"}
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    )
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def empty_comments_payload(*, sort: str = "like") -> dict[str, Any]:
    return {
        "sort": sort,
        "top_comments": [],
        "replies": {},
        "fetched_at": _utc_now_iso(),
    }


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _ts_to_iso(ts: Any) -> str | None:
    ts_int = _to_int(ts, default=-1)
    if ts_int < 0:
        return None
    return datetime.fromtimestamp(ts_int, tz=timezone.utc).replace(microsecond=0).isoformat()


def _extract_bvid(text: str) -> str | None:
    match = re.search(r"(BV[0-9A-Za-z]+)", text)
    if not match:
        return None
    return match.group(1)


class BilibiliCommentCollector:
    def __init__(
        self,
        *,
        top_n: int = 10,
        replies_per_comment: int = 10,
        request_timeout_seconds: float = 10.0,
        retry_attempts: int = 2,
        retry_backoff_seconds: float = 0.5,
        min_request_interval_seconds: float = 0.2,
    ) -> None:
        self._top_n = max(1, int(top_n))
        self._replies_per_comment = max(1, int(replies_per_comment))
        self._request_timeout_seconds = max(1.0, float(request_timeout_seconds))
        self._retry_attempts = max(0, int(retry_attempts))
        self._retry_backoff_seconds = max(0.0, float(retry_backoff_seconds))
        self._min_request_interval_seconds = max(0.0, float(min_request_interval_seconds))
        self._lock = asyncio.Lock()
        self._last_request_at = 0.0

    async def collect(
        self,
        *,
        source_url: str | None,
        video_uid: str | None,
    ) -> dict[str, Any]:
        timeout = httpx.Timeout(self._request_timeout_seconds)
        async with httpx.AsyncClient(
            base_url=BILIBILI_API_BASE,
            timeout=timeout,
            headers=DEFAULT_HEADERS,
            follow_redirects=True,
        ) as client:
            aid = await self._resolve_aid(client=client, source_url=source_url, video_uid=video_uid)
            if aid <= 0:
                raise ValueError("bilibili_aid_not_resolved")

            top_comments = await self._fetch_top_comments(client=client, aid=aid)
            replies_index: dict[str, list[dict[str, Any]]] = {}
            for item in top_comments:
                root_id = _to_int(item.get("comment_id"), default=0)
                replies = await self._fetch_replies(client=client, aid=aid, root_id=root_id)
                item["replies"] = replies
                replies_index[str(item.get("comment_id") or "")] = replies

        return {
            "sort": "like",
            "top_comments": top_comments,
            "replies": replies_index,
            "fetched_at": _utc_now_iso(),
        }

    async def _throttle(self) -> None:
        if self._min_request_interval_seconds <= 0:
            return
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            elapsed = now - self._last_request_at
            if elapsed < self._min_request_interval_seconds:
                await asyncio.sleep(self._min_request_interval_seconds - elapsed)
                now = loop.time()
            self._last_request_at = now

    async def _request_json(
        self,
        client: httpx.AsyncClient,
        path: str,
        *,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self._retry_attempts + 1):
            await self._throttle()
            try:
                response = await client.get(path, params=params)
                if response.status_code in {412, 429}:
                    raise httpx.HTTPStatusError(
                        f"rate_limited:{response.status_code}",
                        request=response.request,
                        response=response,
                    )
                if response.status_code >= 500:
                    response.raise_for_status()
                if response.status_code >= 400:
                    response.raise_for_status()
                payload = response.json()
                code = _to_int(payload.get("code"), default=0)
                if code != 0:
                    raise ValueError(
                        f"bilibili_api_error:{code}:{str(payload.get('message') or payload.get('msg') or '').strip()}"
                    )
                data = payload.get("data")
                if isinstance(data, dict):
                    return data
                return {}
            except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError, ValueError) as exc:
                last_error = exc
                if attempt >= self._retry_attempts:
                    break
                await asyncio.sleep(self._retry_backoff_seconds * float(2**attempt))

        if last_error is not None:
            raise last_error
        raise RuntimeError("bilibili_request_failed")

    def _extract_aid_from_url(self, source_url: str | None) -> int | None:
        if not source_url:
            return None
        parsed = urlparse(source_url)
        host = parsed.netloc.lower()
        if host not in BILIBILI_HOSTS:
            return None

        aid_match = re.search(r"/video/av(\d+)", parsed.path)
        if aid_match:
            return _to_int(aid_match.group(1), default=0) or None

        query = parse_qs(parsed.query)
        aid_values = query.get("aid") or []
        if aid_values:
            aid = _to_int(aid_values[0], default=0)
            if aid > 0:
                return aid
        return None

    async def _resolve_aid(
        self,
        *,
        client: httpx.AsyncClient,
        source_url: str | None,
        video_uid: str | None,
    ) -> int:
        uid = str(video_uid or "").strip()
        if uid.isdigit():
            return int(uid)
        if uid.lower().startswith("av") and uid[2:].isdigit():
            return int(uid[2:])

        aid_from_url = self._extract_aid_from_url(source_url)
        if aid_from_url:
            return aid_from_url

        bvid = _extract_bvid(uid) if uid else None
        if not bvid and source_url:
            bvid = _extract_bvid(source_url)
        if not bvid:
            return 0

        data = await self._request_json(client, "/x/web-interface/view", params={"bvid": bvid})
        return _to_int(data.get("aid"), default=0)

    def _normalize_comment(self, item: dict[str, Any]) -> dict[str, Any]:
        member = item.get("member") or {}
        content = item.get("content") or {}
        return {
            "comment_id": str(item.get("rpid") or ""),
            "author": str(member.get("uname") or "unknown"),
            "author_mid": str(member.get("mid") or ""),
            "content": str(content.get("message") or "").strip(),
            "like_count": _to_int(item.get("like"), default=0),
            "published_at": _ts_to_iso(item.get("ctime")),
            "replies": [],
        }

    async def _fetch_top_comments(self, *, client: httpx.AsyncClient, aid: int) -> list[dict[str, Any]]:
        data = await self._request_json(
            client,
            "/x/v2/reply/main",
            params={
                "type": BILIBILI_VIDEO_TYPE,
                "oid": aid,
                "mode": 3,
                "next": 0,
                "ps": self._top_n,
            },
        )
        comments = data.get("replies") or []
        if not isinstance(comments, list):
            return []

        normalized = [
            self._normalize_comment(item)
            for item in comments
            if isinstance(item, dict)
        ]
        normalized.sort(key=lambda item: _to_int(item.get("like_count"), default=0), reverse=True)
        return normalized[: self._top_n]

    async def _fetch_replies(
        self,
        *,
        client: httpx.AsyncClient,
        aid: int,
        root_id: int,
    ) -> list[dict[str, Any]]:
        if root_id <= 0:
            return []
        data = await self._request_json(
            client,
            "/x/v2/reply/reply",
            params={
                "type": BILIBILI_VIDEO_TYPE,
                "oid": aid,
                "root": root_id,
                "pn": 1,
                "ps": self._replies_per_comment,
            },
        )
        replies = data.get("replies") or []
        if not isinstance(replies, list):
            return []

        normalized: list[dict[str, Any]] = []
        for reply in replies:
            if not isinstance(reply, dict):
                continue
            item = self._normalize_comment(reply)
            item["replies"] = []
            normalized.append(item)
        normalized.sort(key=lambda item: _to_int(item.get("like_count"), default=0), reverse=True)
        return normalized[: self._replies_per_comment]
