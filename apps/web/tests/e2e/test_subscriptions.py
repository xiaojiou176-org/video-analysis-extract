from __future__ import annotations

import re
from uuid import uuid4

from playwright.sync_api import Page, expect


def _create_subscription_via_form(page: Page, source_value: str) -> None:
    page.get_by_label("来源值").fill(source_value)
    page.get_by_label("适配器类型").select_option("rsshub_route")
    page.get_by_label("RSSHub 路由（可选）").fill("/youtube/channel/vd-e2e")
    page.get_by_label("分类").select_option("creator")
    page.get_by_label("标签（逗号分隔，可选）").fill("ai,weekly")
    page.get_by_role("button", name="保存订阅").click()


def test_subscriptions_save_subscription_button(page: Page) -> None:
    source_value = f"https://youtube.com/@vd-e2e-{uuid4().hex[:8]}"
    page.goto("/subscriptions", wait_until="domcontentloaded")
    _create_subscription_via_form(page, source_value)

    expect(page).to_have_url(
        re.compile(r"/subscriptions\?status=success&code=SUBSCRIPTION_(CREATED|UPDATED)")
    )
    expect(page.locator("p.alert.success")).to_contain_text(re.compile(r"订阅已创建。|订阅已更新。"))
    created_row = page.locator("tbody tr", has_text=source_value)
    expect(created_row).to_be_visible()


def test_subscriptions_delete_button(page: Page) -> None:
    source_value = f"https://youtube.com/@vd-delete-{uuid4().hex[:8]}"
    page.goto("/subscriptions", wait_until="domcontentloaded")
    _create_subscription_via_form(page, source_value)

    row = page.locator("tbody tr", has_text=source_value)
    expect(row).to_be_visible()
    row.get_by_role("button", name="删除").click()
    row.get_by_role("button", name="确认删除").click()

    expect(page.locator("tbody tr", has_text=source_value)).to_have_count(0)
