from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _ts_to_iso(raw: Any) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        return text.replace("Z", "+00:00")
    return text


def _extract_video_id(source_url: str | None, video_uid: str | None) -> str:
    uid = str(video_uid or "").strip()
    if uid:
        return uid

    url = str(source_url or "").strip()
    if not url:
        return ""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host not in YOUTUBE_HOSTS:
        return ""

    if host == "youtu.be":
        return parsed.path.strip("/").split("/")[0]

    query = parse_qs(parsed.query)
    values = query.get("v") or []
    if values:
        return str(values[0]).strip()

    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2 and parts[0] == "shorts":
        return parts[1]
    return ""


class YouTubeCommentCollector:
    def __init__(
        self,
        *,
        api_key: str,
        top_n: int = 10,
        replies_per_comment: int = 10,
        request_timeout_seconds: float = 10.0,
        retry_attempts: int = 2,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        self._api_key = str(api_key or "").strip()
        self._top_n = max(1, int(top_n))
        self._replies_per_comment = max(0, int(replies_per_comment))
        self._request_timeout_seconds = max(1.0, float(request_timeout_seconds))
        self._retry_attempts = max(0, int(retry_attempts))
        self._retry_backoff_seconds = max(0.0, float(retry_backoff_seconds))

    async def _request_json(
        self,
        client: httpx.AsyncClient,
        path: str,
        *,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        last_error: Exception | None = None
        for attempt in range(self._retry_attempts + 1):
            try:
                response = await client.get(path, params=params)
                if response.status_code >= 400:
                    response.raise_for_status()
                payload = response.json()
                if isinstance(payload, dict):
                    return payload
                return {}
            except (httpx.TimeoutException, httpx.RequestError, httpx.HTTPStatusError) as exc:
                last_error = exc
                if attempt >= self._retry_attempts:
                    break
                await asyncio.sleep(self._retry_backoff_seconds * float(2**attempt))
        if last_error is not None:
            raise last_error
        raise RuntimeError("youtube_request_failed")

    def _normalize_top_comment(self, item: dict[str, Any]) -> dict[str, Any]:
        snippet = item.get("snippet") or {}
        top = (snippet.get("topLevelComment") or {}).get("snippet") or {}
        comment_id = str(
            (snippet.get("topLevelComment") or {}).get("id")
            or item.get("id")
            or ""
        ).strip()
        reply_count = _to_int(snippet.get("totalReplyCount"), default=0)
        return {
            "comment_id": comment_id or f"youtube_comment_{abs(hash(str(item)))}",
            "author": str(top.get("authorDisplayName") or "unknown"),
            "content": str(top.get("textDisplay") or top.get("textOriginal") or "").strip(),
            "like_count": _to_int(top.get("likeCount"), default=0),
            "reply_count": max(0, reply_count),
            "published_at": _ts_to_iso(top.get("publishedAt")),
            "replies": [],
        }

    def _normalize_reply(self, item: dict[str, Any]) -> dict[str, Any]:
        snippet = item.get("snippet") or {}
        reply_id = str(item.get("id") or "").strip()
        return {
            "reply_id": reply_id or f"youtube_reply_{abs(hash(str(item)))}",
            "author": str(snippet.get("authorDisplayName") or "unknown"),
            "content": str(snippet.get("textDisplay") or snippet.get("textOriginal") or "").strip(),
            "like_count": _to_int(snippet.get("likeCount"), default=0),
            "published_at": _ts_to_iso(snippet.get("publishedAt")),
        }

    async def _collect_replies_by_parent_id(
        self,
        client: httpx.AsyncClient,
        *,
        parent_id: str,
        remaining_limit: int,
        existing_reply_ids: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        if remaining_limit <= 0:
            return []
        seen_reply_ids = set(existing_reply_ids or set())
        replies: list[dict[str, Any]] = []
        page_token: str | None = None

        while len(replies) < remaining_limit:
            params: dict[str, Any] = {
                "part": "snippet",
                "parentId": parent_id,
                "key": self._api_key,
                "textFormat": "plainText",
                "maxResults": min(100, max(1, remaining_limit - len(replies))),
            }
            if page_token:
                params["pageToken"] = page_token

            payload = await self._request_json(client, "/comments", params=params)
            items = payload.get("items")
            if not isinstance(items, list) or not items:
                break

            for raw in items:
                if not isinstance(raw, dict):
                    continue
                reply = self._normalize_reply(raw)
                reply_id = str(reply.get("reply_id") or "").strip()
                if reply_id and reply_id in seen_reply_ids:
                    continue
                if reply_id:
                    seen_reply_ids.add(reply_id)
                replies.append(reply)
                if len(replies) >= remaining_limit:
                    break

            page_token = str(payload.get("nextPageToken") or "").strip() or None
            if not page_token:
                break
        return replies

    async def collect(
        self,
        *,
        source_url: str | None,
        video_uid: str | None,
    ) -> dict[str, Any]:
        if not self._api_key:
            raise ValueError("youtube_api_key_missing")

        video_id = _extract_video_id(source_url, video_uid)
        if not video_id:
            raise ValueError("youtube_video_id_not_resolved")

        timeout = httpx.Timeout(self._request_timeout_seconds)
        top_comments: list[dict[str, Any]] = []
        replies_index: dict[str, list[dict[str, Any]]] = {}
        page_token: str | None = None
        page_size = min(100, self._top_n)

        async with httpx.AsyncClient(base_url=YOUTUBE_API_BASE, timeout=timeout) as client:
            while len(top_comments) < self._top_n:
                params: dict[str, Any] = {
                    "part": "snippet,replies",
                    "videoId": video_id,
                    "key": self._api_key,
                    "order": "relevance",
                    "textFormat": "plainText",
                    "maxResults": page_size,
                }
                if page_token:
                    params["pageToken"] = page_token
                payload = await self._request_json(client, "/commentThreads", params=params)
                items = payload.get("items")
                if not isinstance(items, list) or not items:
                    break

                for item in items:
                    if not isinstance(item, dict):
                        continue
                    top_comment = self._normalize_top_comment(item)
                    replies_raw = ((item.get("replies") or {}).get("comments") or [])
                    replies: list[dict[str, Any]] = []
                    reply_id_set: set[str] = set()
                    if isinstance(replies_raw, list) and self._replies_per_comment > 0:
                        for raw in replies_raw[: self._replies_per_comment]:
                            if not isinstance(raw, dict):
                                continue
                            reply = self._normalize_reply(raw)
                            reply_id = str(reply.get("reply_id") or "").strip()
                            if reply_id:
                                reply_id_set.add(reply_id)
                            replies.append(reply)

                    reply_count = _to_int(top_comment.get("reply_count"), default=0)
                    target_reply_count = min(self._replies_per_comment, max(0, reply_count))
                    parent_id = str(top_comment.get("comment_id") or "").strip()
                    if (
                        self._replies_per_comment > 0
                        and parent_id
                        and target_reply_count > len(replies)
                    ):
                        fetched_replies = await self._collect_replies_by_parent_id(
                            client,
                            parent_id=parent_id,
                            remaining_limit=target_reply_count - len(replies),
                            existing_reply_ids=reply_id_set,
                        )
                        replies.extend(fetched_replies)

                    top_comment["replies"] = replies
                    top_comments.append(top_comment)
                    replies_index[str(top_comment.get("comment_id") or "")] = replies
                    if len(top_comments) >= self._top_n:
                        break

                page_token = str(payload.get("nextPageToken") or "").strip() or None
                if not page_token:
                    break

        top_comments.sort(key=lambda item: _to_int(item.get("like_count"), 0), reverse=True)
        top_comments = top_comments[: self._top_n]

        return {
            "sort": "hot",
            "top_n": self._top_n,
            "replies_per_comment": self._replies_per_comment,
            "top_comments": top_comments,
            "replies": replies_index,
            "fetched_at": _utc_now_iso(),
        }
