from __future__ import annotations

import re
from uuid import uuid4

from playwright.sync_api import Locator, Page, expect


def _create_subscription_form(page: Page) -> Locator:
    # Scope all create actions to the creation form only to avoid collisions
    # with same-labeled fields rendered in the subscriptions list.
    create_section = page.get_by_role("heading", name="创建或更新订阅").locator("xpath=ancestor::section[1]")
    create_form = create_section.locator("form").first
    expect(create_form).to_be_visible()
    return create_form


def _create_subscription_via_form(page: Page, source_value: str) -> None:
    create_form = _create_subscription_form(page)
    create_form.locator('[name="source_type"]').select_option("youtube_channel_id")
    create_form.locator('[name="source_value"]').fill(source_value)
    create_form.locator('[name="adapter_type"]').select_option("rsshub_route")
    create_form.locator('[name="rsshub_route"]').fill("/youtube/channel/vd-e2e")
    create_form.locator('[name="category"]').select_option("creator")
    create_form.locator('[name="tags"]').fill("ai,weekly")
    create_form.evaluate("(form) => form.requestSubmit()")


def test_subscriptions_save_subscription_button(page: Page) -> None:
    source_value = f"UC{uuid4().hex[:22]}"
    page.goto("/subscriptions", wait_until="domcontentloaded")
    _create_subscription_via_form(page, source_value)

    expect(page).to_have_url(
        re.compile(r"/subscriptions\?status=success&code=SUBSCRIPTION_(CREATED|UPDATED)")
    )
    expect(page.locator("p.alert.success")).to_contain_text(
        re.compile(r"订阅已创建。|订阅已更新。")
    )
    created_row = page.locator("tbody tr", has_text=source_value)
    expect(created_row).to_be_visible()


def test_subscriptions_delete_button(page: Page) -> None:
    source_value = f"UC{uuid4().hex[:22]}"
    page.goto("/subscriptions", wait_until="domcontentloaded")
    _create_subscription_via_form(page, source_value)

    row = page.locator("tbody tr", has_text=source_value)
    expect(row).to_be_visible()
    row.get_by_role("button", name="删除").click()
    row.get_by_role("button", name="确认删除").click()

    expect(page.locator("tbody tr", has_text=source_value)).to_have_count(0)


def test_subscriptions_batch_update_category(page: Page) -> None:
    source_value = f"UC{uuid4().hex[:22]}"
    page.goto("/subscriptions", wait_until="domcontentloaded")
    _create_subscription_via_form(page, source_value)

    row = page.locator("tbody tr", has_text=source_value)
    expect(row).to_be_visible()
    row.get_by_role("checkbox").check()
    page.get_by_label("批量设分类").select_option("ops")
    page.get_by_role("button", name="应用").click()

    expect(page.get_by_text("已将 1 条订阅移至分类「ops」")).to_be_visible()
    expect(page.locator("tbody tr", has_text=source_value)).to_contain_text("ops")
