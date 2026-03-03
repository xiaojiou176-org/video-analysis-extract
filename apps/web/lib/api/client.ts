import type {
	ArtifactMarkdownWithMeta,
	DigestFeedResponse,
	IngestPollRequest,
	IngestPollResponse,
	Job,
	JobStatus,
	NotificationConfig,
	NotificationConfigUpdateRequest,
	NotificationSendResponse,
	NotificationTestRequest,
	Platform,
	Subscription,
	SubscriptionUpsertRequest,
	SubscriptionUpsertResponse,
	Video,
	VideoProcessRequest,
	VideoProcessResponse,
} from "@/lib/api/types";
import { buildApiUrl, sanitizeExternalUrl } from "@/lib/api/url";

type RequestOptions = Omit<RequestInit, "body"> & {
	body?: unknown;
};

function asObject(value: unknown): Record<string, unknown> | null {
	if (!value || typeof value !== "object" || Array.isArray(value)) {
		return null;
	}
	return value as Record<string, unknown>;
}

function asString(value: unknown): string {
	return typeof value === "string" ? value : "";
}

function asBoolean(value: unknown): boolean {
	if (typeof value === "boolean") {
		return value;
	}
	if (typeof value === "string") {
		const normalized = value.trim().toLowerCase();
		if (normalized === "true" || normalized === "1" || normalized === "yes" || normalized === "on") {
			return true;
		}
		if (
			normalized === "false" ||
			normalized === "0" ||
			normalized === "no" ||
			normalized === "off" ||
			normalized === ""
		) {
			return false;
		}
		return false;
	}
	if (typeof value === "number") {
		return value !== 0;
	}
	return false;
}

function assertSafeIdentifier(raw: string): string {
	const value = raw.trim();
	if (!/^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$/.test(value)) {
		throw new Error("ERR_INVALID_IDENTIFIER");
	}
	return value;
}

function normalizeStringMap(value: unknown): Record<string, string> {
	if (!value || typeof value !== "object") {
		return {};
	}

	const entries = Object.entries(value as Record<string, unknown>);
	const normalized: Record<string, string> = {};
	for (const [key, item] of entries) {
		if (typeof item === "string") {
			normalized[key] = item;
		}
	}
	return normalized;
}

function normalizeJob(job: Job): Job {
	return {
		...job,
		step_summary: Array.isArray(job.step_summary) ? job.step_summary : [],
		steps: Array.isArray(job.steps)
			? job.steps
					.map((step) => {
						const record = asObject(step);
						if (!record) {
							return null;
						}
						return {
							...(record as Job["steps"][number]),
							thought_metadata:
								record.thought_metadata &&
								typeof record.thought_metadata === "object" &&
								!Array.isArray(record.thought_metadata)
									? (record.thought_metadata as Record<string, unknown>)
									: {},
						};
					})
					.filter((step): step is Job["steps"][number] => step !== null)
			: [],
		degradations: Array.isArray(job.degradations) ? job.degradations : [],
		artifacts_index: normalizeStringMap(job.artifacts_index),
		mode: job.mode ?? null,
		notification_retry: job.notification_retry ?? null,
	};
}

function normalizeArtifactMarkdownWithMeta(payload: unknown): ArtifactMarkdownWithMeta {
	const parsed = asObject(payload);
	return {
		markdown: asString(parsed?.markdown),
		meta: asObject(parsed?.meta),
	};
}

