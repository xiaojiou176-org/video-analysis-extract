import { cleanup, render } from "@testing-library/react";
import { axe } from "jest-axe";
import { beforeEach, describe, expect, it, vi } from "vitest";
import FeedPage from "@/app/feed/page";
import JobsPage from "@/app/jobs/page";
import DashboardPage from "@/app/page";
import SettingsPage from "@/app/settings/page";
import SubscriptionsPage from "@/app/subscriptions/page";

const mockListSubscriptions = vi.fn();
const mockListVideos = vi.fn();
const mockGetJob = vi.fn();
const mockGetDigestFeed = vi.fn();
const mockGetArtifactMarkdown = vi.fn();
const mockGetNotificationConfig = vi.fn();

vi.mock("next/link", () => ({
	default: ({ href, children, ...rest }: { href: string; children: React.ReactNode }) => (
		<a href={href} {...rest}>
			{children}
		</a>
	),
}));

vi.mock("next/navigation", () => ({
	useRouter: () => ({ refresh: vi.fn(), replace: vi.fn() }),
}));

vi.mock("@/app/action-security", () => ({
	getActionSessionTokenForForm: () => "test-session-token",
}));

vi.mock("@/lib/api/client", () => ({
	apiClient: {
		listSubscriptions: (...args: unknown[]) => mockListSubscriptions(...args),
		listVideos: (...args: unknown[]) => mockListVideos(...args),
		getJob: (...args: unknown[]) => mockGetJob(...args),
		getDigestFeed: (...args: unknown[]) => mockGetDigestFeed(...args),
		getArtifactMarkdown: (...args: unknown[]) => mockGetArtifactMarkdown(...args),
		getNotificationConfig: (...args: unknown[]) => mockGetNotificationConfig(...args),
		pollIngest: vi.fn(),
		deleteSubscription: vi.fn(),
		batchUpdateSubscriptionCategory: vi.fn(),
	},
}));

describe("a11y smoke", () => {
	const A11Y_TIMEOUT_MS = 60000;

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
		mockGetDigestFeed.mockResolvedValue({
			items: [
				{
					feed_id: "feed-1",
					job_id: "job-1",
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
			has_more: false,
			next_cursor: null,
		});
		mockGetArtifactMarkdown.mockResolvedValue({
			markdown: "# artifact",
			meta: {
				frame_files: [],
				job: { id: "job-1" },
			},
		});
	});

	it(
		"dashboard/subscriptions/settings/feed/jobs pages have no critical accessibility violations",
		async () => {
			const dashboard = render(await DashboardPage({ searchParams: {} }));
			const dashboardResults = await axe(dashboard.container);
			expect(dashboardResults.violations).toHaveLength(0);
			dashboard.unmount();
			cleanup();

			const subscriptions = render(await SubscriptionsPage({ searchParams: {} }));
			const subscriptionsResults = await axe(subscriptions.container);
			expect(subscriptionsResults.violations).toHaveLength(0);
			subscriptions.unmount();
			cleanup();

			const settings = render(await SettingsPage({ searchParams: {} }));
			const settingsResults = await axe(settings.container);
			expect(settingsResults.violations).toHaveLength(0);
			settings.unmount();
			cleanup();

			const jobs = render(await JobsPage({ searchParams: { job_id: "job-1" } }));
			const jobsResults = await axe(jobs.container);
			expect(jobsResults.violations).toHaveLength(0);
			jobs.unmount();
			cleanup();

			const feed = render(await FeedPage({ searchParams: {} }));
			const feedResults = await axe(feed.container);
			expect(feedResults.violations).toHaveLength(0);
			feed.unmount();
			cleanup();
		},
		A11Y_TIMEOUT_MS,
	);
});
