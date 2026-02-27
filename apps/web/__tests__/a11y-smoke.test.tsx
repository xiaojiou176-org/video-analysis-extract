import { render } from "@testing-library/react";
import { axe } from "jest-axe";
import { beforeEach, describe, expect, it, vi } from "vitest";

import DashboardPage from "@/app/page";
import JobsPage from "@/app/jobs/page";
import SettingsPage from "@/app/settings/page";
import SubscriptionsPage from "@/app/subscriptions/page";

const mockListSubscriptions = vi.fn();
const mockListVideos = vi.fn();
const mockGetJob = vi.fn();
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
		getJob: (...args: unknown[]) => mockGetJob(...args),
		getNotificationConfig: (...args: unknown[]) => mockGetNotificationConfig(...args),
	},
}));

describe("a11y smoke", () => {
	beforeEach(() => {
		vi.clearAllMocks();
		mockListSubscriptions.mockResolvedValue([]);
		mockListVideos.mockResolvedValue([]);
		mockGetNotificationConfig.mockResolvedValue({
			enabled: true,
			to_email: "ops@example.com",
			daily_digest_enabled: false,
			daily_digest_hour_utc: null,
			failure_alert_enabled: true,
			category_rules: {},
			created_at: "2026-02-01T00:00:00Z",
			updated_at: "2026-02-02T00:00:00Z",
		});
		mockGetJob.mockResolvedValue({
			id: "job-1",
			video_id: "video-1",
			status: "running",
			created_at: "2026-02-01T00:00:00Z",
			updated_at: "2026-02-01T00:00:10Z",
			pipeline_final_status: "running",
			step_summary: [],
			degradations: [],
			artifacts_index: {},
		});
	});

	it("dashboard/subscriptions/settings/jobs pages have no critical accessibility violations", async () => {
		const dashboard = render(await DashboardPage({ searchParams: {} }));
		const dashboardResults = await axe(dashboard.container);
		expect(dashboardResults.violations).toHaveLength(0);

		const subscriptions = render(await SubscriptionsPage({ searchParams: {} }));
		const subscriptionsResults = await axe(subscriptions.container);
		expect(subscriptionsResults.violations).toHaveLength(0);

		const settings = render(await SettingsPage({ searchParams: {} }));
		const settingsResults = await axe(settings.container);
		expect(settingsResults.violations).toHaveLength(0);

		const jobs = render(await JobsPage({ searchParams: { job_id: "job-1" } }));
		const jobsResults = await axe(jobs.container);
		expect(jobsResults.violations).toHaveLength(0);
	});
});
