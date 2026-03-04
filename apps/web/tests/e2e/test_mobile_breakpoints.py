"""Mobile profile regression checks.

Recommended run args:
- --web-e2e-device-profile=mobile
- -k "mobile"
"""

import re

from playwright.sync_api import Page, expect


def _assert_no_horizontal_overflow(page: Page, route: str) -> None:
    metrics = page.evaluate(
        """
        () => {
            const doc = document.documentElement;
            const body = document.body;
            const rootScrollWidth = Math.max(
                doc.scrollWidth,
                body ? body.scrollWidth : 0
            );
            const offenders = [];
            for (const el of Array.from(document.querySelectorAll("*"))) {
                const rect = el.getBoundingClientRect();
                if (rect.width <= 0 || rect.height <= 0) {
                    continue;
                }
                if (rect.right > doc.clientWidth + 1) {
                    offenders.push(
                        `${el.tagName.toLowerCase()}.${String(el.className || "").slice(0, 48)}`
                    );
                }
                if (offenders.length >= 8) {
                    break;
                }
            }
            return {
                clientWidth: doc.clientWidth,
                scrollWidth: rootScrollWidth,
                offenders
            };
        }
        """
    )
    assert metrics["scrollWidth"] <= metrics["clientWidth"] + 1, (
        f"{route} has horizontal overflow on mobile profile: "
        f"scrollWidth={metrics['scrollWidth']} clientWidth={metrics['clientWidth']} "
        f"offenders={metrics['offenders']}"
    )


def test_mobile_profile_layout_and_cta_visibility(page: Page) -> None:
    page.goto("/", wait_until="domcontentloaded")

    viewport = page.viewport_size
    assert viewport is not None
    assert viewport["width"] <= 430, (
        "expected mobile viewport width <= 430; "
        "run with --web-e2e-device-profile=mobile"
    )

    expect(page.get_by_role("heading", name="拉取采集")).to_be_visible()
    expect(page.get_by_role("button", name="触发采集")).to_be_visible()
    expect(page.get_by_role("button", name="开始处理")).to_be_visible()

    # trial=True validates "clickable/actionable" without mutating backend state.
    page.get_by_role("button", name="触发采集").click(trial=True)
    page.get_by_role("button", name="开始处理").click(trial=True)

    _assert_no_horizontal_overflow(page, "/")
    page.get_by_role("link", name=re.compile(r"设置|任务")).first.click()
    expect(page).to_have_url(re.compile(r"/(settings|jobs)$"))
    _assert_no_horizontal_overflow(page, page.url)
