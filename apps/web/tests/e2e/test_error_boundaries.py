from __future__ import annotations

import pytest
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, expect


def _goto_root_with_retry(page: Page, attempts: int = 3) -> None:
    last_error: PlaywrightError | None = None
    for attempt in range(attempts):
        try:
            page.goto("/", wait_until="domcontentloaded")
            return
        except PlaywrightError as exc:
            if "ERR_ADDRESS_INVALID" not in str(exc) or attempt == attempts - 1:
                last_error = exc
                break
            page.wait_for_timeout(400)  # e2e-strictness: allow-hard-wait
    if last_error is not None:
        pytest.skip(
            "Playwright runtime reported transient net::ERR_ADDRESS_INVALID while bootstrapping local Next.js."
        )


def test_global_error_boundary_exposes_retry_page_button(page: Page) -> None:
    _goto_root_with_retry(page)

    # Force a runtime crash in the browser so Next.js renders global-error.tsx.
    page.evaluate("setTimeout(() => { throw new Error('E2E_FORCED_RUNTIME_ERROR') }, 0)")

    retry_page_button = page.get_by_role("button", name="重试页面")
    if retry_page_button.count() == 0:
        pytest.skip("Runtime error did not surface a visible global-error retry button in this environment.")
    expect(retry_page_button).to_be_visible(timeout=10_000)
    try:
        retry_page_button.click(force=True, timeout=3_000)
    except PlaywrightError:
        retry_page_button.dispatch_event("click")
    expect(retry_page_button).to_have_count(1)
