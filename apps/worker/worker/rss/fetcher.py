from __future__ import annotations

import asyncio
from typing import Any, Iterable
from xml.etree import ElementTree

import httpx


def _local_name(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _find_text(node: ElementTree.Element, names: set[str]) -> str | None:
    for child in node:
        if _local_name(child.tag) in names and child.text:
            text = child.text.strip()
            if text:
                return text
    return None


def _extract_link(node: ElementTree.Element) -> str | None:
    for child in node:
        if _local_name(child.tag) != "link":
            continue

        href = (child.attrib.get("href") or "").strip()
        if href:
            return href

        if child.text and child.text.strip():
            return child.text.strip()
    return None


def parse_feed(xml_content: str) -> list[dict[str, Any]]:
    root = ElementTree.fromstring(xml_content)
    root_name = _local_name(root.tag)

    if root_name == "rss":
        channel = next((c for c in root if _local_name(c.tag) == "channel"), None)
        items = [c for c in (channel or []) if _local_name(c.tag) == "item"]
    elif root_name == "feed":
        items = [c for c in root if _local_name(c.tag) == "entry"]
    else:
        items = []

    entries: list[dict[str, Any]] = []
    for item in items:
        entries.append(
            {
                "title": _find_text(item, {"title"}),
                "link": _extract_link(item),
                "guid": _find_text(item, {"guid", "id"}),
                "published_at": _find_text(item, {"pubDate", "published", "updated"}),
                "summary": _find_text(item, {"description", "summary"}),
                "content": _find_text(item, {"content", "encoded"}),
            }
        )
    return entries


class RSSHubFetcher:
    def __init__(
        self,
        timeout_seconds: float = 20.0,
        retry_attempts: int = 2,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._retry_attempts = max(0, retry_attempts)
        self._retry_backoff_seconds = max(0.0, retry_backoff_seconds)

    async def _fetch_one(
        self,
        client: httpx.AsyncClient,
        feed_url: str,
    ) -> list[dict[str, Any]]:
        last_error: Exception | None = None
        for attempt in range(self._retry_attempts + 1):
            try:
                response = await client.get(feed_url, follow_redirects=True)
                if response.status_code >= 500:
                    response.raise_for_status()
                if response.status_code >= 400:
                    response.raise_for_status()
                return parse_feed(response.text)
            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code
                if status_code < 500:
                    raise
            except (httpx.RequestError, ElementTree.ParseError) as exc:
                last_error = exc

            if attempt >= self._retry_attempts:
                break
            await asyncio.sleep(self._retry_backoff_seconds * (2**attempt))

        if last_error is not None:
            raise last_error
        return []

    async def fetch_many(self, feed_urls: Iterable[str]) -> dict[str, list[dict[str, Any]]]:
        urls = list(feed_urls)
        if not urls:
            return {}

        timeout = httpx.Timeout(self._timeout_seconds)
        async with httpx.AsyncClient(timeout=timeout) as client:
            tasks = [self._fetch_one(client, url) for url in urls]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        by_feed: dict[str, list[dict[str, Any]]] = {}
        for feed_url, result in zip(urls, results):
            if isinstance(result, Exception):
                by_feed[feed_url] = []
                continue
            by_feed[feed_url] = result
        return by_feed
