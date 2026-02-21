from __future__ import annotations

import os
from dataclasses import dataclass


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
    app_name: str
    app_version: str
    database_url: str
    temporal_target_host: str
    temporal_namespace: str
    temporal_task_queue: str
    sqlite_state_path: str
    notification_enabled: bool
    resend_api_key: str | None
    resend_from_email: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            app_name=os.getenv("APP_NAME", "Video Digestor API"),
            app_version=os.getenv("APP_VERSION", "0.1.0"),
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+psycopg://postgres:postgres@localhost:5432/video_analysis",
            ),
            temporal_target_host=os.getenv("TEMPORAL_TARGET_HOST", "localhost:7233"),
            temporal_namespace=os.getenv("TEMPORAL_NAMESPACE", "default"),
            temporal_task_queue=os.getenv("TEMPORAL_TASK_QUEUE", "video-analysis-worker"),
            sqlite_state_path=os.getenv(
                "SQLITE_STATE_PATH",
                os.path.expanduser("~/.video-digestor/state/worker_state.db"),
            ),
            notification_enabled=_parse_bool(
                os.getenv("NOTIFICATION_ENABLED"),
                default=False,
            ),
            resend_api_key=os.getenv("RESEND_API_KEY"),
            resend_from_email=os.getenv("RESEND_FROM_EMAIL"),
        )

    def validate(self) -> "Settings":
        required_fields = {
            "DATABASE_URL": self.database_url,
            "TEMPORAL_TARGET_HOST": self.temporal_target_host,
            "TEMPORAL_NAMESPACE": self.temporal_namespace,
            "TEMPORAL_TASK_QUEUE": self.temporal_task_queue,
            "SQLITE_STATE_PATH": self.sqlite_state_path,
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


settings = Settings.from_env().validate()
