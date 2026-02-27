import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import ArtifactsPage from "@/app/artifacts/page";
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
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("renders feed list with filters and next page link", async () => {
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

		expect(screen.getByText("AI 摘要订阅流")).toBeInTheDocument();
		expect(screen.getByText("AI Weekly")).toBeInTheDocument();
		expect(screen.getByText("YouTube · Tech Channel")).toBeInTheDocument();
		const feedCard = screen.getByText("AI Weekly").closest("article");
		expect(feedCard).not.toBeNull();
		expect(within(feedCard as HTMLElement).getByText("科技")).toBeInTheDocument();
		expect(screen.getByTestId("markdown-preview")).toHaveTextContent("## summary");
		expect(screen.getByRole("link", { name: "查看产物" })).toHaveAttribute(
			"href",
			"/artifacts?job_id=job-abcdef123",
		);
		expect(screen.getByRole("link", { name: "打开原始链接（在新标签页打开）" })).toHaveAttribute(
			"href",
			"https://www.youtube.com/watch?v=abc",
		);
		expect(screen.getByRole("link", { name: "下一页 →" })).toHaveAttribute(
			"href",
			"/feed?source=youtube&category=tech&limit=50&cursor=cursor-2",
		);
		expect(screen.getByRole("button", { name: "筛选" })).toBeInTheDocument();
	});

	it("renders feed empty state and clear filter entry", async () => {
		mockGetDigestFeed.mockResolvedValue({ items: [], has_more: false, next_cursor: null });

		render(await FeedPage({ searchParams: { source: "bilibili" } }));

		expect(screen.getByText("暂无 AI 摘要内容")).toBeInTheDocument();
		expect(screen.getByRole("link", { name: "清除筛选" })).toHaveAttribute("href", "/feed");
	});

	it("renders feed error message when api fails", async () => {
		mockGetDigestFeed.mockRejectedValue(new Error("ERR_INVALID_INPUT:bad"));

		render(await FeedPage({ searchParams: {} }));

		expect(screen.getByRole("alert")).toHaveTextContent("输入参数不合法，请检查后重试。");
	});

	it("renders jobs page details and artifact links", async () => {
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

		render(await JobsPage({ searchParams: { job_id: "job-1" } }));

		expect(mockGetJob).toHaveBeenCalledWith("job-1");
		expect(screen.getByText("任务概览")).toBeInTheDocument();
		expect(screen.getByText("job-1")).toBeInTheDocument();
		expect(screen.getByText("fetch_video")).toBeInTheDocument();
		expect(screen.getByText("llm_digest")).toBeInTheDocument();
		expect(screen.getByRole("link", { name: "查看产物页" })).toHaveAttribute(
			"href",
			"/artifacts?job_id=job-1",
		);
		expect(screen.getByRole("link", { name: /digest\.md/ })).toHaveAttribute(
			"href",
			"http://127.0.0.1:8000/api/v1/artifacts/assets?job_id=job-1&path=digest.md",
		);
	});

	it("renders jobs error when lookup fails", async () => {
		mockGetJob.mockRejectedValue(new Error("ERR_REQUEST_FAILED"));

		render(await JobsPage({ searchParams: { job_id: "job-missing" } }));

		expect(screen.getByRole("alert")).toHaveTextContent("请求失败，请稍后重试。");
	});

	it("renders artifacts with embedded screenshots and markdown", async () => {
		mockGetArtifactMarkdown.mockResolvedValue({
			markdown: "# artifact",
			meta: {
				frame_files: ["frame-1.png", "frame-2.jpg"],
				job: { id: "job-2" },
			},
		});

		render(
			await ArtifactsPage({ searchParams: { video_url: "https://www.youtube.com/watch?v=xyz" } }),
		);

		expect(mockGetArtifactMarkdown).toHaveBeenCalledWith({
			job_id: undefined,
			video_url: "https://www.youtube.com/watch?v=xyz",
			include_meta: true,
		});
		expect(screen.getByRole("link", { name: "查看截图 1" })).toHaveAttribute(
			"href",
			"http://127.0.0.1:8000/api/v1/artifacts/assets?job_id=job-2&path=frame-1.png",
		);
		expect(screen.getByLabelText("Screenshot 1: frame-1.png")).toBeInTheDocument();
		expect(screen.getByTestId("markdown-preview")).toHaveTextContent("# artifact");
	});

	it("renders artifacts status when api returns empty payload", async () => {
		mockGetArtifactMarkdown.mockResolvedValue(null);

		render(await ArtifactsPage({ searchParams: { job_id: "job-3" } }));

		expect(screen.getByText("产物请求已完成，但未返回 Markdown 内容。")).toBeInTheDocument();
	});

	it("renders artifacts error alert on failure", async () => {
		mockGetArtifactMarkdown.mockRejectedValue(new Error("ERR_REQUEST_FAILED"));

		render(await ArtifactsPage({ searchParams: { job_id: "job-err" } }));

		expect(screen.getByRole("alert")).toHaveTextContent("请求失败，请稍后重试。");
	});
});
