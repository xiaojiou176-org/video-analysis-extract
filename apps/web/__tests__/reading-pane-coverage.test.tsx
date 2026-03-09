import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ReadingPane } from "@/components/reading-pane";

const { mockGetArtifactMarkdown } = vi.hoisted(() => ({
	mockGetArtifactMarkdown: vi.fn(),
}));

vi.mock("next/link", () => ({
	default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
		<a href={href} {...rest}>
			{children}
		</a>
	),
}));

vi.mock("@/components/markdown-preview", () => ({
	MarkdownPreview: ({ markdown }: { markdown: string }) => <div data-testid="markdown-preview">{markdown}</div>,
}));

vi.mock("@/lib/api/client", () => ({
	apiClient: {
		getArtifactMarkdown: (...args: unknown[]) => mockGetArtifactMarkdown(...args),
	},
}));

function createDeferred<T>() {
	let resolve!: (value: T) => void;
	let reject!: (reason?: unknown) => void;
	const promise = new Promise<T>((res, rej) => {
		resolve = res;
		reject = rej;
	});
	return { promise, resolve, reject };
}

describe("ReadingPane coverage", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("renders empty state when no job is selected", () => {
		render(<ReadingPane jobId={null} />);
		expect(screen.getByText("选择左侧条目查看摘要与正文")).toBeInTheDocument();
		expect(screen.getByText("视频与文章均支持 AI 摘要与大纲")).toBeInTheDocument();
		expect(mockGetArtifactMarkdown).not.toHaveBeenCalled();
	});

	it("renders loading then content state for selected job", async () => {
		const deferred = createDeferred<{ markdown: string; meta: Record<string, unknown> }>();
		mockGetArtifactMarkdown.mockReturnValueOnce(deferred.promise);

		render(<ReadingPane jobId="job-loading-1" title="加载测试" />);

		expect(await screen.findByText("加载中…")).toBeInTheDocument();
		expect(mockGetArtifactMarkdown).toHaveBeenCalledWith({
			job_id: "job-loading-1",
			include_meta: true,
		});

		deferred.resolve({
			markdown: "# Heading One\n\n正文内容",
			meta: {},
		});

		await waitFor(() => {
			expect(screen.getByTestId("markdown-preview")).toHaveTextContent("正文内容");
		});
	});

	it("renders friendly error state and supports in-place retry", async () => {
		mockGetArtifactMarkdown
			.mockRejectedValueOnce(new Error("network down"))
			.mockResolvedValueOnce({ markdown: "retry success", meta: {} });

		render(<ReadingPane jobId="job-error-1" />);

		expect(await screen.findByText("正文暂时不可用，请稍后重试。")).toBeInTheDocument();
		const retryButton = screen.getByRole("button", { name: "重试" });
		fireEvent.click(retryButton);

		await waitFor(() => {
			expect(mockGetArtifactMarkdown).toHaveBeenCalledTimes(2);
			expect(screen.getByTestId("markdown-preview")).toHaveTextContent("retry success");
		});
	});

	it("renders outline, metadata and safe external link", async () => {
		mockGetArtifactMarkdown.mockResolvedValueOnce({
			markdown: "# Heading One\n\n## Section 2!\n\nMain body",
			meta: {},
		});

		render(
			<ReadingPane
				jobId="job-heading-001"
				title="Digest Title"
				source="youtube"
				sourceName="Tech Channel"
				videoUrl="https://example.com/watch?v=1"
				publishedAt="2026-03-07T08:00:00Z"
				publishedDateLabel="昨天"
			/>,
		);

		expect(await screen.findByTestId("markdown-preview")).toHaveTextContent("Main body");
		expect(screen.getByText("YouTube · Tech Channel")).toBeInTheDocument();
		expect(screen.getByText("昨天")).toBeInTheDocument();
		expect(screen.getByRole("link", { name: /job-head/ })).toHaveAttribute(
			"href",
			"/jobs?job_id=job-heading-001",
		);
		expect(screen.getByRole("link", { name: "打开原文" })).toHaveAttribute(
			"href",
			"https://example.com/watch?v=1",
		);
		expect(screen.getByRole("link", { name: "Heading One" })).toHaveAttribute("href", "#heading-one");
		expect(screen.getByRole("link", { name: "Section 2!" })).toHaveAttribute("href", "#section-2");

		const outlineTrigger = screen.getByRole("button", { name: /大纲/ });
		expect(outlineTrigger).toHaveAttribute("data-state", "open");
		fireEvent.click(outlineTrigger);
		expect(outlineTrigger).toHaveAttribute("data-state", "closed");
	});

	it("renders fallback text and blocks unsafe external link", async () => {
		mockGetArtifactMarkdown.mockResolvedValueOnce({ markdown: "", meta: {} });

		render(
			<ReadingPane
				jobId="job-empty-1"
				title="No Body"
				source="rss_generic"
				videoUrl="javascript:alert(1)"
			/>,
		);

		expect(await screen.findByText("RSS")).toBeInTheDocument();
		expect(screen.queryByRole("link", { name: "打开原文" })).toBeNull();
		expect(screen.queryByRole("button", { name: /大纲/ })).toBeNull();
		expect(screen.getByText("无正文内容")).toBeInTheDocument();
	});

	it("maps bilibili source label", async () => {
		mockGetArtifactMarkdown.mockResolvedValueOnce({ markdown: "正文", meta: {} });
		render(<ReadingPane jobId="job-bili-1" source="bilibili" />);
		expect(await screen.findByText("Bilibili")).toBeInTheDocument();
	});

	it("keeps unknown source label as-is", async () => {
		mockGetArtifactMarkdown.mockResolvedValueOnce({ markdown: "正文", meta: {} });
		render(<ReadingPane jobId="job-custom-source" source="CustomSource" />);
		expect(await screen.findByText("CustomSource")).toBeInTheDocument();
	});
});
