from __future__ import annotations

import re
from uuid import uuid4

from playwright.sync_api import Locator, Page, TimeoutError, expect


def _select_option(page: Page, label: str, option_name: str) -> None:
    trigger = page.get_by_role("combobox", name=label)
    trigger.click()
    option = page.get_by_role("option", name=option_name)
    try:
        option.first.click(timeout=3_000)
    except TimeoutError:
        page.locator("[data-slot='select-content']").get_by_text(option_name, exact=True).first.click()


def _create_subscription_form(page: Page) -> Locator:
    # Scope all create actions to the creation form only to avoid collisions
    # with same-labeled fields rendered in the subscriptions list.
    create_section = page.get_by_role("heading", name="创建或更新订阅").locator("xpath=ancestor::section[1]")
    create_form = create_section.locator("form").first
    expect(create_form).to_be_visible()
    return create_form


def _subscription_row(page: Page, source_value: str) -> Locator:
    return page.locator("tbody tr").filter(has_text=source_value).first


def _create_subscription_via_form(page: Page, source_value: str) -> None:
    create_form = _create_subscription_form(page)
    create_form.locator('[name="source_value"]').fill(source_value)
    _select_option(page, "适配器类型", "RSSHub 路由")
    create_form.locator('[name="rsshub_route"]').fill("/youtube/channel/vd-e2e")
    _select_option(page, "分类", "创作者")
    create_form.locator('[name="tags"]').fill("ai,weekly")
    create_form.evaluate("(form) => form.requestSubmit()")


def test_subscriptions_save_subscription_button(page: Page) -> None:
    source_value = f"https://www.youtube.com/@vd-e2e-{uuid4().hex[:8]}"
    page.goto("/subscriptions", wait_until="domcontentloaded")
    _create_subscription_via_form(page, source_value)

    expect(page).to_have_url(
        re.compile(r"/subscriptions\?status=success&code=SUBSCRIPTION_(CREATED|UPDATED)")
    )
    expect(page.locator("p.alert.success")).to_contain_text(
        re.compile(r"订阅已创建。|订阅已更新。")
    )
    created_row = _subscription_row(page, source_value)
    expect(created_row).to_be_visible()


def test_subscriptions_delete_button(page: Page) -> None:
    source_value = f"https://www.youtube.com/@vd-delete-{uuid4().hex[:8]}"
    page.goto("/subscriptions", wait_until="domcontentloaded")
    _create_subscription_via_form(page, source_value)

    row = _subscription_row(page, source_value)
    expect(row).to_be_visible()
    row.get_by_role("button", name="删除").click()
    row.get_by_test_id("subscription-confirm-delete").click()

    expect(page).to_have_url(
        re.compile(r"/subscriptions\?status=success&code=SUBSCRIPTION_DELETED")
    )
    expect(page.locator("tbody tr").filter(has_text=source_value)).to_have_count(0)
    expect(page.locator("p.alert.success")).to_contain_text("订阅已删除。")


def test_subscriptions_batch_update_category(page: Page) -> None:
    source_value = f"https://www.youtube.com/@vd-batch-{uuid4().hex[:8]}"
    page.goto("/subscriptions", wait_until="domcontentloaded")
    _create_subscription_via_form(page, source_value)

    row = _subscription_row(page, source_value)
    expect(row).to_be_visible()
    row.get_by_role("checkbox").click()
    _select_option(page, "批量设分类", "运维")
    page.get_by_test_id("subscription-apply-category").click()

    expect(_subscription_row(page, source_value)).to_contain_text("运维")
    undo_button = page.get_by_test_id("subscription-undo-category")
    expect(undo_button).to_be_visible()
    undo_button.click()
    expect(_subscription_row(page, source_value)).to_contain_text("创作者")
