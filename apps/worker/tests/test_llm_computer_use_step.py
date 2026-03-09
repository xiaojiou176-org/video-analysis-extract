from __future__ import annotations

import sys
import types
from typing import Any

from worker.pipeline.steps import llm_computer_use

sys.modules["apps.worker.worker.pipeline.steps.llm_computer_use"] = llm_computer_use


def test_coerce_dict_returns_copy_for_dict_and_empty_for_non_dict() -> None:
    source = {"k": "v"}
    copied = llm_computer_use._coerce_dict(source)
    copied["k"] = "changed"

    assert source == {"k": "v"}
    assert llm_computer_use._coerce_dict(["not-a-dict"]) == {}


def test_resolve_computer_use_payload_prefers_section_then_llm_then_state() -> None:
    payload = llm_computer_use._resolve_computer_use_payload(
        state={
            "source_url": "https://state.example/video",
            "metadata": {"webpage_url": "https://meta.example/video"},
            "computer_use": {
                "executor": "browser_stub",
                "url": "https://state.example/override",
                "screenshot": "state-shot",
                "context": {"level": "state"},
            },
        },
        llm_policy={
            "computer_use_executor": "playwright",
            "computer_use_url": "https://llm.example/video",
            "computer_use": {
                "screenshot": "llm-shot",
                "context": {"level": "llm"},
            },
        },
        section_policy={
            "computer_use": {
                "executor": "no_op",
                "url": "https://section.example/video",
                "screenshot": "section-shot",
                "context": {"level": "section"},
            }
        },
    )

    assert payload == {
        "executor": "no_op",
        "url": "https://section.example/video",
        "screenshot": "section-shot",
        "context": {"level": "section"},
    }


def test_resolve_computer_use_payload_defaults_and_url_fallback_order() -> None:
    payload = llm_computer_use._resolve_computer_use_payload(
        state={"metadata": {"webpage_url": "https://meta.example/video"}},
        llm_policy={},
        section_policy={},
    )
    payload_with_source = llm_computer_use._resolve_computer_use_payload(
        state={
            "source_url": "https://source.example/video",
            "metadata": {"webpage_url": "https://meta.example/video"},
        },
        llm_policy={},
        section_policy={},
    )

    assert payload == {
        "executor": "playwright",
        "url": "https://meta.example/video",
        "screenshot": "",
        "context": {},
    }
    assert payload_with_source["url"] == "https://source.example/video"


def test_executor_name_normalizes_known_values_and_defaults_to_no_op() -> None:
    assert llm_computer_use._executor_name("playwright") == "playwright"
    assert llm_computer_use._executor_name("browser_playwright") == "playwright"
    assert llm_computer_use._executor_name("browser_stub") == "browser_stub"
    assert llm_computer_use._executor_name("browser") == "browser_stub"
    assert llm_computer_use._executor_name(" Browser ") == "browser_stub"
    assert llm_computer_use._executor_name("something-else") == "no_op"


def test_normalize_action_and_stub_handlers_cover_success_and_error() -> None:
    action_name, action_args = llm_computer_use._normalize_action(
        {
            "action": "",
            "type": " CLICK ",
            "selector": "#cta",
            "url": "https://example.com",
            "screenshot": "shot",
            "context": {"k": "v"},
        }
    )

    assert action_name == "click"
    assert action_args == {"selector": "#cta"}
    assert llm_computer_use._execute_noop("", {})["error"] == "computer_use_action_missing"
    assert llm_computer_use._execute_browser_stub("", {})["error"] == "computer_use_action_missing"
    assert llm_computer_use._execute_noop("tap", {"selector": "#cta"})["message"] == "computer_use_noop_executed"
    assert (
        llm_computer_use._execute_browser_stub("tap", {"selector": "#cta"})["message"]
        == "computer_use_browser_stub_executed"
    )


def test_build_default_handler_uses_browser_stub_and_target_payload() -> None:
    handler = llm_computer_use.build_default_computer_use_handler(
        state={
            "computer_use": {
                "executor": "browser_stub",
                "url": "https://state.example/video",
                "screenshot": "state-shot",
                "context": {"from": "state"},
            }
        },
        llm_policy={},
        section_policy={},
    )

    result = handler(action="click", selector="#cta")

    assert result["status"] == "ok"
    assert result["executor"] == "browser_stub"
    assert result["action"] == {"name": "click", "args": {"selector": "#cta"}}
    assert result["target"] == {
        "url": "https://state.example/video",
        "screenshot": "state-shot",
        "context": {"from": "state"},
    }


