from __future__ import annotations

import re
from uuid import uuid4

from playwright.sync_api import Page, expect


def _create_job_and_get_id(page: Page) -> str:
    page.goto("/", wait_until="domcontentloaded")
    page.get_by_label("视频链接 *").fill(f"https://www.youtube.com/watch?v=e2e-jobs-{uuid4().hex[:10]}")
    page.get_by_label("模式 *").select_option("text_only")
    page.get_by_role("button", name="开始处理").click()

    expect(page).to_have_url(re.compile(r"/\?status=success&code=PROCESS_VIDEO_OK"))
    expect(page.locator("p.alert.success")).to_contain_text("已创建处理任务。")

    jobs_link = page.locator("a[href^='/jobs?job_id=']").first
    expect(jobs_link).to_be_visible()
    href = jobs_link.get_attribute("href")
    assert href is not None
    matched = re.search(r"job_id=([^&]+)", href)
    assert matched is not None
    return matched.group(1)


def test_jobs_to_artifacts_query_navigation(page: Page) -> None:
    job_id = _create_job_and_get_id(page)

    page.goto("/jobs", wait_until="domcontentloaded")
    page.get_by_label("任务 ID *").fill(job_id)
    page.get_by_role("button", name="查询").click()

    expect(page).to_have_url(re.compile(rf"/jobs\?job_id={re.escape(job_id)}"))
    expect(page.get_by_role("heading", name="任务查询")).to_be_visible()

    page.get_by_role("link", name="查看产物页").click()
    expect(
        page
    ).to_have_url(re.compile(rf"/artifacts\?job_id={re.escape(job_id)}(?:&.*)?$"))
    expect(page.get_by_role("heading", name="产物查询")).to_be_visible()
    expect(page.locator("body")).to_contain_text(
        re.compile(r"Markdown 预览|产物请求已完成，但未返回 Markdown 内容。|请求失败，请稍后重试。")
    )

def test_artifacts_lookup_form_requires_single_field(page: Page) -> None:
    page.goto("/artifacts", wait_until="domcontentloaded")
    submit = page.get_by_role("button", name="加载产物")

    expect(submit).to_be_disabled()
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
    submit = page.get_by_role("button", name="查询")
    expect(submit).to_be_disabled()
    page.get_by_label("任务 ID *").fill("   ")
    expect(submit).to_be_disabled()
    page.get_by_label("任务 ID *").fill("00000000-0000-4000-8000-0000000000ff")
    expect(submit).to_be_enabled()


def test_artifact_lookup_by_video_url_shows_result_or_error(page: Page) -> None:
    page.goto("/artifacts", wait_until="domcontentloaded")
    page.get_by_label("视频 URL").fill("https://www.youtube.com/watch?v=e2e001")
    page.get_by_role("button", name="加载产物").click()

    expect(page).to_have_url(re.compile(r"/artifacts\?(?=.*(?:^|&)video_url=).*"))
    expect(page.locator("body")).to_contain_text(
        re.compile(r"Markdown 预览|产物请求已完成，但未返回 Markdown 内容。|请求失败，请稍后重试。")
    )