function normalizeDigestFeedResponse(payload: unknown): DigestFeedResponse {
	const parsed = asObject(payload);
	const rawItems = Array.isArray(parsed?.items) ? parsed.items : [];
	const items: DigestFeedResponse["items"] = rawItems
		.map((item) => {
			const record = asObject(item);
			if (!record) {
				return null;
			}

			const feedId = asString(record.feed_id).trim();
			const jobId = asString(record.job_id).trim();
			if (!feedId || !jobId) {
				return null;
			}

			const category = asString(record.category).trim();
			const artifactTypeRaw = asString(record.artifact_type).trim();
			return {
				feed_id: feedId,
				job_id: jobId,
				video_url: asString(record.video_url),
				title: asString(record.title),
				source: asString(record.source),
				source_name: asString(record.source_name),
				category: category || "misc",
				published_at: asString(record.published_at),
				summary_md: asString(record.summary_md),
				artifact_type: artifactTypeRaw === "outline" ? "outline" : "digest",
			};
		})
		.filter((item): item is DigestFeedResponse["items"][number] => item !== null);

	const nextCursorRaw = parsed?.next_cursor;
	return {
		items,
		has_more: asBoolean(parsed?.has_more),
		next_cursor: typeof nextCursorRaw === "string" ? nextCursorRaw : null,
	};
}

function assertSafeExternalUrl(raw: string): string {
	const normalized = sanitizeExternalUrl(raw);
	if (!normalized) {
		throw new Error("ERR_INVALID_INPUT");
	}
	return normalized;
}

function normalizeErrorCodeCandidate(value: unknown): string | null {
	if (typeof value !== "string") {
		return null;
	}
	const matched = value.trim().toUpperCase().match(/\bERR_[A-Z0-9_]+\b/);
	return matched?.[0] ?? null;
}

function parseErrorCodeFromBody(body: string): string | null {
	const fromText = normalizeErrorCodeCandidate(body);
	if (fromText) {
		return fromText;
	}

	let parsed: unknown;
	try {
		parsed = JSON.parse(body);
	} catch {
		return null;
	}
	const asRecord = asObject(parsed);
	if (!asRecord) {
		return null;
	}
	return (
		normalizeErrorCodeCandidate(asRecord.error_code) ??
		normalizeErrorCodeCandidate(asRecord.code) ??
		normalizeErrorCodeCandidate(asRecord.detail) ??
		normalizeErrorCodeCandidate(asRecord.message)
	);
}

async function parseError(response: Response): Promise<string> {
	const body = await response.text().catch(() => "");
	const errorCode = parseErrorCodeFromBody(body);
	if (errorCode) {
		return errorCode;
	}
	if (response.status === 400 || response.status === 422) {
		return "ERR_INVALID_INPUT";
	}
	if (response.status === 404) {
		return "ERR_REQUEST_FAILED";
	}
	if (response.status >= 500) {
		return "ERR_REQUEST_FAILED";
	}
	if (response.status === 401 || response.status === 403) {
		return "ERR_AUTH_REQUIRED";
	}
	return "ERR_REQUEST_FAILED";
}

async function requestJson<T>(
	path: string,
	options: RequestOptions = {},
	query?: Record<string, string | number | boolean | null | undefined>,
	normalize?: (payload: unknown) => T,
): Promise<T> {
	const url = buildApiUrl(path, query);
	let response: Response;
	try {
		response = await fetch(url, {
			...options,
			cache: "no-store",
			headers: {
				"Content-Type": "application/json",
				...(options.headers ?? {}),
			},
			body: options.body === undefined ? undefined : JSON.stringify(options.body),
		});
	} catch {
		throw new Error("ERR_REQUEST_FAILED");
	}

	if (!response.ok) {
		const reason = await parseError(response);
		throw new Error(reason);
	}

	if (response.status === 204) {
		return undefined as T;
	}

	const textBody = await response.text().catch(() => "");
	if (!textBody.trim()) {
		throw new Error("ERR_PROTOCOL_EMPTY_BODY");
	}

	let parsed: unknown;
	try {
		parsed = JSON.parse(textBody);
	} catch {
		throw new Error("ERR_REQUEST_FAILED");
	}

	if (normalize) {
		return normalize(parsed);
	}

	return parsed as T;
}

