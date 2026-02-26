import { afterEach, describe, expect, it, vi } from "vitest";

import { apiClient } from "@/lib/api/client";

describe("apiClient core behavior", () => {
	afterEach(() => {
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

	it("maps server errors and not found to ERR_REQUEST_FAILED", async () => {
		const fetchSpy = vi
			.spyOn(globalThis, "fetch")
			.mockResolvedValueOnce(new Response("missing", { status: 404 }))
			.mockResolvedValueOnce(new Response("oops", { status: 503 }));

		await expect(apiClient.getNotificationConfig()).rejects.toThrow("ERR_REQUEST_FAILED");
		await expect(apiClient.getNotificationConfig()).rejects.toThrow("ERR_REQUEST_FAILED");
		expect(fetchSpy).toHaveBeenCalledTimes(2);
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
});
