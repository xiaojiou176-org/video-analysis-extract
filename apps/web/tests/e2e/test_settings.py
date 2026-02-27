from __future__ import annotations

import re

from playwright.sync_api import Page, expect


def test_settings_save_config_button(page: Page) -> None:
    page.goto("/settings", wait_until="domcontentloaded")
    digest_hour = page.get_by_label("每日摘要发送时间（UTC 小时）")
    expect(digest_hour).to_be_disabled()
    page.get_by_label("收件人邮箱").fill("ops-e2e@example.com")
    daily_digest_toggle = page.get_by_label("启用每日摘要")
    daily_digest_toggle.check()
    expect(digest_hour).to_be_enabled()
    digest_hour.fill("7")
    daily_digest_toggle.uncheck()
    expect(digest_hour).to_be_disabled()
    daily_digest_toggle.check()
    expect(digest_hour).to_be_enabled()
    page.get_by_role("button", name="保存配置").click()

    expect(page).to_have_url(
        re.compile(r"/settings\?status=success&code=NOTIFICATION_CONFIG_SAVED")
    )
    expect(page.locator("p.alert.success")).to_contain_text("通知配置已保存。")


def test_settings_send_test_email_button(page: Page) -> None:
    page.goto("/settings", wait_until="domcontentloaded")
    page.get_by_label("覆盖收件人（可选）").fill("qa-e2e@example.com")
    page.get_by_label("主题（可选）").fill("E2E notification check")
    page.get_by_label("正文（可选）").fill("this is an automated e2e notification test")
    page.get_by_role("button", name="发送测试邮件").click()

    expect(page).to_have_url(re.compile(r"/settings\?status=success&code=NOTIFICATION_TEST_SENT"))
    expect(page.locator("p.alert.success")).to_contain_text("测试通知已发送。")
