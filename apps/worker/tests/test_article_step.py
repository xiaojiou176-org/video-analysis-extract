"""Tests for article pipeline step_fetch_article_content."""

from __future__ import annotations

import asyncio
import builtins
import sys
from types import ModuleType, SimpleNamespace
from typing import Any, Self
from unittest.mock import AsyncMock, patch

import worker.pipeline.steps.article as article_step
from worker.pipeline.steps.article import step_fetch_article_content


class _FakeResponse:
    def __init__(self, text: str, *, raise_error: Exception | None = None) -> None:
        self.text = text
        self._raise_error = raise_error

    def raise_for_status(self) -> None:
        if self._raise_error is not None:
            raise self._raise_error


class _FakeAsyncClient:
    def __init__(self, response: _FakeResponse, *, get_error: Exception | None = None) -> None:
        self._response = response
        self._get_error = get_error

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False

    async def get(self, _url: str) -> _FakeResponse:
        if self._get_error is not None:
            raise self._get_error
        return self._response


def _patch_async_client(
    monkeypatch,
    *,
    response_text: str = "<html></html>",
    get_error: Exception | None = None,
    raise_error: Exception | None = None,
) -> None:
    def _factory(*_args: Any, **_kwargs: Any) -> _FakeAsyncClient:
        return _FakeAsyncClient(
            response=_FakeResponse(response_text, raise_error=raise_error),
            get_error=get_error,
        )

    monkeypatch.setattr(article_step.httpx, "AsyncClient", _factory)


def _install_trafilatura(monkeypatch, *, extracted: str | None) -> None:
    module = ModuleType("trafilatura")
    module.extract = lambda *_args, **_kwargs: extracted
    monkeypatch.setitem(sys.modules, "trafilatura", module)


def test_step_fetch_article_content_fails_when_source_url_missing() -> None:
    async def _run() -> Any:
        return await step_fetch_article_content(
            SimpleNamespace(),
            {},
            run_command=lambda _ctx, _cmd: asyncio.sleep(0),
        )

    execution = asyncio.run(_run())
    assert execution.status == "failed"
    assert execution.reason == "source_url_missing"
    assert execution.state_updates.get("transcript") == ""
    assert execution.state_updates.get("frames") == []
    assert execution.state_updates.get("comments") == []


def test_step_fetch_article_content_fails_when_http_fails_without_rss_fallback(monkeypatch) -> None:
    state = {
        "source_url": "https://example.com/article/2",
        "title": "",
        "overrides": {},
    }
    _patch_async_client(monkeypatch, get_error=Exception("Connection refused"))

    async def _run() -> Any:
        return await step_fetch_article_content(
            SimpleNamespace(),
            state,
            run_command=lambda _ctx, _cmd: asyncio.sleep(0),
        )

    execution = asyncio.run(_run())
    assert execution.status == "succeeded"
    assert execution.degraded is True
    assert execution.reason == "http_fetch_failed_rss_fallback"
    assert "Source: https://example.com/article/2" in execution.state_updates.get("transcript", "")


def test_step_fetch_article_content_uses_rss_fallback_when_http_fails() -> None:
    state = {
        "source_url": "https://example.com/article/1",
        "title": "Test Article",
        "platform": "rss",
        "video_uid": "hash123",
        "overrides": {"rss_content": "Full article body from RSS.", "rss_summary": "Short summary"},
    }

    async def _run() -> Any:
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=AsyncMock(
                    get=AsyncMock(side_effect=Exception("Connection refused")),
                )
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            return await step_fetch_article_content(
                SimpleNamespace(),
                state,
                run_command=lambda _ctx, _cmd: asyncio.sleep(0),
            )

    execution = asyncio.run(_run())
    assert execution.status == "succeeded"
    assert execution.degraded is True
    assert "Full article body from RSS" in (execution.state_updates.get("transcript") or "")
    assert execution.state_updates.get("frames") == []
    assert execution.state_updates.get("comments") == []


def test_step_fetch_article_content_uses_trafilatura_when_available(monkeypatch) -> None:
    state = {"source_url": "https://example.com/article/3", "title": "Article"}
    _patch_async_client(monkeypatch, response_text="<article>Hello</article>")
    _install_trafilatura(monkeypatch, extracted="  extracted body  ")

    async def _run() -> Any:
        return await step_fetch_article_content(
            SimpleNamespace(),
            state,
            run_command=lambda _ctx, _cmd: asyncio.sleep(0),
        )

    execution = asyncio.run(_run())
    assert execution.status == "succeeded"
    assert execution.output == {"provider": "trafilatura"}
    assert execution.state_updates.get("transcript") == "extracted body"


def test_step_fetch_article_content_uses_rss_fallback_when_trafilatura_empty(monkeypatch) -> None:
    state = {
        "source_url": "https://example.com/article/4",
        "title": "Fallback article",
        "overrides": {"rss_summary": "rss summary"},
    }
    _patch_async_client(monkeypatch, response_text="<article>empty</article>")
    _install_trafilatura(monkeypatch, extracted=" ")

    async def _run() -> Any:
        return await step_fetch_article_content(
            SimpleNamespace(),
            state,
            run_command=lambda _ctx, _cmd: asyncio.sleep(0),
        )

    execution = asyncio.run(_run())
    assert execution.status == "succeeded"
    assert execution.degraded is True
    assert execution.reason == "trafilatura_empty_rss_fallback"
    assert "rss summary" in (execution.state_updates.get("transcript") or "")