def test_build_default_handler_falls_back_when_playwright_execution_errors(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        llm_computer_use,
        "_execute_playwright",
        lambda **_: {"ok": False, "status": "error", "error": "playwright-boom"},
    )

    handler = llm_computer_use.build_default_computer_use_handler(
        state={"computer_use": {"executor": "playwright", "url": "https://example.com"}},
        llm_policy={},
        section_policy={},
    )

    result = handler(action="click", selector="#retry")

    assert result["status"] == "ok"
    assert result["executor"] == "playwright"
    assert result["fallback_from"] == "playwright"
    assert result["playwright_error"] == "playwright-boom"
    assert result["action"] == {"name": "click", "args": {"selector": "#retry"}}


def test_build_default_handler_wraps_non_dict_context_without_fallback_on_playwright_success(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        llm_computer_use,
        "_execute_playwright",
        lambda **kwargs: {
            "ok": True,
            "status": "ok",
            "action": {"name": kwargs["action_name"], "args": kwargs["action_args"]},
        },
    )
    handler = llm_computer_use.build_default_computer_use_handler(
        state={"computer_use": {"executor": "playwright", "url": "https://base.example/video"}},
        llm_policy={},
        section_policy={},
    )

    result = handler(type="fill", target="#search", input_text="demo", context="raw-context")

    assert result["status"] == "ok"
    assert result["executor"] == "playwright"
    assert "fallback_from" not in result
    assert result["action"] == {
        "name": "fill",
        "args": {"target": "#search", "input_text": "demo"},
    }
    assert result["target"]["url"] == "https://base.example/video"
    assert result["target"]["context"] == {"value": "raw-context"}


def test_build_default_handler_uses_noop_executor_for_unknown_executor_name() -> None:
    handler = llm_computer_use.build_default_computer_use_handler(
        state={"computer_use": {"executor": "unsupported"}},
        llm_policy={},
        section_policy={},
    )
    result = handler(name="click", selector="#cta")

    assert result["status"] == "ok"
    assert result["executor"] == "no_op"
    assert result["message"] == "computer_use_noop_executed"
    assert result["action"] == {"name": "click", "args": {"selector": "#cta"}}


def test_execute_playwright_covers_missing_action_and_url() -> None:
    missing_action = llm_computer_use._execute_playwright(
        action_name="",
        action_args={},
        url="https://example.com",
    )
    missing_url = llm_computer_use._execute_playwright(
        action_name="click",
        action_args={},
        url="",
    )

    assert missing_action == {
        "ok": False,
        "status": "error",
        "error": "computer_use_action_missing",
    }
    assert missing_url == {
        "ok": False,
        "status": "error",
        "error": "computer_use_target_url_missing",
    }


def test_execute_playwright_reports_import_failure_as_unavailable(monkeypatch: Any) -> None:
    monkeypatch.setitem(sys.modules, "playwright.sync_api", types.SimpleNamespace())
    result = llm_computer_use._execute_playwright(
        action_name="click",
        action_args={"selector": "#go"},
        url="https://example.com/start",
    )

    assert result["status"] == "error"
    assert str(result["error"]).startswith("computer_use_playwright_unavailable:")


def test_execute_playwright_click_and_navigate_paths(monkeypatch: Any) -> None:
    recorded: list[tuple[str, Any]] = []

    class FakePage:
        def __init__(self) -> None:
            self.url = "https://example.com/original"

        def goto(self, url: str, *, timeout: int, wait_until: str) -> None:
            recorded.append(("goto", url, timeout, wait_until))
            self.url = url

        def click(self, selector: str, *, timeout: int) -> None:
            recorded.append(("click", selector, timeout))

        def fill(self, selector: str, text: str, *, timeout: int) -> None:
            recorded.append(("fill", selector, text, timeout))

        def wait_for_timeout(self, wait_ms: int) -> None:
            recorded.append(("wait", wait_ms))

        def evaluate(self, script: str) -> None:
            recorded.append(("evaluate", script))

        def screenshot(self, *, type: str, full_page: bool) -> bytes:
            recorded.append(("screenshot", type, full_page))
            return b"png-bytes"

    class FakeBrowser:
        def __init__(self) -> None:
            self.page = FakePage()

        def new_page(self) -> FakePage:
            return self.page

        def close(self) -> None:
            recorded.append(("close",))

    class FakeChromium:
        def launch(self, *, headless: bool) -> FakeBrowser:
            recorded.append(("launch", headless))
            return FakeBrowser()

    class FakePlaywright:
        def __enter__(self) -> types.SimpleNamespace:
            return types.SimpleNamespace(chromium=FakeChromium())

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    def _sync_playwright() -> FakePlaywright:
        return FakePlaywright()

    monkeypatch.setitem(
        __import__("sys").modules,
        "playwright.sync_api",
        types.SimpleNamespace(sync_playwright=_sync_playwright),
    )

    click_result = llm_computer_use._execute_playwright(
        action_name="click",
        action_args={"selector": "#go"},
        url="https://example.com/start",
    )
    navigate_result = llm_computer_use._execute_playwright(
        action_name="navigate",
        action_args={"url": "https://example.com/next"},
        url="https://example.com/start",
    )

    assert click_result["status"] == "ok"
    assert click_result["current_url"] == "https://example.com/start"
    assert click_result["screenshot_base64"]
    assert navigate_result["status"] == "ok"
    assert navigate_result["current_url"] == "https://example.com/next"
    assert ("click", "#go", 8000) in recorded
    assert ("goto", "https://example.com/next", 8000, "domcontentloaded") in recorded


