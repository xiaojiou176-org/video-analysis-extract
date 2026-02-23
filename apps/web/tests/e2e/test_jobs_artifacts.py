from __future__ import annotations

import re
from urllib.parse import quote

import pytest
from playwright.sync_api import Page, expect

from support.assertions import wait_for_call_count, wait_for_http_path, wait_for_http_query_fragment
from support.mock_api import MockApiState


def test_jobs_to_artifacts_query_navigation(page: Page, mock_api_state: MockApiState) -> None:
    page.goto("/jobs", wait_until="domcontentloaded")
    page.get_by_label("Job ID").fill(mock_api_state.job_id)
    page.get_by_role("button", name="Fetch job").click()

    expect(page).to_have_url(re.compile(r"/jobs\?job_id=job-e2e-001"))
    expect(page.get_by_role("heading", name="Job lookup")).to_be_visible()

    page.goto("/artifacts", wait_until="domcontentloaded")
    expect(page.get_by_role("heading", name="Artifact lookup")).to_be_visible()
    page.get_by_label("Job ID").fill(mock_api_state.job_id)
    page.get_by_role("button", name="Load artifacts").click()

    wait_for_call_count(mock_api_state, "get_artifact_markdown", 1)
    wait_for_http_path(mock_api_state, "/api/v1/artifacts/assets")
    wait_for_http_query_fragment(mock_api_state, "/api/v1/artifacts/assets", "path=screenshots%2Fframe_0001.png")
    wait_for_http_query_fragment(mock_api_state, "/api/v1/artifacts/assets", "path=screenshots%2Fframe_0002.webp")
    artifact_payload = mock_api_state.last_call("get_artifact_markdown")
    assert artifact_payload["job_id"] == mock_api_state.job_id
    assert artifact_payload["include_meta"] == "true"

    expect(page).to_have_url(re.compile(r"/artifacts\?job_id=job-e2e-001"))
    expect(page.get_by_role("heading", name="Artifact lookup")).to_be_visible()
    expect(page.get_by_role("heading", name="Markdown preview")).to_be_visible()


def test_artifacts_lookup_form_requires_single_field(page: Page) -> None:
    page.goto("/artifacts", wait_until="domcontentloaded")
    submit = page.get_by_role("button", name="Load artifacts")

    expect(submit).to_be_disabled()
    page.get_by_label("Job ID").fill("job-e2e-001")
    expect(submit).to_be_enabled()
    page.get_by_label("Video URL").fill("https://www.youtube.com/watch?v=e2e001")
    expect(submit).to_be_disabled()
    page.get_by_label("Job ID").fill("")
    expect(submit).to_be_enabled()
    page.get_by_label("Video URL").fill("")
    expect(submit).to_be_disabled()


def test_jobs_lookup_form_requires_job_id(page: Page) -> None:
    page.goto("/jobs", wait_until="domcontentloaded")
    submit = page.get_by_role("button", name="Fetch job")
    expect(submit).to_be_disabled()
    page.get_by_label("Job ID").fill("   ")
    expect(submit).to_be_disabled()
    page.get_by_label("Job ID").fill("job-e2e-001")
    expect(submit).to_be_enabled()


@pytest.mark.parametrize(
    "frame_file",
    [
        "screenshots/frame_0001.png",
        "screenshots/frame_0002.jpg",
        "screenshots/frame_0003.webp",
    ],
    ids=["artifact-png", "artifact-jpg", "artifact-webp"],
)
def test_artifact_preview_and_asset_request_for_image_formats(
    page: Page,
    mock_api_state: MockApiState,
    frame_file: str,
) -> None:
    with mock_api_state.lock:
        mock_api_state.artifact_frame_files = [frame_file]

    page.goto("/artifacts", wait_until="domcontentloaded")
    page.get_by_label("Job ID").fill(mock_api_state.job_id)
    page.get_by_role("button", name="Load artifacts").click()

    wait_for_call_count(mock_api_state, "get_artifact_markdown", 1)
    wait_for_http_path(mock_api_state, "/api/v1/artifacts/assets")
    wait_for_http_query_fragment(
        mock_api_state,
        "/api/v1/artifacts/assets",
        f"path={quote(frame_file, safe='')}",
    )

    embedded_section = page.locator("section", has=page.get_by_role("heading", name="Embedded screenshots"))
    expect(embedded_section).to_be_visible()
    expect(embedded_section.get_by_role("link", name="Open screenshot 1")).to_be_visible()
    expect(page.locator(f'object[aria-label="Screenshot 1: {frame_file}"]')).to_be_visible()

    fallback_section = page.locator("section", has=page.get_by_role("heading", name="Screenshot index (fallback)"))
    expect(fallback_section).to_be_visible()
    expect(fallback_section.locator("code", has_text=frame_file)).to_be_visible()