async function requestText(
	path: string,
	query?: Record<string, string | number | boolean | null | undefined>,
): Promise<string> {
	const url = buildApiUrl(path, query);
	let response: Response;
	try {
		response = await fetch(url, { cache: "no-store" });
	} catch {
		throw new Error("ERR_REQUEST_FAILED");
	}
	if (!response.ok) {
		const reason = await parseError(response);
		throw new Error(reason);
	}
	return response.text();
}

function getArtifactMarkdown(params: {
	job_id?: string;
	video_url?: string;
	include_meta: true;
}): Promise<ArtifactMarkdownWithMeta>;
function getArtifactMarkdown(params: {
	job_id?: string;
	video_url?: string;
	include_meta?: false;
}): Promise<string>;
function getArtifactMarkdown(params: {
	job_id?: string;
	video_url?: string;
	include_meta?: boolean;
}): Promise<ArtifactMarkdownWithMeta | string> {
	const safeVideoUrl = params.video_url ? assertSafeExternalUrl(params.video_url) : undefined;
	const safeParams = safeVideoUrl ? { ...params, video_url: safeVideoUrl } : params;
	if (params.include_meta) {
		return requestJson<ArtifactMarkdownWithMeta>(
			"/api/v1/artifacts/markdown",
			{},
			safeParams,
			normalizeArtifactMarkdownWithMeta,
		);
	}

	return requestText("/api/v1/artifacts/markdown", safeParams);
}

export const apiClient = {
	listSubscriptions(params?: { platform?: Platform; enabled_only?: boolean }) {
		return requestJson<Subscription[]>("/api/v1/subscriptions", {}, params);
	},

	upsertSubscription(payload: SubscriptionUpsertRequest) {
		return requestJson<SubscriptionUpsertResponse>("/api/v1/subscriptions", {
			method: "POST",
			body: payload,
		});
	},

	batchUpdateSubscriptionCategory(payload: { ids: string[]; category: string }) {
		return requestJson<{ updated: number }>("/api/v1/subscriptions/batch-update-category", {
			method: "POST",
			body: payload,
		});
	},

	deleteSubscription(id: string) {
		const safeId = encodeURIComponent(assertSafeIdentifier(id));
		return requestJson<void>(`/api/v1/subscriptions/${safeId}`, {
			method: "DELETE",
		});
	},

	pollIngest(payload: IngestPollRequest) {
		return requestJson<IngestPollResponse>("/api/v1/ingest/poll", {
			method: "POST",
			body: payload,
		});
	},

	listVideos(params?: { platform?: Platform; status?: JobStatus; limit?: number }) {
		return requestJson<Video[]>("/api/v1/videos", {}, params);
	},

	processVideo(payload: VideoProcessRequest) {
		return requestJson<VideoProcessResponse>("/api/v1/videos/process", {
			method: "POST",
			body: payload,
		});
	},

	getJob(jobId: string) {
		const safeJobId = encodeURIComponent(assertSafeIdentifier(jobId));
		return requestJson<Job>(`/api/v1/jobs/${safeJobId}`).then(normalizeJob);
	},

	getArtifactMarkdown,

	getNotificationConfig() {
		return requestJson<NotificationConfig>("/api/v1/notifications/config");
	},

	updateNotificationConfig(payload: NotificationConfigUpdateRequest) {
		return requestJson<NotificationConfig>("/api/v1/notifications/config", {
			method: "PUT",
			body: payload,
		});
	},

	sendNotificationTest(payload: NotificationTestRequest) {
		return requestJson<NotificationSendResponse>("/api/v1/notifications/test", {
			method: "POST",
			body: payload,
		});
	},

	getDigestFeed(params?: {
		source?: Platform;
		category?: "tech" | "creator" | "macro" | "ops" | "misc";
		limit?: number;
		cursor?: string;
		since?: string;
	}) {
		return requestJson<DigestFeedResponse>(
			"/api/v1/feed/digests",
			{},
			params,
			normalizeDigestFeedResponse,
		);
	},
};
