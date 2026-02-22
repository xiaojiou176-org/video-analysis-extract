import type {
  ArtifactMarkdownWithMeta,
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
import { resolveApiBaseUrl } from "@/lib/api/url";

type RequestOptions = Omit<RequestInit, "body"> & {
  body?: unknown;
};

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

function buildUrl(path: string, query?: Record<string, string | number | boolean | null | undefined>): string {
  const target = new URL(path, resolveApiBaseUrl());
  if (!query) {
    return target.toString();
  }

  for (const [key, value] of Object.entries(query)) {
    if (value === null || value === undefined || value === "") {
      continue;
    }
    target.searchParams.set(key, String(value));
  }

  return target.toString();
}

async function parseError(response: Response): Promise<string> {
  const contentType = response.headers.get("content-type") ?? "";
  let detailMessage: string | null = null;

  if (contentType.includes("application/json")) {
    const payload = (await response.json().catch(() => null)) as Record<string, unknown> | null;
    if (payload && typeof payload === "object") {
      const detail = payload["detail"];
      if (typeof detail === "string") {
        return detail;
      }
      const message = payload["message"];
      if (typeof message === "string") {
        detailMessage = message;
      }
    }
  }

  if (detailMessage) {
    return detailMessage;
  }

  const text = (await response.text().catch(() => "")).trim();
  if (response.status === 404) {
    return "Requested resource was not found.";
  }
  if (response.status >= 500) {
    return "Service is temporarily unavailable. Please try again.";
  }
  if (response.status === 401 || response.status === 403) {
    return "You do not have permission to access this resource.";
  }
  if (response.status === 400) {
    return "Request payload is invalid. Please check your input.";
  }
  return text || `Request failed (${response.status})`;
}

async function requestJson<T>(path: string, options: RequestOptions = {}, query?: Record<string, string | number | boolean | null | undefined>): Promise<T> {
  const response = await fetch(buildUrl(path, query), {
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

async function requestText(path: string, query?: Record<string, string | number | boolean | null | undefined>): Promise<string> {
  const response = await fetch(buildUrl(path, query), { cache: "no-store" });
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
  if (params.include_meta) {
    return requestJson<ArtifactMarkdownWithMeta>("/api/v1/artifacts/markdown", {}, params);
  }

  return requestText("/api/v1/artifacts/markdown", params);
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

  deleteSubscription(id: string) {
    return requestJson<void>(`/api/v1/subscriptions/${id}`, {
      method: "DELETE",
    });
  },

  pollIngest(payload: IngestPollRequest) {
    return requestJson<IngestPollResponse>("/api/v1/ingest/poll", {
      method: "POST",
      body: payload,
    });
  },

  listVideos(params?: {
    platform?: Platform;
    status?: JobStatus;
    limit?: number;
  }) {
    return requestJson<Video[]>("/api/v1/videos", {}, params);
  },

  processVideo(payload: VideoProcessRequest) {
    return requestJson<VideoProcessResponse>("/api/v1/videos/process", {
      method: "POST",
      body: payload,
    });
  },

  getJob(jobId: string) {
    return requestJson<Job>(`/api/v1/jobs/${jobId}`).then(normalizeJob);
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
};
