from __future__ import annotations

import os
from urllib.error import URLError
from urllib.request import urlopen

import pytest


def test_web_smoke_page_available_and_contains_expected_text() -> None:
    base_url = os.getenv("WEB_BASE_URL")
    if not base_url:
        pytest.skip("WEB_BASE_URL is not set. Example: http://127.0.0.1:8000/healthz")

    try:
        with urlopen(base_url, timeout=3):
            pass
    except URLError as exc:
        pytest.skip(f"WEB_BASE_URL is unreachable: {exc}")

    playwright = pytest.importorskip("playwright.sync_api")
    expected_text = os.getenv("WEB_E2E_EXPECT_TEXT", "").strip()

    try:
        with playwright.sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            response = page.goto(base_url, wait_until="domcontentloaded")
            body_text = (page.text_content("body") or "").strip()
            browser.close()
    except Exception as exc:
        pytest.skip(f"Playwright runtime unavailable: {exc}")

    assert response is not None
    assert response.status < 400
    if expected_text:
        assert expected_text in body_text
    else:
        assert len(body_text) > 0
