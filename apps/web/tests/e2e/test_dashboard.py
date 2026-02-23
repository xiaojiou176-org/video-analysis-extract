from __future__ import annotations

from http import HTTPStatus

import pytest
from playwright.sync_api import Page, expect

from support.assertions import wait_for_call_count
from support.mock_api import MockApiState
from support.runtime_utils import external_web_base_url_from_env


def test_external_web_base_url_env_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WEB_BASE_URL", raising=False)
    assert external_web_base_url_from_env() is None

    monkeypatch.setenv("WEB_BASE_URL", "  http://127.0.0.1:3300/  ")
    assert external_web_base_url_from_env() == "http://127.0.0.1:3300"

    monkeypatch.setenv("WEB_BASE_URL", "not-a-url")
    with pytest.raises(RuntimeError, match="absolute http\\(s\\) URL"):
        external_web_base_url_from_env()


def test_dashboard_trigger_ingest_poll_button(page: Page, mock_api_state: MockApiState) -> None:
    page.goto("/", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Poll ingest")).to_be_visible()
    expect(page.get_by_role("link", name="API health: Healthy")).to_be_visible()
    page.get_by_role("button", name="Trigger ingest poll").click()

    wait_for_call_count(mock_api_state, "poll_ingest", 1)
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
    process_payload = mock_api_state.last_call("process_video")
    assert process_payload["video"]["url"] == "https://www.youtube.com/watch?v=e2e001"
    assert process_payload["mode"] == "text_only"
    assert process_payload["force"] is True
