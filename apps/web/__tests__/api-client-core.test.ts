import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/lib/api/client";

describe("apiClient core behavior", () => {
	const envSnapshot = { ...process.env };

	beforeEach(() => {
		process.env = { ...envSnapshot, NEXT_PUBLIC_API_BASE_URL: "https://api.example.com" };
	});

	afterEach(() => {
		process.env = { ...envSnapshot };
		vi.restoreAllMocks();
	});

	it("maps auth errors to ERR_AUTH_REQUIRED", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("denied", { status: 401 }));

		await expect(apiClient.listVideos()).rejects.toThrow("ERR_AUTH_REQUIRED");
	});

	it("maps bad request to ERR_INVALID_INPUT", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("bad", { status: 400 }));

		await expect(apiClient.sendNotificationTest({ subject: "x" })).rejects.toThrow(
			"ERR_INVALID_INPUT",
		);
	});

	it("maps unprocessable entity to ERR_INVALID_INPUT", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue(
			new Response(JSON.stringify({ detail: "validation failed" }), { status: 422 }),
		);

		await expect(apiClient.sendNotificationTest({ subject: "x" })).rejects.toThrow(
			"ERR_INVALID_INPUT",
		);
	});

	it("maps server errors and not found to ERR_REQUEST_FAILED", async () => {
		const fetchSpy = vi
			.spyOn(globalThis, "fetch")
			.mockResolvedValueOnce(new Response("missing", { status: 404 }))
			.mockResolvedValueOnce(new Response("oops", { status: 503 }));

		await expect(apiClient.getNotificationConfig()).rejects.toThrow("ERR_REQUEST_FAILED");
		await expect(apiClient.getNotificationConfig()).rejects.toThrow("ERR_REQUEST_FAILED");
		expect(fetchSpy).toHaveBeenCalledTimes(2);
	});

	it("throws ERR_PROTOCOL_EMPTY_BODY for 200 responses with empty body", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(null, { status: 200 }));

		await expect(apiClient.getNotificationConfig()).rejects.toThrow("ERR_PROTOCOL_EMPTY_BODY");
	});

	it("sends JSON payload with no-store caching", async () => {
		const fetchSpy = vi
			.spyOn(globalThis, "fetch")
			.mockResolvedValue(
				new Response(JSON.stringify({ enqueued: 0, candidates: [] }), { status: 200 }),
			);

		await apiClient.pollIngest({ max_new_videos: 20 });

		const [, options] = fetchSpy.mock.calls[0];
		expect(options).toMatchObject({
			method: "POST",
			cache: "no-store",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ max_new_videos: 20 }),
		});
	});

	it("normalizes malformed job payload arrays and maps", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue(
			new Response(
				JSON.stringify({
					id: "job-1",
					video_id: "video-1",
					kind: "video_digest_v1",
					status: "running",
					idempotency_key: "idem-1",
					error_message: null,
					artifact_digest_md: null,
					artifact_root: null,
					llm_required: null,
					llm_gate_passed: null,
					hard_fail_reason: null,
					created_at: "2026-02-26T00:00:00Z",
					updated_at: "2026-02-26T00:00:00Z",
					step_summary: null,
					steps: "broken",
					degradations: { x: 1 },
					pipeline_final_status: null,
					artifacts_index: { digest: "a.md", bad: 123 },
					mode: undefined,
					notification_retry: undefined,
				}),
				{ status: 200 },
			),
		);

		const job = await apiClient.getJob("job-1");
		expect(job.step_summary).toEqual([]);
		expect(job.steps).toEqual([]);
		expect(job.degradations).toEqual([]);
		expect(job.artifacts_index).toEqual({ digest: "a.md" });
		expect(job.mode).toBeNull();
		expect(job.notification_retry).toBeNull();
	});

	it("supports plain text artifact markdown endpoint", async () => {
		const fetchSpy = vi
			.spyOn(globalThis, "fetch")
			.mockResolvedValue(new Response("# hello", { status: 200 }));

		await expect(apiClient.getArtifactMarkdown({ job_id: "job-1" })).resolves.toBe("# hello");
		const [url] = fetchSpy.mock.calls[0];
		expect(String(url)).toContain("/api/v1/artifacts/markdown");
		expect(String(url)).toContain("job_id=job-1");
	});

	it("maps network errors to ERR_REQUEST_FAILED for text endpoints", async () => {
		vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("network down"));

		await expect(apiClient.getArtifactMarkdown({ job_id: "job-1" })).rejects.toThrow(
			"ERR_REQUEST_FAILED",
		);
	});

	it("preserves local query validation error code from buildApiUrl", async () => {
		const fetchSpy = vi.spyOn(globalThis, "fetch");

		await expect(
			apiClient.getDigestFeed({
				limit: 20,
				session_token: "abc",
			} as unknown as Parameters<typeof apiClient.getDigestFeed>[0]),
		).rejects.toThrow("ERR_SENSITIVE_QUERY_KEY:session_token");
		expect(fetchSpy).not.toHaveBeenCalled();
	});

	it("normalizes malformed feed payload to keep page rendering safe", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue(
			new Response(
				JSON.stringify({
					items: [
						null,
						{
							feed_id: "feed-1",
							job_id: "job-1",
							video_url: 1,
							title: null,
							source: "youtube",
							source_name: null,
							category: "",
							published_at: 123,
							summary_md: { x: 1 },
							artifact_type: "unknown",
						},
						{ feed_id: "", job_id: "missing" },
					],
						has_more: "unknown",
					next_cursor: 123,
				}),
				{ status: 200 },
			),
		);

		const feed = await apiClient.getDigestFeed();
		expect(feed.has_more).toBe(false);
		expect(feed.next_cursor).toBeNull();
		expect(feed.items).toEqual([
			{
				feed_id: "feed-1",
				job_id: "job-1",
				video_url: "",
				title: "",
				source: "youtube",
				source_name: "",
				category: "misc",
				published_at: "",
				summary_md: "",
				artifact_type: "digest",
			},
		]);
	});

	it("normalizes artifact markdown meta response shape", async () => {
		vi.spyOn(globalThis, "fetch").mockResolvedValue(
			new Response(JSON.stringify({ markdown: 1, meta: [] }), { status: 200 }),
		);

		await expect(
			apiClient.getArtifactMarkdown({ job_id: "job-1", include_meta: true }),
		).resolves.toEqual({
			markdown: "",
			meta: null,
		});
	});

	it("covers additional client endpoints with query/body wiring", async () => {
		const fetchSpy = vi
			.spyOn(globalThis, "fetch")
			.mockResolvedValueOnce(
				new Response(
					JSON.stringify({
						job_id: "job-2",
						video_db_id: "video-2",
						video_uid: "uid-2",
						status: "queued",
						idempotency_key: "idem-2",
						mode: "full",
						overrides: {},
						force: false,
						reused: false,
						workflow_id: null,
					}),
					{ status: 200 },
				),
			)
			.mockResolvedValueOnce(
				new Response(
					JSON.stringify({
						enabled: true,
						to_email: "a@example.com",
						daily_digest_enabled: false,
						daily_digest_hour_utc: null,
						failure_alert_enabled: true,
						category_rules: {},
						created_at: "2026-02-26T00:00:00Z",
						updated_at: "2026-02-26T00:00:00Z",
					}),
					{ status: 200 },
				),
			)
			.mockResolvedValueOnce(
				new Response(JSON.stringify({ items: [], has_more: false, next_cursor: null }), {
					status: 200,
				}),
			);

		await apiClient.processVideo({
			video: { platform: "youtube", url: "https://example.com/v/1" },
			force: false,
		});
		await apiClient.updateNotificationConfig({
			enabled: true,
			to_email: "a@example.com",
			daily_digest_enabled: false,
			daily_digest_hour_utc: null,
			failure_alert_enabled: true,
			category_rules: {},
		});
		await apiClient.getDigestFeed({ source: "youtube", limit: 20 });

		expect(fetchSpy).toHaveBeenCalledTimes(3);
		const [processUrl, processOpts] = fetchSpy.mock.calls[0];
		expect(String(processUrl)).toContain("/api/v1/videos/process");
		expect(processOpts).toMatchObject({ method: "POST" });

		const [feedUrl] = fetchSpy.mock.calls[2];
		expect(String(feedUrl)).toContain("/api/v1/feed/digests");
		expect(String(feedUrl)).toContain("source=youtube");
		expect(String(feedUrl)).toContain("limit=20");
	});

	it("covers subscription endpoints and artifact markdown error path", async () => {
		const fetchSpy = vi
			.spyOn(globalThis, "fetch")
			.mockResolvedValueOnce(
				new Response(
					JSON.stringify([
						{
							id: "sub-1",
							platform: "youtube",
							source_type: "url",
							source_value: "https://www.youtube.com/@x",
							adapter_type: "rsshub_route",
							source_url: null,
							rsshub_route: "/youtube/channel/abc",
							category: "tech",
							tags: [],
							priority: 50,
							enabled: true,
							created_at: "2026-02-01T00:00:00Z",
							updated_at: "2026-02-01T00:00:00Z",
						},
					]),
					{ status: 200 },
				),
			)
			.mockResolvedValueOnce(
				new Response(JSON.stringify({ ok: true, subscription_id: "sub-1", action: "created" }), {
					status: 200,
				}),
			)
			.mockResolvedValueOnce(new Response(JSON.stringify({ updated: 1 }), { status: 200 }))
			.mockResolvedValueOnce(new Response(null, { status: 204 }))
			.mockResolvedValueOnce(new Response("server down", { status: 503 }));

		await apiClient.listSubscriptions({ platform: "youtube", enabled_only: true });
		await apiClient.upsertSubscription({
			platform: "youtube",
			source_type: "url",
			source_value: "https://www.youtube.com/@x",
			adapter_type: "rsshub_route",
			category: "tech",
		});
		await apiClient.batchUpdateSubscriptionCategory({ ids: ["sub-1"], category: "creator" });
		await apiClient.deleteSubscription("sub-1");
		await expect(apiClient.getArtifactMarkdown({ job_id: "job-2" })).rejects.toThrow(
			"ERR_REQUEST_FAILED",
		);

		expect(fetchSpy).toHaveBeenCalledTimes(5);
		expect(String(fetchSpy.mock.calls[0][0])).toContain("/api/v1/subscriptions");
		expect(String(fetchSpy.mock.calls[0][0])).toContain("platform=youtube");
		expect(String(fetchSpy.mock.calls[0][0])).toContain("enabled_only=true");
		expect(fetchSpy.mock.calls[1][1]).toMatchObject({ method: "POST" });
		expect(String(fetchSpy.mock.calls[3][0])).toContain("/api/v1/subscriptions/sub-1");
		expect(fetchSpy.mock.calls[3][1]).toMatchObject({ method: "DELETE" });
	});
});