def test_execute_playwright_fill_wait_scroll_and_unknown_paths(monkeypatch: Any) -> None:
    recorded: list[tuple[str, Any]] = []

    class FakePage:
        def __init__(self) -> None:
            self.url = "https://example.com/original"

        def goto(self, url: str, *, timeout: int, wait_until: str) -> None:
            recorded.append(("goto", url, timeout, wait_until))
            self.url = url

        def click(self, selector: str, *, timeout: int) -> None:
            recorded.append(("click", selector, timeout))

        def fill(self, selector: str, text: str, *, timeout: int) -> None:
            recorded.append(("fill", selector, text, timeout))

        def wait_for_timeout(self, wait_ms: int) -> None:
            recorded.append(("wait", wait_ms))

        def evaluate(self, script: str) -> None:
            recorded.append(("evaluate", script))

        def screenshot(self, *, type: str, full_page: bool) -> bytes:
            recorded.append(("screenshot", type, full_page))
            return b"png-bytes"

    class FakeBrowser:
        def __init__(self) -> None:
            self.page = FakePage()

        def new_page(self) -> FakePage:
            return self.page

        def close(self) -> None:
            recorded.append(("close",))

    class FakeChromium:
        def launch(self, *, headless: bool) -> FakeBrowser:
            recorded.append(("launch", headless))
            return FakeBrowser()

    class FakePlaywright:
        def __enter__(self) -> types.SimpleNamespace:
            return types.SimpleNamespace(chromium=FakeChromium())

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    def _sync_playwright() -> FakePlaywright:
        return FakePlaywright()

    monkeypatch.setitem(
        sys.modules,
        "playwright.sync_api",
        types.SimpleNamespace(sync_playwright=_sync_playwright),
    )

    fill_result = llm_computer_use._execute_playwright(
        action_name="fill",
        action_args={"target": "#search", "input_text": "query", "timeout_ms": 1234},
        url="https://example.com/start",
    )
    wait_result = llm_computer_use._execute_playwright(
        action_name="wait",
        action_args={"wait_ms": 55},
        url="https://example.com/start",
    )
    scroll_result = llm_computer_use._execute_playwright(
        action_name="scroll",
        action_args={},
        url="https://example.com/start",
    )
    unknown_result = llm_computer_use._execute_playwright(
        action_name="unknown",
        action_args={},
        url="https://example.com/start",
    )

    assert fill_result["status"] == "ok"
    assert wait_result["status"] == "ok"
    assert scroll_result["status"] == "ok"
    assert unknown_result["status"] == "ok"
    assert ("fill", "#search", "query", 1234) in recorded
    assert ("wait", 55) in recorded
    assert ("evaluate", "window.scrollBy(0, Math.max(200, window.innerHeight * 0.8));") in recorded
    assert ("wait", 100) in recorded


def test_execute_playwright_navigate_requires_url(monkeypatch: Any) -> None:
    class FakePage:
        def __init__(self) -> None:
            self.url = "https://example.com/start"

        def goto(self, _url: str, *, timeout: int, wait_until: str) -> None:
            _ = (timeout, wait_until)

        def screenshot(self, *, type: str, full_page: bool) -> bytes:
            _ = (type, full_page)
            return b"png-bytes"

    class FakeBrowser:
        def __init__(self) -> None:
            self.page = FakePage()

        def new_page(self) -> FakePage:
            return self.page

        def close(self) -> None:
            return None

    class FakeChromium:
        def launch(self, *, headless: bool) -> FakeBrowser:
            _ = headless
            return FakeBrowser()

    class FakePlaywright:
        def __enter__(self) -> types.SimpleNamespace:
            return types.SimpleNamespace(chromium=FakeChromium())

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    def _sync_playwright() -> FakePlaywright:
        return FakePlaywright()

    monkeypatch.setitem(
        sys.modules,
        "playwright.sync_api",
        types.SimpleNamespace(sync_playwright=_sync_playwright),
    )
    result = llm_computer_use._execute_playwright(
        action_name="navigate",
        action_args={},
        url="https://example.com/start",
    )

    assert result["status"] == "error"
    assert str(result["error"]).startswith("computer_use_playwright_failed:")
    assert "navigate action requires url" in str(result["error"])


