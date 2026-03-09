import { render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import FeedPage from "@/app/feed/page";
import JobsPage from "@/app/jobs/page";

const mockGetDigestFeed = vi.fn();
const mockGetJob = vi.fn();
const mockGetArtifactMarkdown = vi.fn();

vi.mock("next/link", () => ({
	default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
		<a href={href} {...rest}>
			{children}
		</a>
	),
}));

vi.mock("@/components/markdown-preview", () => ({
	MarkdownPreview: ({ markdown }: { markdown: string }) => (
		<div data-testid="markdown-preview">{markdown}</div>
	),
}));

vi.mock("@/components/relative-time", () => ({
	RelativeTime: ({ dateTime }: { dateTime: string }) => (
		<time data-testid="relative-time">{dateTime}</time>
	),
}));

vi.mock("@/components/sync-now-button", () => ({
	SyncNowButton: () => <button type="button">立即同步</button>,
}));

vi.mock("@/lib/api/client", () => ({
	apiClient: {
		getDigestFeed: (...args: unknown[]) => mockGetDigestFeed(...args),
		getJob: (...args: unknown[]) => mockGetJob(...args),
		getArtifactMarkdown: (...args: unknown[]) => mockGetArtifactMarkdown(...args),
	},
}));

describe("feed/jobs/artifacts pages", () => {
	const PAGE_TEST_TIMEOUT_MS = 15000;

	beforeEach(() => {
		vi.clearAllMocks();
	});

	it(
		"renders feed list with filters and next page link",
		async () => {
			mockGetDigestFeed.mockResolvedValue({
				items: [
					{
						feed_id: "feed-1",
						job_id: "job-abcdef123",
						video_url: "https://www.youtube.com/watch?v=abc",
						title: "AI Weekly",
						source: "youtube",
						source_name: "Tech Channel",
						category: "tech",
						published_at: "2026-02-01T00:00:00Z",
						summary_md: "## summary",
						artifact_type: "digest",
					},
				],
				has_more: true,
				next_cursor: "cursor-2",
			});

			render(
				await FeedPage({
					searchParams: { source: " youtube ", category: "tech", limit: "50" },
				}),
			);

			expect(mockGetDigestFeed).toHaveBeenCalledWith({
				source: "youtube",
				category: "tech",
				limit: 50,
				cursor: undefined,
			});

			expect(screen.getByText("AI Weekly")).toBeInTheDocument();
			expect(screen.getByText("YouTube · Tech Channel")).toBeInTheDocument();
			expect(screen.getAllByText("科技").length).toBeGreaterThan(0);
			expect(screen.getByRole("link", { name: /AI Weekly/ })).toHaveAttribute(
				"href",
				expect.stringContaining("item=job-abcdef123"),
			);
			expect(screen.getByRole("link", { name: "下一页 →" })).toHaveAttribute(
				"href",
				"/feed?source=youtube&category=tech&limit=50&page=2&cursor=cursor-2",
			);
				expect(screen.getByText("页码 1")).toBeInTheDocument();
				expect(screen.getByRole("button", { name: "筛选" })).toBeInTheDocument();
				expect(screen.getByRole("button", { name: "筛选" })).toHaveAttribute("data-variant", "hero");
				expect(screen.getByRole("link", { name: "下一页 →" })).toHaveAttribute("data-variant", "surface");
				const sourceSelect = screen.getByRole("combobox", { name: "来源" });
				expect(sourceSelect).toHaveTextContent("YouTube");
				const filterForm = screen.getByRole("button", { name: "筛选" }).closest("form");
				expect(filterForm).not.toBeNull();
				expect(
					(filterForm as HTMLElement).querySelector('input[type="hidden"][name="source"]'),
				).toHaveValue("youtube");
		},
		PAGE_TEST_TIMEOUT_MS,
	);

	it(
		"renders feed previous page link and explicit page state on non-first page",
		async () => {
			mockGetDigestFeed.mockResolvedValue({
				items: [
					{
						feed_id: "feed-2",
						job_id: "job-zxyw9876",
						video_url: "https://www.youtube.com/watch?v=def",
						title: "AI Deep Dive",
						source: "youtube",
						source_name: "Tech Channel",
						category: "tech",
						published_at: "2026-02-02T00:00:00Z",
						summary_md: "## summary 2",
						artifact_type: "digest",
					},
				],
				has_more: true,
				next_cursor: "cursor-3",
			});

			render(
				await FeedPage({
					searchParams: {
						source: "youtube",
						category: "tech",
						cursor: "cursor-2",
						prev_cursor: "cursor-1",
						page: "3",
					},
				}),
			);

			expect(screen.getByRole("link", { name: "← 上一页" })).toHaveAttribute(
				"href",
				"/feed?source=youtube&category=tech&page=2&cursor=cursor-1",
			);
			expect(screen.getByRole("link", { name: "← 上一页" })).toHaveAttribute("data-variant", "surface");
			expect(screen.getByText("页码 3")).toBeInTheDocument();
			expect(screen.getByRole("link", { name: "下一页 →" })).toHaveAttribute(
				"href",
				"/feed?source=youtube&category=tech&page=4&cursor=cursor-3&prev_cursor=cursor-2",
			);
			expect(screen.getByRole("link", { name: "下一页 →" })).toHaveAttribute("data-variant", "surface");
		},
		PAGE_TEST_TIMEOUT_MS,
	);

	it(
		"renders main reading flow when feed item is selected",
		async () => {
			mockGetDigestFeed.mockResolvedValue({
				items: [
					{
						feed_id: "feed-reading-1",
						job_id: "job-reading-1",
						video_url: "https://www.youtube.com/watch?v=reading1",
						title: "Digest One",
						source: "youtube",
						source_name: "Creator One",
						category: "creator",
						published_at: "2026-02-10T00:00:00Z",
						summary_md: "## summary 1",
						artifact_type: "digest",
					},
					{
						feed_id: "feed-reading-2",
						job_id: "job-reading-2",
						video_url: "https://www.youtube.com/watch?v=reading2",
						title: "Digest Two",
						source: "youtube",
						source_name: "Creator Two",
						category: "creator",
						published_at: "2026-02-11T00:00:00Z",
						summary_md: "## summary 2",
						artifact_type: "digest",
					},
				],
				has_more: false,
				next_cursor: null,
			});
			mockGetArtifactMarkdown.mockResolvedValue({
				markdown: "# Digest One\n\nMain reading body",
				meta: { job: { id: "job-reading-1" }, frame_files: [] },
			});

			render(await FeedPage({ searchParams: { item: "job-reading-1" } }));

			expect(screen.getByRole("complementary", { name: "条目列表" })).toBeInTheDocument();
			expect(screen.getByRole("link", { name: /Digest One/ })).toHaveAttribute("aria-current", "true");
			expect(screen.getByRole("link", { name: /Digest Two/ })).toHaveAttribute(
				"href",
				expect.stringContaining("item=job-reading-2"),
			);

			await waitFor(() => {
				expect(mockGetArtifactMarkdown).toHaveBeenCalledWith({
					job_id: "job-reading-1",
					include_meta: true,
				});
			});

			expect(await screen.findByTestId("markdown-preview")).toHaveTextContent("Main reading body");
			expect(screen.getByRole("link", { name: /job-read/ })).toHaveAttribute(
				"href",
				"/jobs?job_id=job-reading-1",
			);
			expect(screen.getByRole("link", { name: /打开原文/ })).toHaveAttribute(
				"href",
				"https://www.youtube.com/watch?v=reading1",
			);
		},
		PAGE_TEST_TIMEOUT_MS,
	);

	it(
		"passes subscription filter through feed query and preserves it in pagination urls",
		async () => {
			mockGetDigestFeed.mockResolvedValue({
				items: [
					{
						feed_id: "feed-sub",
						job_id: "job-sub",
						video_url: "https://example.com/article",
						title: "Article Digest",
						source: "rss",
						source_name: "Macro Blog",
						category: "macro",
						published_at: "2026-02-05T00:00:00Z",
						summary_md: "## article",
						artifact_type: "digest",
						content_type: "article",
					},
				],
				has_more: true,
				next_cursor: "cursor-sub",
			});

			render(await FeedPage({ searchParams: { sub: "sub-123", page: "2", cursor: "cursor-1" } }));

			expect(mockGetDigestFeed).toHaveBeenCalledWith({
				source: undefined,
				category: undefined,
				subscription_id: "sub-123",
				limit: 20,
				cursor: "cursor-1",
			});
			expect(screen.getByText("文章")).toBeInTheDocument();
			expect(screen.getByRole("link", { name: "← 上一页" })).toHaveAttribute(
				"href",
				"/feed?sub=sub-123",
			);
			expect(screen.getByRole("link", { name: "下一页 →" })).toHaveAttribute(
				"href",
				"/feed?sub=sub-123&page=3&cursor=cursor-sub&prev_cursor=cursor-1",
			);
		},
		PAGE_TEST_TIMEOUT_MS,
	);

	it(
		"keeps legacy source query executable and falls back source selector safely",
		async () => {
			mockGetDigestFeed.mockResolvedValue({
				items: [
					{
						feed_id: "feed-legacy",
						job_id: "job-legacy",
						video_url: "https://example.com/video",
						title: "Legacy Source Digest",
						source: "legacy_platform",
						source_name: "",
						category: "misc",
						published_at: "2026-02-01T00:00:00Z",
						summary_md: "legacy",
						artifact_type: "digest",
					},
				],
				has_more: true,
				next_cursor: "cursor-legacy",
			});

			render(await FeedPage({ searchParams: { source: " legacy_platform " } }));

			expect(mockGetDigestFeed).toHaveBeenCalledWith({
				source: "legacy_platform",
				category: undefined,
				limit: 20,
				cursor: undefined,
			});
			expect(screen.getByRole("combobox", { name: "来源" })).toHaveTextContent("全部来源");
		expect(screen.getAllByText("legacy_platform").length).toBeGreaterThan(0);
			expect(screen.getByRole("link", { name: "下一页 →" })).toHaveAttribute(
				"href",
				"/feed?source=legacy_platform&page=2&cursor=cursor-legacy",
			);
		},
		PAGE_TEST_TIMEOUT_MS,
	);

	it(
		"renders feed empty state and clear filter entry",
		async () => {
			mockGetDigestFeed.mockResolvedValue({ items: [], has_more: false, next_cursor: null });

			render(await FeedPage({ searchParams: { source: "bilibili" } }));

			expect(screen.getByText("暂无 AI 摘要内容")).toBeInTheDocument();
			expect(screen.getByRole("link", { name: "清除" })).toHaveAttribute("href", "/feed");
		},
		PAGE_TEST_TIMEOUT_MS,
	);

	it(
		"renders feed empty state subscription management link when no filters are active",
		async () => {
			mockGetDigestFeed.mockResolvedValue({ items: [], has_more: false, next_cursor: null });

			render(await FeedPage({ searchParams: {} }));

			expect(screen.getByRole("link", { name: "前往订阅管理" })).toHaveAttribute(
				"href",
				"/subscriptions",
			);
		},
		PAGE_TEST_TIMEOUT_MS,
	);

	it(
		"renders semantic disabled end-page control on last page",
		async () => {
			mockGetDigestFeed.mockResolvedValue({
				items: [
					{
						feed_id: "feed-last",
						job_id: "job-last",
						video_url: "https://www.youtube.com/watch?v=last",
						title: "Last Page Digest",
						source: "youtube",
						source_name: "Channel",
						category: "tech",
						published_at: "2026-02-03T00:00:00Z",
						summary_md: "last",
						artifact_type: "digest",
					},
				],
				has_more: false,
				next_cursor: null,
			});

			render(await FeedPage({ searchParams: { page: "2", cursor: "cursor-last" } }));

			const disabledEndControl = screen.queryByRole("button", { name: "已到末页" });
			expect(disabledEndControl).toBeNull();
			expect(screen.getByText("页码 2")).toBeInTheDocument();
		},
		PAGE_TEST_TIMEOUT_MS,
	);

	it(
		"renders feed error message when api fails",
		async () => {
			mockGetDigestFeed.mockRejectedValue(new Error("ERR_INVALID_INPUT:bad"));

			render(await FeedPage({ searchParams: {} }));

			expect(screen.getByRole("alert")).toHaveTextContent("输入参数不合法，请检查后重试。");
			expect(screen.getByRole("link", { name: "重试当前页面" })).toHaveAttribute("href", "/feed");
		},
		PAGE_TEST_TIMEOUT_MS,
	);

	it(
		"renders jobs page details and artifact links",
		async () => {
			mockGetJob.mockResolvedValue({
				id: "job-1",
				video_id: "video-1",
				kind: "video_digest_v1",
				status: "running",
				idempotency_key: "idem",
				error_message: null,
				artifact_digest_md: null,
				artifact_root: null,
				llm_required: true,
				llm_gate_passed: true,
				hard_fail_reason: null,
				created_at: "2026-02-01T00:00:00Z",
				updated_at: "2026-02-01T00:02:00Z",
				step_summary: [
					{
						name: "fetch_video",
						status: "succeeded",
						attempt: 1,
						started_at: "2026-02-01T00:00:00Z",
						finished_at: "2026-02-01T00:00:10Z",
						error: null,
					},
				],
				steps: [],
				degradations: [
					{
						step: "llm_digest",
						status: "degraded",
						reason: "timeout",
						error: null,
						error_kind: null,
						retry_meta: null,
						cache_meta: null,
					},
				],
				pipeline_final_status: "degraded",
				artifacts_index: { digest: "digest.md" },
				mode: "full",
			});

			const { container } = render(await JobsPage({ searchParams: { job_id: "job-1" } }));

			expect(mockGetJob).toHaveBeenCalledWith("job-1");
			expect(container.querySelector(".folo-page-shell")).not.toBeNull();
			expect(container.querySelectorAll('[data-slot="card"]').length).toBeGreaterThanOrEqual(4);
			expect(screen.getByRole("button", { name: "查询" })).toBeInTheDocument();
			const lookupInput = screen.getByRole("textbox", { name: "任务 ID *" });
			expect(lookupInput).toHaveValue("job-1");
			expect(lookupInput).toBeRequired();
			const lookupForm = lookupInput.closest("form");
			expect(lookupForm).not.toBeNull();
			expect(lookupForm).toHaveAttribute(
				"data-auto-disable-required",
				"true",
			);
			expect((lookupForm as HTMLElement).getAttribute("method")?.toLowerCase()).toBe("get");
			expect(within(lookupForm as HTMLElement).getByRole("button", { name: "查询" })).toHaveAttribute(
				"type",
				"submit",
			);
			expect(screen.getByText("任务概览")).toBeInTheDocument();
			expect(screen.getByText("job-1")).toBeInTheDocument();
			const overviewSection = screen.getByText("任务概览").closest('[data-slot="card"]');
			expect(overviewSection).not.toBeNull();
				expect(within(overviewSection as HTMLElement).getByText("运行中")).toBeInTheDocument();
				expect(within(overviewSection as HTMLElement).getByText("已降级")).toBeInTheDocument();
				expect(screen.getByRole("link", { name: "首页最近视频" })).toHaveAttribute("href", "/");
				expect(screen.getByRole("link", { name: "AI 摘要页" })).toHaveAttribute("href", "/feed");
				expect(screen.getByText("任务步骤摘要表")).toBeInTheDocument();
			expect(screen.getByText("任务步骤摘要表").closest(".overflow-x-auto")).not.toBeNull();
			expect(screen.getByText("fetch_video")).toBeInTheDocument();
			expect(screen.getByText("llm_digest")).toBeInTheDocument();
			expect(screen.getByText("已完成")).toBeInTheDocument();
			expect(screen.getByRole("link", { name: "在摘要流中查看" })).toHaveAttribute(
				"href",
				"/feed?item=job-1",
			);
			expect(screen.getByRole("link", { name: /digest\.md/ })).toHaveAttribute(
				"href",
				"http://127.0.0.1:9000/api/v1/artifacts/assets?job_id=job-1&path=digest.md",
			);
		},
		PAGE_TEST_TIMEOUT_MS,
	);

	it(
		"renders jobs error when lookup fails",
		async () => {
			mockGetJob.mockRejectedValue(new Error("ERR_REQUEST_FAILED"));

			render(await JobsPage({ searchParams: { job_id: "job-missing" } }));

			expect(screen.getByRole("alert")).toHaveTextContent("请求失败，请稍后重试。");
			expect(screen.getByRole("link", { name: "重试当前页面" })).toHaveAttribute(
				"href",
				"/jobs?job_id=job-missing",
			);
		},
		PAGE_TEST_TIMEOUT_MS,
	);

});
