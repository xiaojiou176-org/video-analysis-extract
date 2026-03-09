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

class ResizeObserverMock {
	observe() {}
	unobserve() {}
	disconnect() {}
}

vi.stubGlobal("ResizeObserver", ResizeObserverMock);

describe("dashboard/settings/subscriptions pages", () => {
	const PAGE_TEST_TIMEOUT_MS = 15000;

	beforeEach(() => {
		vi.clearAllMocks();
	});

	it(
		"renders dashboard metrics, table rows and failure CTA",
		async () => {
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

			render(await DashboardPage({ searchParams: {} }));
			expect(document.querySelector(".folo-page-shell")).not.toBeNull();
			expect(document.querySelectorAll('[data-slot="card"]').length).toBeGreaterThanOrEqual(7);

			const metricRegion = screen.getByRole("region", { name: "关键指标" });
			const metrics = Array.from(metricRegion.querySelectorAll('[data-slot="card"]'));
			expect(metrics).toHaveLength(4);
			expect(within(metrics[0] as HTMLElement).getByText("2")).toBeInTheDocument();
			expect(within(metrics[1] as HTMLElement).getByText("3")).toBeInTheDocument();
			expect(within(metrics[2] as HTMLElement).getByText("2")).toBeInTheDocument();
			expect(within(metrics[3] as HTMLElement).getByText("1")).toBeInTheDocument();
				expect(screen.getByRole("link", { name: "查看失败任务 →" })).toHaveAttribute("href", "/jobs");

			const recentVideoTable = screen.getByRole("table");
			expect(within(recentVideoTable).getByText("最近视频列表")).toBeInTheDocument();
			expect(within(recentVideoTable).getByText("标题").tagName).toBe("TH");
			expect(within(recentVideoTable).getByText("标题")).toHaveAttribute("scope", "col");
			expect(within(recentVideoTable).getByText("YouTube")).toBeInTheDocument();
			expect(within(recentVideoTable).getByText("Bilibili")).toBeInTheDocument();
			expect(within(recentVideoTable).getByText("rss_generic")).toBeInTheDocument();
			expect(within(recentVideoTable).getByText("运行中")).toBeInTheDocument();
			expect(within(recentVideoTable).getByText("排队中")).toBeInTheDocument();
			expect(within(recentVideoTable).getByText("已失败")).toBeInTheDocument();

			expect(screen.getByRole("link", { name: "job-111" })).toHaveAttribute(
				"href",
				"/jobs?job_id=job-111",
			);
			expect(screen.getByRole("link", { name: "job-333" })).toHaveAttribute(
				"href",
				"/jobs?job_id=job-333",
			);

				const pollForm = screen.getByRole("button", { name: "触发采集" }).closest("form");
				expect(pollForm).not.toBeNull();
				expect(pollForm).not.toHaveAttribute("method");
				expect(
					(pollForm as HTMLElement).querySelector('input[type="hidden"][name="platform"]'),
				).toHaveValue("");
				expect(within(pollForm as HTMLElement).getByRole("spinbutton", { name: "最多拉取视频数" })).toHaveValue(
					50,
				);
			expect((pollForm as HTMLElement).querySelector('input[type="hidden"][name="session_token"]')).toHaveValue(
				"test-session-token",
			);
				expect(within(pollForm as HTMLElement).getByRole("button", { name: "触发采集" })).toHaveAttribute(
					"type",
					"submit",
				);
				expect(screen.getByRole("link", { name: "查看任务队列 →" })).toHaveAttribute("href", "/jobs");

				const processForm = screen.getByRole("button", { name: "开始处理" }).closest("form");
				expect(processForm).not.toBeNull();
				expect(processForm).toHaveAttribute("data-auto-disable-required", "true");
				expect(processForm).not.toHaveAttribute("method");
				expect(
					(processForm as HTMLElement).querySelector('input[type="hidden"][name="platform"]'),
				).toHaveValue("youtube");
				expect(within(processForm as HTMLElement).getByRole("textbox", { name: "视频链接 *" })).toBeRequired();
				expect(
					(processForm as HTMLElement).querySelector('input[type="hidden"][name="mode"]'),
				).toHaveValue("full");
				expect(within(processForm as HTMLElement).getByRole("checkbox", { name: "强制执行" })).not.toBeChecked();
			expect((processForm as HTMLElement).querySelector('input[type="hidden"][name="session_token"]')).toHaveValue(
				"test-session-token",
			);
				expect(within(processForm as HTMLElement).getByRole("button", { name: "开始处理" })).toHaveAttribute(
					"type",
					"submit",
				);
				expect(screen.getByRole("link", { name: "查看任务详情 →" })).toHaveAttribute("href", "/jobs");
				expect(screen.getByRole("link", { name: "查看全部任务 →" })).toHaveAttribute("href", "/jobs");
		},
		PAGE_TEST_TIMEOUT_MS,
	);

	it(
		"renders dashboard load error and empty fallback copy",
		async () => {
			mockListSubscriptions.mockRejectedValue(new Error("network failed"));
			mockListVideos.mockRejectedValue(new Error("network failed"));

			render(await DashboardPage({ searchParams: {} }));

			expect(screen.getByRole("alert")).toHaveTextContent("请求失败，请稍后重试。");
			expect(screen.getByRole("link", { name: "重试当前页面" })).toHaveAttribute("href", "/");
			expect(screen.getByText("当前无法加载视频列表。")).toBeInTheDocument();
			expect(screen.getAllByText("数据暂不可用")).toHaveLength(4);

			const metricRegion = screen.getByRole("region", { name: "关键指标" });
			const metrics = Array.from(metricRegion.querySelectorAll('[data-slot="card"]'));
			expect(metrics).toHaveLength(4);
			for (const metric of metrics) {
				expect(within(metric as HTMLElement).getByText(/--/)).toBeInTheDocument();
				expect(within(metric as HTMLElement).queryByText("0")).not.toBeInTheDocument();
			}
		},
		PAGE_TEST_TIMEOUT_MS,
	);

	it(
		"renders dashboard flash success from search params",
		async () => {
			mockListSubscriptions.mockResolvedValue([]);
			mockListVideos.mockResolvedValue([]);

			render(await DashboardPage({ searchParams: { status: "success", code: "POLL_INGEST_OK" } }));

			const successFlash = screen.getByText("已触发采集任务。").closest('[role="status"]');
			expect(successFlash).not.toBeNull();
			expect(successFlash).toHaveAttribute("role", "status");
			expect(successFlash).toHaveAttribute("role", "status");
				expect(screen.getByRole("link", { name: "添加第一个订阅 →" })).toHaveAttribute("href", "/subscriptions");
			expect(screen.getByText("暂无视频。")).toBeInTheDocument();
		},
		PAGE_TEST_TIMEOUT_MS,
	);

	it(
		"renders subscriptions page list and batch panel",
		async () => {
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
				expect(screen.getByRole("combobox", { name: "平台" })).toHaveTextContent("YouTube");
				expect(screen.getByRole("combobox", { name: "来源类型" })).toHaveTextContent("来源链接（URL）");
				expect(screen.getByLabelText("来源值")).toBeRequired();
				expect(screen.getByRole("combobox", { name: "适配器类型" })).toHaveTextContent("RSSHub 路由");
				expect(screen.getByRole("combobox", { name: "分类" })).toHaveTextContent("其他");
				expect(screen.getByLabelText("优先级 (0-100)")).toHaveValue(50);
				expect(screen.getByRole("checkbox", { name: "启用" })).toBeChecked();

				const subscriptionsForm = screen.getByRole("button", { name: "保存订阅" }).closest("form");
				expect(subscriptionsForm).not.toBeNull();
				expect(subscriptionsForm).toHaveAttribute("data-auto-disable-required", "true");
				expect(subscriptionsForm).not.toHaveAttribute("method");
				expect(
					(subscriptionsForm as HTMLElement).querySelector('input[type="hidden"][name="platform"]'),
				).toHaveValue("youtube");
				expect(
					(subscriptionsForm as HTMLElement).querySelector('input[type="hidden"][name="source_type"]'),
				).toHaveValue("url");
				expect(
					(subscriptionsForm as HTMLElement).querySelector('input[type="hidden"][name="adapter_type"]'),
				).toHaveValue("rsshub_route");
				expect(
					(subscriptionsForm as HTMLElement).querySelector('input[type="hidden"][name="category"]'),
				).toHaveValue("misc");
				expect(
					(subscriptionsForm as HTMLElement).querySelector('input[type="hidden"][name="session_token"]'),
				).toHaveValue("test-session-token");
			expect(within(subscriptionsForm as HTMLElement).getByRole("button", { name: "保存订阅" })).toHaveAttribute(
				"type",
				"submit",
			);
		},
		PAGE_TEST_TIMEOUT_MS,
	);

	it(
		"renders settings page config values and load failure message",
		async () => {
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

			expect(screen.getByText("通知配置已保存。")).toBeInTheDocument();
			expect(screen.getByLabelText("收件人邮箱")).toHaveValue("ops@example.com");
			expect(screen.getByRole("checkbox", { name: "启用通知" })).toBeChecked();
			expect(screen.getByRole("checkbox", { name: "启用每日摘要" })).toBeChecked();
			expect(screen.getByRole("spinbutton", { name: "每日摘要发送时间（UTC 小时）" })).toHaveValue(8);
			expect(screen.getByRole("spinbutton", { name: "每日摘要发送时间（UTC 小时）" })).toBeEnabled();
			expect(screen.getByRole("checkbox", { name: "启用失败告警" })).toBeChecked();
			expect(
				screen.getByText(
					/本地时间预览：本字段使用 UTC 小时。换算公式为「本地时间 = UTC 时间 \+ 时区偏移」。\s*例如 UTC\+8 用户可将本地目标小时减 8 后填写（如本地 09:00 → UTC 01:00）。/,
				),
			).toBeInTheDocument();
			expect(screen.getByText("当前默认收件人：ops@example.com")).toBeInTheDocument();
			expect(screen.getByRole("button", { name: "发送测试邮件" })).toBeInTheDocument();

			const configForm = screen.getByRole("button", { name: "保存配置" }).closest("form");
			expect(configForm).not.toBeNull();
			expect(configForm).not.toHaveAttribute("method");
			expect((configForm as HTMLElement).querySelector('input[type="hidden"][name="session_token"]')).toHaveValue(
				"test-session-token",
			);
			expect(within(configForm as HTMLElement).getByRole("button", { name: "保存配置" })).toHaveAttribute(
				"type",
				"submit",
			);

			const sendTestForm = screen.getByRole("button", { name: "发送测试邮件" }).closest("form");
			expect(sendTestForm).not.toBeNull();
			expect(sendTestForm).not.toHaveAttribute("method");
			expect((sendTestForm as HTMLElement).querySelector('input[type="hidden"][name="session_token"]')).toHaveValue(
				"test-session-token",
			);
			expect(within(sendTestForm as HTMLElement).getByRole("button", { name: "发送测试邮件" })).toHaveAttribute(
				"type",
				"submit",
			);
		},
		PAGE_TEST_TIMEOUT_MS,
	);

	it(
		"renders settings load error fallback when API fails",
		async () => {
			mockGetNotificationConfig.mockRejectedValue(new Error("boom"));

			render(await SettingsPage({ searchParams: {} }));

			expect(screen.getByRole("alert")).toHaveTextContent("请求失败，请稍后重试。");
			expect(screen.getByRole("link", { name: "重试当前页面" })).toHaveAttribute(
				"href",
				"/settings",
			);
			expect(screen.getByRole("button", { name: "保存配置" })).toBeInTheDocument();
			expect(screen.getByRole("checkbox", { name: "启用通知" })).toBeChecked();
			expect(screen.getByRole("checkbox", { name: "启用每日摘要" })).not.toBeChecked();
			expect(screen.getByRole("spinbutton", { name: "每日摘要发送时间（UTC 小时）" })).toBeDisabled();
			expect(screen.getByRole("checkbox", { name: "启用失败告警" })).toBeChecked();
		},
		PAGE_TEST_TIMEOUT_MS,
	);

	it(
		"renders subscriptions load error with retry link when API fails",
		async () => {
			mockListSubscriptions.mockRejectedValue(new Error("boom"));

			render(await SubscriptionsPage({ searchParams: {} }));

			expect(screen.getByRole("alert")).toHaveTextContent("请求失败，请稍后重试。");
			expect(screen.getByRole("link", { name: "重试当前页面" })).toHaveAttribute(
				"href",
				"/subscriptions",
			);
			expect(screen.getByRole("button", { name: "保存订阅" })).toBeInTheDocument();
		},
		PAGE_TEST_TIMEOUT_MS,
	);
});