def test_execute_playwright_fill_uses_element_and_text_alias_with_default_timeout(
    monkeypatch: Any,
) -> None:
    recorded: list[tuple[str, Any]] = []

    class FakePage:
        def __init__(self) -> None:
            self.url = "https://example.com/original"

        def goto(self, url: str, *, timeout: int, wait_until: str) -> None:
            recorded.append(("goto", url, timeout, wait_until))
            self.url = url

        def fill(self, selector: str, text: str, *, timeout: int) -> None:
            recorded.append(("fill", selector, text, timeout))

        def screenshot(self, *, type: str, full_page: bool) -> bytes:
            recorded.append(("screenshot", type, full_page))
            return b"png-bytes"

    class FakeBrowser:
        def __init__(self) -> None:
            self.page = FakePage()

        def new_page(self) -> FakePage:
            return self.page

        def close(self) -> None:
            recorded.append(("close",))

    class FakeChromium:
        def launch(self, *, headless: bool) -> FakeBrowser:
            recorded.append(("launch", headless))
            return FakeBrowser()

    class FakePlaywright:
        def __enter__(self) -> types.SimpleNamespace:
            return types.SimpleNamespace(chromium=FakeChromium())

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    monkeypatch.setitem(
        sys.modules,
        "playwright.sync_api",
        types.SimpleNamespace(sync_playwright=FakePlaywright),
    )

    result = llm_computer_use._execute_playwright(
        action_name="fill",
        action_args={"element": "#query", "text": "hello"},
        url="https://example.com/start",
    )

    assert result["status"] == "ok"
    assert result["action"] == {"name": "fill", "args": {"element": "#query", "text": "hello"}}
    assert result["screenshot_base64"] == "cG5nLWJ5dGVz"
    assert ("goto", "https://example.com/start", 8000, "domcontentloaded") in recorded
    assert ("fill", "#query", "hello", 8000) in recorded


def test_execute_playwright_wait_uses_default_wait_ms(monkeypatch: Any) -> None:
    recorded: list[tuple[str, Any]] = []

    class FakePage:
        def __init__(self) -> None:
            self.url = "https://example.com/original"

        def goto(self, url: str, *, timeout: int, wait_until: str) -> None:
            recorded.append(("goto", url, timeout, wait_until))
            self.url = url

        def wait_for_timeout(self, wait_ms: int) -> None:
            recorded.append(("wait", wait_ms))

        def screenshot(self, *, type: str, full_page: bool) -> bytes:
            recorded.append(("screenshot", type, full_page))
            return b"png-bytes"

    class FakeBrowser:
        def __init__(self) -> None:
            self.page = FakePage()

        def new_page(self) -> FakePage:
            return self.page

        def close(self) -> None:
            recorded.append(("close",))

    class FakeChromium:
        def launch(self, *, headless: bool) -> FakeBrowser:
            recorded.append(("launch", headless))
            return FakeBrowser()

    class FakePlaywright:
        def __enter__(self) -> types.SimpleNamespace:
            return types.SimpleNamespace(chromium=FakeChromium())

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    monkeypatch.setitem(
        sys.modules,
        "playwright.sync_api",
        types.SimpleNamespace(sync_playwright=FakePlaywright),
    )

    result = llm_computer_use._execute_playwright(
        action_name="wait",
        action_args={},
        url="https://example.com/start",
    )

    assert result["status"] == "ok"
    assert ("wait", 800) in recorded


