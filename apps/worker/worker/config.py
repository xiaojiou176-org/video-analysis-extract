from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_bool(raw: str | None, *, default: bool) -> bool:
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    return default


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


@dataclass(frozen=True)
class Settings:
    rsshub_base_url: str = "https://rsshub.app"
    feed_paths: list[str] = field(default_factory=list)
    request_timeout_seconds: float = 15.0
    request_retry_attempts: int = 3
    request_retry_backoff_seconds: float = 0.5
    comments_top_n: int = 10
    comments_replies_per_comment: int = 10
    comments_request_timeout_seconds: float = 10.0

    sqlite_path: str = os.path.expanduser("~/.video-digestor/state/worker_state.db")
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/video_analysis"

    temporal_target_host: str = "localhost:7233"
    temporal_namespace: str = "default"
    temporal_task_queue: str = "video-analysis-worker"

    lock_ttl_seconds: int = 90
    pipeline_workspace_dir: str = os.path.expanduser("~/.video-digestor/workspace")
    pipeline_artifact_root: str = os.path.expanduser("~/.video-digestor/artifacts")
    pipeline_retry_attempts: int = 2
    pipeline_retry_backoff_seconds: float = 1.0
    pipeline_subprocess_timeout_seconds: int = 180
    pipeline_max_frames: int = 6
    pipeline_frame_interval_seconds: int = 30
    pipeline_llm_input_mode: str = "auto"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-1.5-flash"
    youtube_api_key: str | None = None
    notification_enabled: bool = False
    resend_api_key: str | None = None
    resend_from_email: str | None = None
    digest_template_path: str = str(
        Path(__file__).resolve().parent.parent / "templates" / "digest.md.mustache"
    )

    @property
    def feed_urls(self) -> list[str]:
        urls: list[str] = []
        for path in self.feed_paths:
            if path.startswith("http://") or path.startswith("https://"):
                urls.append(path)
                continue

            base = self.rsshub_base_url.rstrip("/")
            relative = path if path.startswith("/") else f"/{path}"
            urls.append(f"{base}{relative}")
        return urls

    @classmethod
    def from_env(cls) -> "Settings":
        feed_urls = _split_csv(os.getenv("FEED_URLS"))
        feed_paths = feed_urls or _split_csv(os.getenv("FEED_PATHS"))
        settings = cls(
            rsshub_base_url=os.getenv("RSSHUB_BASE_URL", "https://rsshub.app"),
            feed_paths=feed_paths,
            request_timeout_seconds=float(os.getenv("REQUEST_TIMEOUT_SECONDS", "15")),
            request_retry_attempts=int(os.getenv("REQUEST_RETRY_ATTEMPTS", "3")),
            request_retry_backoff_seconds=float(
                os.getenv("REQUEST_RETRY_BACKOFF_SECONDS", "0.5")
            ),
            comments_top_n=int(os.getenv("COMMENTS_TOP_N", "10")),
            comments_replies_per_comment=int(os.getenv("COMMENTS_REPLIES_PER_COMMENT", "10")),
            comments_request_timeout_seconds=float(
                os.getenv("COMMENTS_REQUEST_TIMEOUT_SECONDS", "10")
            ),
            sqlite_path=os.getenv(
                "SQLITE_PATH",
                os.path.expanduser("~/.video-digestor/state/worker_state.db"),
            ),
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+psycopg://postgres:postgres@localhost:5432/video_analysis",
            ),
            temporal_target_host=os.getenv("TEMPORAL_TARGET_HOST", "localhost:7233"),
            temporal_namespace=os.getenv("TEMPORAL_NAMESPACE", "default"),
            temporal_task_queue=os.getenv("TEMPORAL_TASK_QUEUE", "video-analysis-worker"),
            lock_ttl_seconds=int(os.getenv("LOCK_TTL_SECONDS", "90")),
            pipeline_workspace_dir=os.getenv(
                "PIPELINE_WORKSPACE_DIR",
                os.path.expanduser("~/.video-digestor/workspace"),
            ),
            pipeline_artifact_root=os.getenv(
                "PIPELINE_ARTIFACT_ROOT",
                os.path.expanduser("~/.video-digestor/artifacts"),
            ),
            pipeline_retry_attempts=int(os.getenv("PIPELINE_RETRY_ATTEMPTS", "2")),
            pipeline_retry_backoff_seconds=float(
                os.getenv("PIPELINE_RETRY_BACKOFF_SECONDS", "1.0")
            ),
            pipeline_subprocess_timeout_seconds=int(
                os.getenv("PIPELINE_SUBPROCESS_TIMEOUT_SECONDS", "180")
            ),
            pipeline_max_frames=int(os.getenv("PIPELINE_MAX_FRAMES", "6")),
            pipeline_frame_interval_seconds=int(
                os.getenv("PIPELINE_FRAME_INTERVAL_SECONDS", "30")
            ),
            pipeline_llm_input_mode=os.getenv("PIPELINE_LLM_INPUT_MODE", "auto"),
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-flash"),
            youtube_api_key=os.getenv("YOUTUBE_API_KEY"),
            notification_enabled=_parse_bool(
                os.getenv("NOTIFICATION_ENABLED"),
                default=False,
            ),
            resend_api_key=os.getenv("RESEND_API_KEY"),
            resend_from_email=os.getenv("RESEND_FROM_EMAIL"),
            digest_template_path=os.getenv(
                "DIGEST_TEMPLATE_PATH",
                str(Path(__file__).resolve().parent.parent / "templates" / "digest.md.mustache"),
            ),
        )
        return settings.validate()

    def validate(self) -> "Settings":
        required_fields = {
            "DATABASE_URL": self.database_url,
            "TEMPORAL_TARGET_HOST": self.temporal_target_host,
            "TEMPORAL_NAMESPACE": self.temporal_namespace,
            "TEMPORAL_TASK_QUEUE": self.temporal_task_queue,
            "SQLITE_PATH": self.sqlite_path,
            "PIPELINE_WORKSPACE_DIR": self.pipeline_workspace_dir,
            "PIPELINE_ARTIFACT_ROOT": self.pipeline_artifact_root,
        }
        for key, value in required_fields.items():
            if _is_blank(value):
                raise RuntimeError(f"{key} is not configured")

        if self.notification_enabled:
            if _is_blank(self.resend_api_key):
                raise RuntimeError("RESEND_API_KEY is not configured")
            if _is_blank(self.resend_from_email):
                raise RuntimeError("RESEND_FROM_EMAIL is not configured")
        return self
