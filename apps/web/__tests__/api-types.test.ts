import { describe, expect, expectTypeOf, it } from "vitest";

import type {
	DigestFeedResponse,
	NotificationConfigUpdateRequest,
	Subscription,
	VideoProcessMode,
	VideoProcessResponse,
} from "@/lib/api/types";

describe("api type contracts", () => {
	it("keeps subscription and notification request contracts", () => {
		const subscription: Subscription = {
			id: "sub-1",
			platform: "youtube",
			source_type: "channel",
			source_value: "UC123",
			source_name: "Test",
			adapter_type: "youtube_channel",
			source_url: null,
			rsshub_route: "",
			category: "tech",
			tags: ["ai"],
			priority: 80,
			enabled: true,
			created_at: "2026-02-01T00:00:00Z",
			updated_at: "2026-02-01T00:00:00Z",
		};

		const update: NotificationConfigUpdateRequest = {
			enabled: true,
			to_email: "a@example.com",
			daily_digest_enabled: true,
			daily_digest_hour_utc: 8,
			failure_alert_enabled: false,
			category_rules: { tech: true },
		};

		expectTypeOf(subscription.category).toEqualTypeOf<
			"tech" | "creator" | "macro" | "ops" | "misc"
		>();
		expectTypeOf(update.daily_digest_hour_utc).toEqualTypeOf<number | null>();
		expect(subscription.source_type).toBe("channel");
		expect(update.enabled).toBe(true);
	});

	it("keeps process response and digest feed contracts", () => {
		const processResponse: VideoProcessResponse = {
			job_id: "job-1",
			video_db_id: "video-db-1",
			video_uid: "uid-1",
			status: "queued",
			idempotency_key: "idem",
			mode: "full",
			overrides: {},
			force: false,
			reused: false,
			workflow_id: null,
		};

		const feed: DigestFeedResponse = {
			items: [],
			has_more: false,
			next_cursor: null,
		};

		expectTypeOf(processResponse.mode).toEqualTypeOf<VideoProcessMode>();
		expectTypeOf(feed.items).toEqualTypeOf<Array<DigestFeedResponse["items"][number]>>();
		expect(processResponse.status).toBe("queued");
		expect(feed.has_more).toBe(false);
	});
});