def test_execute_playwright_runtime_exception_returns_failed(monkeypatch: Any) -> None:
    class FakePage:
        def __init__(self) -> None:
            self.url = "https://example.com/original"

        def goto(self, url: str, *, timeout: int, wait_until: str) -> None:
            _ = (url, timeout, wait_until)

        def fill(self, selector: str, text: str, *, timeout: int) -> None:
            _ = (selector, text, timeout)
            raise RuntimeError("fill exploded")

    class FakeBrowser:
        def __init__(self) -> None:
            self.page = FakePage()

        def new_page(self) -> FakePage:
            return self.page

        def close(self) -> None:
            return None

    class FakeChromium:
        def launch(self, *, headless: bool) -> FakeBrowser:
            _ = headless
            return FakeBrowser()

    class FakePlaywright:
        def __enter__(self) -> types.SimpleNamespace:
            return types.SimpleNamespace(chromium=FakeChromium())

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

    monkeypatch.setitem(
        sys.modules,
        "playwright.sync_api",
        types.SimpleNamespace(sync_playwright=FakePlaywright),
    )

    result = llm_computer_use._execute_playwright(
        action_name="fill",
        action_args={"target": "#q", "input_text": "boom"},
        url="https://example.com/start",
    )

    assert result["status"] == "error"
    assert str(result["error"]).startswith("computer_use_playwright_failed:")
    assert "fill exploded" in str(result["error"])


def test_build_default_handler_target_overrides_and_context_copy(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        llm_computer_use,
        "_execute_playwright",
        lambda **kwargs: {
            "ok": True,
            "status": "ok",
            "action": {"name": kwargs["action_name"], "args": kwargs["action_args"]},
        },
    )

    state = {
        "computer_use": {
            "executor": "playwright",
            "url": "https://base.example/video",
            "screenshot": "base-shot",
            "context": {"from": "base"},
        }
    }
    handler = llm_computer_use.build_default_computer_use_handler(
        state=state,
        llm_policy={},
        section_policy={},
    )

    incoming_context = {"from": "incoming"}
    overridden = handler(
        action="click",
        selector="#cta",
        url="https://override.example/video",
        screenshot="override-shot",
        context=incoming_context,
    )
    base_context = handler(action="click", selector="#base")

    assert overridden["target"] == {
        "url": "https://override.example/video",
        "screenshot": "override-shot",
        "context": {"from": "incoming"},
    }
    overridden["target"]["context"]["from"] = "mutated"
    assert incoming_context == {"from": "incoming"}

    assert base_context["target"]["url"] == "https://base.example/video"
    assert base_context["target"]["screenshot"] == "base-shot"
    assert base_context["target"]["context"] == {"from": "base"}
    base_context["target"]["context"]["from"] = "changed"
    assert state["computer_use"]["context"] == {"from": "base"}


def test_build_default_handler_wraps_base_non_dict_context() -> None:
    handler = llm_computer_use.build_default_computer_use_handler(
        state={
            "computer_use": {
                "executor": "browser_stub",
                "url": "https://base.example/video",
                "context": "raw-base-context",
            }
        },
        llm_policy={},
        section_policy={},
    )

    result = handler(action="click", selector="#cta")

    assert result["status"] == "ok"
    assert result["target"]["context"] == {"value": "raw-base-context"}


def test_resolve_computer_use_payload_uses_top_level_llm_fields_and_state_fallback() -> None:
    payload = llm_computer_use._resolve_computer_use_payload(
        state={
            "source_url": "https://state.example/video",
            "computer_use": {
                "executor": "browser_stub",
                "url": "https://state.example/override",
                "screenshot": "state-shot",
                "context": {"from": "state"},
            },
        },
        llm_policy={
            "computer_use_executor": "playwright",
            "computer_use_url": "https://llm.example/video",
            "computer_use_screenshot": "llm-shot",
            "computer_use_context": {"from": "llm"},
            "computer_use": {},
        },
        section_policy={},
    )
    fallback_payload = llm_computer_use._resolve_computer_use_payload(
        state={
            "source_url": "https://state.example/video",
            "computer_use": {
                "executor": "browser_stub",
                "screenshot": "state-shot",
                "context": {"from": "state"},
            },
        },
        llm_policy={
            "computer_use_executor": "",
            "computer_use_url": "",
            "computer_use_screenshot": "",
            "computer_use_context": {},
        },
        section_policy={},
    )

    assert payload == {
        "executor": "playwright",
        "url": "https://llm.example/video",
        "screenshot": "llm-shot",
        "context": {"from": "llm"},
    }
    assert fallback_payload == {
        "executor": "browser_stub",
        "url": "https://state.example/video",
        "screenshot": "state-shot",
        "context": {"from": "state"},
    }


def test_normalize_action_prefers_action_key_and_filters_transport_fields() -> None:
    action_name, action_args = llm_computer_use._normalize_action(
        {
            "action": " Fill ",
            "type": "click",
            "name": "tap",
            "selector": "#query",
            "text": "hello",
            "url": "https://example.com",
            "screenshot": "shot",
            "context": {"k": "v"},
        }
    )

    assert action_name == "fill"
    assert action_args == {"selector": "#query", "text": "hello"}
