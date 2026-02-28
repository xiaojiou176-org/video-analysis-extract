import { render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "@/app/page";
import SettingsPage from "@/app/settings/page";
import SubscriptionsPage from "@/app/subscriptions/page";

const mockListSubscriptions = vi.fn();
const mockListVideos = vi.fn();
const mockGetNotificationConfig = vi.fn();

vi.mock("next/link", () => ({
	default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
		<a href={href} {...rest}>
			{children}
		</a>
	),
}));

vi.mock("@/app/action-security", () => ({
	getActionSessionTokenForForm: () => "test-session-token",
}));

vi.mock("@/components/subscription-batch-panel", () => ({
	SubscriptionBatchPanel: ({ subscriptions }: { subscriptions: Array<{ id: string }> }) => (
		<div data-testid="subscription-batch-panel">count:{subscriptions.length}</div>
	),
}));

vi.mock("@/lib/api/client", () => ({
	apiClient: {
		listSubscriptions: (...args: unknown[]) => mockListSubscriptions(...args),
		listVideos: (...args: unknown[]) => mockListVideos(...args),
		getNotificationConfig: (...args: unknown[]) => mockGetNotificationConfig(...args),
	},
}));

describe("dashboard/settings/subscriptions pages", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	it("renders dashboard metrics, table rows and failure CTA", async () => {
		mockListSubscriptions.mockResolvedValue([{ id: "sub-1" }, { id: "sub-2" }]);
		mockListVideos.mockResolvedValue([
			{
				id: "v1",
				platform: "youtube",
				video_uid: "yt-1",
				source_url: "https://example.com/1",
				title: "Video One",
				published_at: null,
				first_seen_at: "2026-02-01T00:00:00Z",
				last_seen_at: "2026-02-01T00:00:00Z",
				status: "running",
				last_job_id: "job-111",
			},
			{
				id: "v2",
				platform: "bilibili",
				video_uid: "bb-2",
				source_url: "https://example.com/2",
				title: null,
				published_at: null,
				first_seen_at: "2026-02-01T00:00:00Z",
				last_seen_at: "2026-02-01T00:00:00Z",
				status: "failed",
				last_job_id: null,
			},
			{
				id: "v3",
				platform: "rss_generic",
				video_uid: "rss-3",
				source_url: "https://example.com/3",
				title: "Video Three",
				published_at: null,
				first_seen_at: "2026-02-01T00:00:00Z",
				last_seen_at: "2026-02-01T00:00:00Z",
				status: "queued",
				last_job_id: "job-333",
			},
		]);

		const { container } = render(await DashboardPage({ searchParams: {} }));

		const metrics = Array.from(container.querySelectorAll(".card.metric"));
		expect(metrics).toHaveLength(4);
		expect(within(metrics[0] as HTMLElement).getByText("2")).toBeInTheDocument();
		expect(within(metrics[1] as HTMLElement).getByText("3")).toBeInTheDocument();
		expect(within(metrics[2] as HTMLElement).getByText("2")).toBeInTheDocument();
		expect(within(metrics[3] as HTMLElement).getByText("1")).toBeInTheDocument();
		expect(screen.getByRole("link", { name: "查看失败任务，前往任务列表" })).toHaveAttribute(
			"href",
			"/jobs",
		);

		const recentVideoTable = screen.getByRole("table");
		expect(within(recentVideoTable).getByText("最近视频列表")).toBeInTheDocument();
		expect(within(recentVideoTable).getByText("标题").tagName).toBe("TH");
		expect(within(recentVideoTable).getByText("标题")).toHaveAttribute("scope", "col");
		expect(within(recentVideoTable).getByText("YouTube")).toBeInTheDocument();
		expect(within(recentVideoTable).getByText("Bilibili")).toBeInTheDocument();
		expect(within(recentVideoTable).getByText("rss_generic")).toBeInTheDocument();

		expect(screen.getByRole("link", { name: "job-111" })).toHaveAttribute(
			"href",
			"/jobs?job_id=job-111",
		);
		expect(screen.getByRole("link", { name: "job-333" })).toHaveAttribute(
			"href",
			"/jobs?job_id=job-333",
		);
	});

	it("renders dashboard load error and empty fallback copy", async () => {
		mockListSubscriptions.mockRejectedValue(new Error("network failed"));
		mockListVideos.mockRejectedValue(new Error("network failed"));

		render(await DashboardPage({ searchParams: {} }));

		expect(screen.getByRole("alert")).toHaveTextContent("请求失败，请稍后重试。");
		expect(screen.getByText("当前无法加载视频列表。")).toBeInTheDocument();
	});

	it("renders dashboard flash success from search params", async () => {
		mockListSubscriptions.mockResolvedValue([]);
		mockListVideos.mockResolvedValue([]);

		render(await DashboardPage({ searchParams: { status: "success", code: "POLL_INGEST_OK" } }));

		expect(screen.getByText("已触发采集任务。")).toBeInTheDocument();
		expect(screen.getByRole("link", { name: "添加第一个订阅，前往订阅管理" })).toHaveAttribute(
			"href",
			"/subscriptions",
		);
		expect(screen.getByText("暂无视频。")).toBeInTheDocument();
	});

	it("renders subscriptions page list and batch panel", async () => {
		mockListSubscriptions.mockResolvedValue([
			{
				id: "sub-1",
				source_name: "channel-1",
				source_value: "value",
				rsshub_route: "",
				platform: "youtube",
				source_type: "url",
				adapter_type: "rsshub_route",
				source_url: null,
				category: "tech",
				tags: [],
				priority: 50,
				enabled: true,
				created_at: "2026-02-01T00:00:00Z",
				updated_at: "2026-02-01T00:00:00Z",
			},
		]);

		render(
			await SubscriptionsPage({ searchParams: { status: "error", code: "ERR_INVALID_INPUT" } }),
		);

		expect(screen.getByRole("alert")).toHaveTextContent("输入参数不合法，请检查后重试。");
		expect(screen.getByTestId("subscription-batch-panel")).toHaveTextContent("count:1");
		expect(screen.getByRole("button", { name: "保存订阅" })).toBeInTheDocument();
	});

	it("renders settings page config values and load failure message", async () => {
		mockGetNotificationConfig.mockResolvedValue({
			enabled: true,
			to_email: "ops@example.com",
			daily_digest_enabled: true,
			daily_digest_hour_utc: 8,
			failure_alert_enabled: true,
			category_rules: {},
			created_at: "2026-02-01T00:00:00Z",
			updated_at: "2026-02-02T00:00:00Z",
		});

		render(
			await SettingsPage({
				searchParams: { status: "success", code: "NOTIFICATION_CONFIG_SAVED" },
			}),
		);

		expect(screen.getByRole("status")).toHaveTextContent("通知配置已保存。");
		expect(screen.getByDisplayValue("ops@example.com")).toBeInTheDocument();
		expect(screen.getByDisplayValue("8")).toBeInTheDocument();
		expect(screen.getByRole("button", { name: "发送测试邮件" })).toBeInTheDocument();
	});

	it("renders settings load error fallback when API fails", async () => {
		mockGetNotificationConfig.mockRejectedValue(new Error("boom"));

		render(await SettingsPage({ searchParams: {} }));

		expect(screen.getByRole("alert")).toHaveTextContent("请求失败，请稍后重试。");
		expect(screen.getByRole("button", { name: "保存配置" })).toBeInTheDocument();
	});
});
