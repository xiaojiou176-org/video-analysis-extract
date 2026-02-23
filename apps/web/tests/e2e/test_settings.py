from __future__ import annotations

from playwright.sync_api import Page, expect

from support.assertions import wait_for_call_count
from support.mock_api import MockApiState


def test_settings_save_config_button(page: Page, mock_api_state: MockApiState) -> None:
    page.goto("/settings", wait_until="domcontentloaded")
    digest_hour = page.get_by_label("Daily digest hour (UTC)")
    expect(digest_hour).to_be_disabled()
    page.get_by_label("Recipient email").fill("ops-e2e@example.com")
    daily_digest_toggle = page.get_by_label("Enable daily digest")
    daily_digest_toggle.check()
    expect(digest_hour).to_be_enabled()
    digest_hour.fill("7")
    daily_digest_toggle.uncheck()
    expect(digest_hour).to_be_disabled()
    daily_digest_toggle.check()
    expect(digest_hour).to_be_enabled()
    page.get_by_role("button", name="Save config").click()

    wait_for_call_count(mock_api_state, "update_notification_config", 1)
    update_payload = mock_api_state.last_call("update_notification_config")
    assert update_payload["to_email"] == "ops-e2e@example.com"
    assert update_payload["daily_digest_enabled"] is True
    assert update_payload["daily_digest_hour_utc"] == 7


def test_settings_send_test_email_button(page: Page, mock_api_state: MockApiState) -> None:
    page.goto("/settings", wait_until="domcontentloaded")
    page.get_by_label("Override recipient (optional)").fill("qa-e2e@example.com")
    page.get_by_label("Subject (optional)").fill("E2E notification check")
    page.get_by_label("Body (optional)").fill("this is an automated e2e notification test")
    page.get_by_role("button", name="Send test email").click()

    wait_for_call_count(mock_api_state, "send_notification_test", 1)
    notify_payload = mock_api_state.last_call("send_notification_test")
    assert notify_payload["to_email"] == "qa-e2e@example.com"
    assert notify_payload["subject"] == "E2E notification check"
    assert notify_payload["body"] == "this is an automated e2e notification test"
