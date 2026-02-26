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
		steps: Array.isArray(job.steps) ? job.steps : [],
		degradations: Array.isArray(job.degradations) ? job.degradations : [],
		artifacts_index: normalizeStringMap(job.artifacts_index),
		mode: job.mode ?? null,
	};
}

function assertSafeExternalUrl(raw: string): string {
	const normalized = sanitizeExternalUrl(raw);
	if (!normalized) {
		throw new Error("ERR_INVALID_INPUT");
	}
	return normalized;
}

async function parseError(response: Response): Promise<string> {
	void response.text().catch(() => "");
	if (response.status === 404) {
		return "ERR_REQUEST_FAILED";
	}
	if (response.status >= 500) {
		return "ERR_REQUEST_FAILED";
	}
	if (response.status === 401 || response.status === 403) {
		return "ERR_AUTH_REQUIRED";
	}
	if (response.status === 400) {
		return "ERR_INVALID_INPUT";
	}
	return "ERR_REQUEST_FAILED";
}

async function requestJson<T>(
	path: string,
	options: RequestOptions = {},
	query?: Record<string, string | number | boolean | null | undefined>,
): Promise<T> {
	const response = await fetch(buildApiUrl(path, query), {
		...options,
		cache: "no-store",
		headers: {
			"Content-Type": "application/json",
			...(options.headers ?? {}),
		},
		body: options.body === undefined ? undefined : JSON.stringify(options.body),
	});

	if (!response.ok) {
		const reason = await parseError(response);
		throw new Error(reason);
	}

	if (response.status === 204) {
		return undefined as T;
	}

	return (await response.json()) as T;
}

async function requestText(
	path: string,
	query?: Record<string, string | number | boolean | null | undefined>,
): Promise<string> {
	const response = await fetch(buildApiUrl(path, query), { cache: "no-store" });
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
		return requestJson<ArtifactMarkdownWithMeta>("/api/v1/artifacts/markdown", {}, safeParams);
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
		return requestJson<DigestFeedResponse>("/api/v1/feed/digests", {}, params);
	},
};
