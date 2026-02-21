export type Platform = "bilibili" | "youtube";
export type SourceType = "bilibili_uid" | "youtube_channel_id" | "url";
export type JobStatus = "queued" | "running" | "succeeded" | "failed" | "partial";
export type PipelineFinalStatus = "succeeded" | "partial" | "failed";
export type VideoProcessMode = "full" | "text_only" | "refresh_comments" | "refresh_llm";

export type Subscription = {
  id: string;
  platform: Platform;
  source_type: SourceType;
  source_value: string;
  rsshub_route: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type SubscriptionUpsertRequest = {
  platform: Platform;
  source_type: SourceType;
  source_value: string;
  rsshub_route?: string | null;
  enabled?: boolean;
};

export type SubscriptionUpsertResponse = {
  subscription: Subscription;
  created: boolean;
};

export type IngestPollRequest = {
  subscription_id?: string;
  platform?: Platform;
  max_new_videos?: number;
};

export type IngestCandidate = {
  video_id: string;
  platform: Platform;
  video_uid: string;
  source_url: string;
  title: string | null;
  published_at: string | null;
  job_id: string;
};

export type IngestPollResponse = {
  enqueued: number;
  candidates: IngestCandidate[];
};

export type Video = {
  id: string;
  platform: Platform;
  video_uid: string;
  source_url: string;
  title: string | null;
  published_at: string | null;
  first_seen_at: string;
  last_seen_at: string;
  status: JobStatus | null;
  last_job_id: string | null;
};

export type VideoProcessRequest = {
  video: {
    platform: Platform;
    url: string;
    video_id?: string | null;
  };
  mode?: VideoProcessMode;
  overrides?: Record<string, unknown>;
  force?: boolean;
};

export type VideoProcessResponse = {
  job_id: string;
  video_db_id: string;
  video_uid: string;
  status: JobStatus;
  idempotency_key: string;
  mode: VideoProcessMode;
  overrides: Record<string, unknown>;
  force: boolean;
  reused: boolean;
  workflow_id: string | null;
};

export type JobStepSummary = {
  name: string;
  status: string;
  attempt: number;
  started_at: string | null;
  finished_at: string | null;
  error: unknown;
};

export type JobStepDetail = JobStepSummary & {
  error_kind: string | null;
  retry_meta: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  cache_key: string | null;
};

export type JobDegradation = {
  step: string | null;
  status: string | null;
  reason: string | null;
  error: unknown;
  error_kind: string | null;
  retry_meta: Record<string, unknown> | null;
  cache_meta: Record<string, unknown> | null;
};

export type Job = {
  id: string;
  video_id: string;
  kind: "video_digest_v1" | "phase2_ingest_stub";
  status: JobStatus;
  idempotency_key: string;
  error_message: string | null;
  artifact_digest_md: string | null;
  artifact_root: string | null;
  created_at: string;
  updated_at: string;
  step_summary: JobStepSummary[];
  steps: JobStepDetail[];
  degradations: JobDegradation[];
  pipeline_final_status: PipelineFinalStatus | null;
  artifacts_index: Record<string, string>;
  mode: VideoProcessMode | null;
};

export type ArtifactMarkdownWithMeta = {
  markdown: string;
  meta: Record<string, unknown> | null;
};

export type NotificationConfig = {
  enabled: boolean;
  to_email: string | null;
  daily_digest_enabled: boolean;
  daily_digest_hour_utc: number | null;
  failure_alert_enabled: boolean;
  created_at: string;
  updated_at: string;
};

export type NotificationConfigUpdateRequest = {
  enabled: boolean;
  to_email: string | null;
  daily_digest_enabled: boolean;
  daily_digest_hour_utc: number | null;
  failure_alert_enabled: boolean;
};

export type NotificationTestRequest = {
  to_email?: string | null;
  subject?: string | null;
  body?: string | null;
};

export type NotificationSendResponse = {
  delivery_id: string;
  status: string;
  provider_message_id: string | null;
  error_message: string | null;
  recipient_email: string;
  subject: string;
  sent_at: string | null;
  created_at: string;
};
