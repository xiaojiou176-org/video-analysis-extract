from __future__ import annotations

from http import HTTPStatus

import pytest
from playwright.sync_api import Page, expect
from support.assertions import wait_for_call_count, wait_for_http_call
from support.mock_api import MockApiState
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


def test_dashboard_trigger_ingest_poll_button(page: Page, mock_api_state: MockApiState) -> None:
    page.goto("/", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Poll ingest")).to_be_visible()
    expect(page.get_by_role("link", name="API health: Healthy")).to_be_visible()
    page.get_by_role("button", name="Trigger ingest poll").click()

    wait_for_call_count(mock_api_state, "poll_ingest", 1)
    wait_for_http_call(
        mock_api_state,
        method="POST",
        path="/api/v1/ingest/poll",
        status=int(HTTPStatus.ACCEPTED),
        payload_contains={"max_new_videos": 50},
    )
    payload = mock_api_state.last_call("poll_ingest")
    assert payload.get("max_new_videos") == 50


@pytest.mark.parametrize(
    ("health_status", "health_delay_seconds", "expected_health_label"),
    [
        (int(HTTPStatus.OK), 0.0, "Healthy"),
        (int(HTTPStatus.SERVICE_UNAVAILABLE), 0.0, "Degraded"),
        (int(HTTPStatus.OK), 2.0, "Unknown"),
    ],
    ids=["status-200", "status-non200", "network-failure-timeout"],
)
def test_layout_health_chip_states(
    page: Page,
    mock_api_state: MockApiState,
    health_status: int,
    health_delay_seconds: float,
    expected_health_label: str,
) -> None:
    mock_api_state.health_delay_seconds = health_delay_seconds
    mock_api_state.health_status = health_status
    page.goto("/", wait_until="domcontentloaded")
    expect(page.get_by_role("link", name=f"API health: {expected_health_label}")).to_be_visible()


def test_dashboard_start_processing_button(page: Page, mock_api_state: MockApiState) -> None:
    page.goto("/", wait_until="domcontentloaded")
    start_button = page.get_by_role("button", name="Start processing")
    expect(start_button).to_be_disabled()
    page.get_by_label("Video URL").fill("invalid-url")
    expect(start_button).to_be_disabled()
    page.get_by_label("Video URL").fill("https://www.youtube.com/watch?v=e2e001")
    expect(start_button).to_be_enabled()
    page.get_by_label("Mode").select_option("text_only")
    page.get_by_role("checkbox", name="Force run").check()
    start_button.click()

    wait_for_call_count(mock_api_state, "process_video", 1)
    wait_for_http_call(
        mock_api_state,
        method="POST",
        path="/api/v1/videos/process",
        status=int(HTTPStatus.ACCEPTED),
        payload_check=lambda payload: bool(payload and payload.get("video", {}).get("url")),
    )
    process_payload = mock_api_state.last_call("process_video")
    assert process_payload["video"]["url"] == "https://www.youtube.com/watch?v=e2e001"
    assert process_payload["mode"] == "text_only"
    assert process_payload["force"] is True
