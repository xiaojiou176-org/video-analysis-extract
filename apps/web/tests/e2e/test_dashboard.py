from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect
from support.runtime_utils import parse_external_web_base_url


def test_external_web_base_url_option_parsing() -> None:
    assert parse_external_web_base_url(None) is None
    assert parse_external_web_base_url("") is None
    assert parse_external_web_base_url("  http://127.0.0.1:3300/  ") == "http://127.0.0.1:3300"

    with pytest.raises(RuntimeError, match="absolute http\\(s\\) URL"):
        parse_external_web_base_url("not-a-url")


def test_external_web_base_url_option_validation_message() -> None:
    with pytest.raises(RuntimeError, match="absolute http\\(s\\) URL"):
        parse_external_web_base_url("ftp://127.0.0.1:3300")


def test_dashboard_trigger_ingest_poll_button(page: Page) -> None:
    page.goto("/", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="拉取采集")).to_be_visible()
    for attempt in range(2):
        page.get_by_role("button", name="触发采集").click()
        try:
            # Allow additional query parameters and ordering differences from redirect chains.
            expect(page).to_have_url(
                re.compile(r".*status=success.*code=POLL_INGEST_OK"),
                timeout=12000,
            )
            break
        except AssertionError:
            # Retry once when backend returns a transient request error.
            if attempt == 0 and "code=ERR_REQUEST_FAILED" in page.url:
                page.goto("/", wait_until="domcontentloaded")
                continue
            raise
    expect(page.locator("p.alert.success")).to_contain_text("已触发采集任务。")


def test_layout_health_chip_states(page: Page) -> None:
    page.goto("/", wait_until="domcontentloaded")
    expect(page.get_by_role("link", name=re.compile(r"API 状态：(正常|异常|未知)"))).to_be_visible()


def test_dashboard_start_processing_button(page: Page) -> None:
    page.goto("/", wait_until="domcontentloaded")
    start_button = page.get_by_role("button", name="开始处理")
    expect(start_button).to_be_disabled()
    page.get_by_label("视频链接 *").fill("invalid-url")
    expect(start_button).to_be_disabled()
    page.get_by_label("视频链接 *").fill("https://www.youtube.com/watch?v=e2e001")
    expect(start_button).to_be_enabled()
    page.get_by_label("模式 *").select_option("text_only")
    page.get_by_role("checkbox", name="强制执行").check()
    for attempt in range(2):
        start_button.click()
        try:
            expect(page).to_have_url(
                re.compile(r".*status=success.*code=PROCESS_VIDEO_OK"),
                timeout=12000,
            )
            break
        except AssertionError:
            if attempt == 0 and "code=ERR_REQUEST_FAILED" in page.url:
                page.goto("/", wait_until="domcontentloaded")
                start_button = page.get_by_role("button", name="开始处理")
                page.get_by_label("视频链接 *").fill("https://www.youtube.com/watch?v=e2e001")
                page.get_by_label("模式 *").select_option("text_only")
                page.get_by_role("checkbox", name="强制执行").check()
                continue
            raise
    expect(page.locator("p.alert.success")).to_contain_text("已创建处理任务。")
