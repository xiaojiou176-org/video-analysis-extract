from __future__ import annotations

from http import HTTPStatus

from playwright.sync_api import Page, expect
from support.assertions import wait_for_call_count, wait_for_http_call
from support.mock_api import MockApiState, seed_subscription


def test_subscriptions_save_subscription_button(page: Page, mock_api_state: MockApiState) -> None:
    page.goto("/subscriptions", wait_until="domcontentloaded")
    page.get_by_label("Source value").fill("https://youtube.com/@vd-e2e")
    page.get_by_label("Adapter type").select_option("rsshub_route")
    page.get_by_label("RSSHub route (optional)").fill("/youtube/channel/vd-e2e")
    page.get_by_label("Category").select_option("creator")
    page.get_by_label("Tags (comma separated, optional)").fill("ai,weekly")
    page.get_by_role("button", name="Save subscription").click()

    wait_for_call_count(mock_api_state, "upsert_subscription", 1)
    wait_for_http_call(
        mock_api_state,
        method="POST",
        path="/api/v1/subscriptions",
        status=int(HTTPStatus.OK),
        payload_contains={"source_value": "https://youtube.com/@vd-e2e"},
    )
    upsert_payload = mock_api_state.last_call("upsert_subscription")
    assert upsert_payload["source_value"] == "https://youtube.com/@vd-e2e"
    assert upsert_payload["adapter_type"] == "rsshub_route"
    assert upsert_payload["rsshub_route"] == "/youtube/channel/vd-e2e"
    assert upsert_payload["category"] == "creator"
    assert upsert_payload["tags"] == ["ai", "weekly"]
    assert upsert_payload["enabled"] is True
    created_row = page.locator("tbody tr", has_text="https://youtube.com/@vd-e2e")
    expect(created_row).to_be_visible()


def test_subscriptions_delete_button(page: Page, mock_api_state: MockApiState) -> None:
    seeded_source = "https://youtube.com/@vd-delete"
    seeded_id = "00000000-0000-4000-8000-0000000000aa"
    seed_subscription(mock_api_state, seeded_id, seeded_source)

    page.goto("/subscriptions", wait_until="domcontentloaded")
    row = page.locator("tbody tr", has_text=seeded_source)
    expect(row).to_be_visible()
    row.get_by_role("button", name="Delete").click()

    wait_for_call_count(mock_api_state, "delete_subscription", 1)
    wait_for_http_call(
        mock_api_state,
        method="DELETE",
        path=f"/api/v1/subscriptions/{seeded_id}",
        status=int(HTTPStatus.NO_CONTENT),
    )
    delete_payload = mock_api_state.last_call("delete_subscription")
    assert delete_payload["id"] == seeded_id
    expect(page.locator("tbody tr", has_text=seeded_source)).to_have_count(0)