def test_step_fetch_article_content_fails_when_trafilatura_empty_and_no_rss(monkeypatch) -> None:
    state = {"source_url": "https://example.com/article/5", "title": ""}
    _patch_async_client(monkeypatch, response_text="<article>empty</article>")
    _install_trafilatura(monkeypatch, extracted="")

    async def _run() -> Any:
        return await step_fetch_article_content(
            SimpleNamespace(),
            state,
            run_command=lambda _ctx, _cmd: asyncio.sleep(0),
        )

    execution = asyncio.run(_run())
    assert execution.status == "succeeded"
    assert execution.degraded is True
    assert execution.reason == "trafilatura_empty_rss_fallback"


def test_step_fetch_article_content_handles_missing_trafilatura(monkeypatch) -> None:
    state = {
        "source_url": "https://example.com/article/6",
        "title": "Import fallback",
        "overrides": {"rss_content": "rss content"},
    }
    _patch_async_client(monkeypatch, response_text="<article>hello</article>")
    monkeypatch.delitem(sys.modules, "trafilatura", raising=False)

    real_import = builtins.__import__

    def _fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "trafilatura":
            raise ImportError("missing dependency")
        return real_import(name, *args, **kwargs)

    async def _run() -> Any:
        with patch("builtins.__import__", side_effect=_fake_import):
            return await step_fetch_article_content(
                SimpleNamespace(),
                state,
                run_command=lambda _ctx, _cmd: asyncio.sleep(0),
            )

    execution = asyncio.run(_run())
    assert execution.status == "succeeded"
    assert execution.degraded is True
    assert execution.reason == "trafilatura_unavailable_rss_fallback"
    assert "rss content" in (execution.state_updates.get("transcript") or "")


def test_step_fetch_article_content_fails_when_trafilatura_missing_and_no_rss(monkeypatch) -> None:
    state = {"source_url": "https://example.com/article/7", "title": ""}
    _patch_async_client(monkeypatch, response_text="<article>hello</article>")
    monkeypatch.delitem(sys.modules, "trafilatura", raising=False)

    real_import = builtins.__import__

    def _fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "trafilatura":
            raise ImportError("missing dependency")
        return real_import(name, *args, **kwargs)

    async def _run() -> Any:
        with patch("builtins.__import__", side_effect=_fake_import):
            return await step_fetch_article_content(
                SimpleNamespace(),
                state,
                run_command=lambda _ctx, _cmd: asyncio.sleep(0),
            )

    execution = asyncio.run(_run())
    assert execution.status == "succeeded"
    assert execution.degraded is True
    assert execution.reason == "trafilatura_unavailable_rss_fallback"


def test_step_fetch_article_content_succeeds_with_trafilatura_extract() -> None:
    state = {
        "source_url": "https://example.com/article/2",
        "title": "Extracted Article",
        "platform": "rss",
        "video_uid": "hash456",
    }

    async def _run() -> Any:
        fake_response = SimpleNamespace(
            raise_for_status=lambda: None,
            text="<html><body>article</body></html>",
        )
        with patch("httpx.AsyncClient") as mock_client, patch(
            "trafilatura.extract", return_value="Extracted full text"
        ):
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=AsyncMock(
                    get=AsyncMock(return_value=fake_response),
                )
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            return await step_fetch_article_content(
                SimpleNamespace(),
                state,
                run_command=lambda _ctx, _cmd: asyncio.sleep(0),
            )

    execution = asyncio.run(_run())
    assert execution.status == "succeeded"
    assert execution.degraded is False
    assert execution.output == {"provider": "trafilatura"}
    assert execution.state_updates["transcript"] == "Extracted full text"


def test_step_fetch_article_content_fails_when_trafilatura_empty_and_no_rss_fallback() -> None:
    state = {
        "source_url": "https://example.com/article/3",
        "title": "No Fallback",
        "platform": "rss",
        "video_uid": "hash789",
    }

    async def _run() -> Any:
        fake_response = SimpleNamespace(
            raise_for_status=lambda: None,
            text="<html><body>empty</body></html>",
        )
        with patch("httpx.AsyncClient") as mock_client, patch("trafilatura.extract", return_value=""):
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=AsyncMock(
                    get=AsyncMock(return_value=fake_response),
                )
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            return await step_fetch_article_content(
                SimpleNamespace(),
                state,
                run_command=lambda _ctx, _cmd: asyncio.sleep(0),
            )

    execution = asyncio.run(_run())
    assert execution.status == "succeeded"
    assert execution.degraded is True
    assert execution.reason == "trafilatura_empty_rss_fallback"
    assert "# No Fallback" in execution.state_updates["transcript"]


def test_step_fetch_article_content_uses_rss_fallback_when_trafilatura_missing() -> None:
    state = {
        "source_url": "https://example.com/article/4",
        "title": "Import Error",
        "platform": "rss",
        "video_uid": "hash000",
        "published_at": "2026-03-08T00:00:00Z",
        "overrides": {"rss_summary": "summary body"},
    }

    async def _run() -> Any:
        original_import = __import__
        fake_response = SimpleNamespace(
            raise_for_status=lambda: None,
            text="<html><body>content</body></html>",
        )
        with patch("httpx.AsyncClient") as mock_client, patch(
            "builtins.__import__",
            side_effect=lambda name, *args, **kwargs: (_ for _ in ()).throw(ImportError(name))
            if name == "trafilatura"
            else original_import(name, *args, **kwargs),
        ):
            mock_client.return_value.__aenter__ = AsyncMock(
                return_value=AsyncMock(
                    get=AsyncMock(return_value=fake_response),
                )
            )
            mock_client.return_value.__aexit__ = AsyncMock(return_value=None)
            return await step_fetch_article_content(
                SimpleNamespace(),
                state,
                run_command=lambda _ctx, _cmd: asyncio.sleep(0),
            )

    execution = asyncio.run(_run())
    assert execution.status == "succeeded"
    assert execution.degraded is True
    assert execution.reason == "trafilatura_unavailable_rss_fallback"
    assert "summary body" in execution.state_updates["transcript"]
