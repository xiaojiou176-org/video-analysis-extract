from __future__ import annotations

import os
import re

import pytest
from playwright.sync_api import Page, expect


def _is_truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _mock_api_enabled(pytestconfig: pytest.Config) -> bool:
    option_value = pytestconfig.getoption("--web-e2e-use-mock-api")
    env_value = os.environ.get("WEB_E2E_USE_MOCK_API")
    return _is_truthy(None if option_value is None else str(option_value)) or _is_truthy(env_value)


def test_jobs_to_artifacts_query_navigation(page: Page, pytestconfig: pytest.Config) -> None:
    job_id = "00000000-0000-4000-8000-000000000001"

    page.goto("/jobs", wait_until="domcontentloaded")
    page.get_by_label("任务 ID *").fill(job_id)
    page.get_by_role("button", name="查询").click()

    expect(page).to_have_url(re.compile(rf"/jobs\?job_id={re.escape(job_id)}"))
    expect(page.get_by_role("heading", name="任务查询")).to_be_visible()

    artifacts_link = page.get_by_role("link", name="查看产物页")
    if _mock_api_enabled(pytestconfig):
        expect(artifacts_link).to_have_attribute(
            "href", re.compile(rf"/artifacts\?job_id={re.escape(job_id)}")
        )
        artifacts_link.click()
    else:
        # Real API mode may not have this job seeded; assert query contract without skipping.
        page.goto(f"/artifacts?job_id={job_id}", wait_until="domcontentloaded")

    expect(page).to_have_url(
        re.compile(rf"/artifacts\?job_id={re.escape(job_id)}(?:&.*)?$")
    )
    expect(page.get_by_role("heading", name="产物查询")).to_be_visible()
    expect(page.get_by_label("任务 ID")).to_have_value(job_id)


def test_artifacts_lookup_form_requires_single_field(page: Page) -> None:
    page.goto("/artifacts", wait_until="domcontentloaded")
    submit = page.get_by_role("button", name="加载产物")

    page.get_by_label("任务 ID").fill("00000000-0000-4000-8000-0000000000ff")
    expect(submit).to_be_enabled()
    page.get_by_label("视频 URL").fill("https://www.youtube.com/watch?v=e2e001")
    expect(submit).to_be_disabled()
    page.get_by_label("任务 ID").fill("")
    expect(submit).to_be_enabled()
    page.get_by_label("视频 URL").fill("")
    expect(submit).to_be_disabled()


def test_jobs_lookup_form_requires_job_id(page: Page) -> None:
    page.goto("/jobs", wait_until="domcontentloaded")
    job_id_input = page.get_by_label("任务 ID *")
    expect(job_id_input).to_have_attribute("required", "")

    job_id_input.fill("00000000-0000-4000-8000-0000000000ff")
    job_id_input.press("Enter")
    expect(page).to_have_url(
        re.compile(r"/jobs\?job_id=00000000-0000-4000-8000-0000000000ff(?:&.*)?$")
    )


def test_artifact_lookup_by_video_url_shows_markdown_result(
    page: Page, pytestconfig: pytest.Config
) -> None:
    page.goto("/artifacts", wait_until="domcontentloaded")
    page.get_by_label("视频 URL").fill("https://www.youtube.com/watch?v=e2e001")
    page.get_by_role("button", name="加载产物").click()

    expect(page).to_have_url(re.compile(r"/artifacts\?(?:.*&)?video_url=.*"))
    if _mock_api_enabled(pytestconfig):
        _expect_artifact_success_result(page)
    else:
        _expect_artifact_response_rendered(page)


def test_artifact_lookup_by_invalid_job_id_shows_error_alert(page: Page) -> None:
    page.goto("/artifacts", wait_until="domcontentloaded")
    page.get_by_label("任务 ID").fill("invalid-job-id")
    page.get_by_role("button", name="加载产物").click()

    expect(page).to_have_url(re.compile(r"/artifacts\?job_id=.*"))
    _expect_artifact_error_alert(page)


def _expect_artifact_success_result(page: Page) -> None:
    error_alert = page.locator("p.alert.error")
    expect(page.locator("h3", has_text="Markdown 预览")).to_be_visible(timeout=8_000)
    expect(error_alert).to_have_count(0)

    expect(page.locator("article.markdown-body")).to_be_visible(timeout=8_000)


def _expect_artifact_response_rendered(page: Page) -> None:
    error_alert = page.locator("p.alert.error")
    markdown_preview = page.locator("h3", has_text="Markdown 预览")
    empty_success = page.get_by_text("产物请求已完成，但未返回 Markdown 内容。")

    expect(markdown_preview.or_(empty_success).or_(error_alert).first).to_be_visible(timeout=8_000)


def _expect_artifact_error_alert(page: Page) -> None:
    error_alert = page.locator("p.alert.error")
    expect(error_alert).to_be_visible(timeout=8_000)
    error_text = error_alert.inner_text().strip()
    allowed_error_texts = {
        "标识符格式不合法。",
        "输入参数不合法，请检查后重试。",
        "请求失败，请稍后重试。",
        "加载产物请求失败，请稍后重试。",
    }
    assert error_text in allowed_error_texts, (
        f"unexpected artifact error text: {error_text!r}"
    )
