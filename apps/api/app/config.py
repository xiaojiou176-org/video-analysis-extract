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


def _read_required_env(name: str) -> str:
    value = os.getenv(name)
    if _is_blank(value):
        raise RuntimeError(f"{name} is not configured")
    return value.strip()


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
            database_url=_read_required_env("DATABASE_URL"),
            temporal_target_host=_read_required_env("TEMPORAL_TARGET_HOST"),
            temporal_namespace=_read_required_env("TEMPORAL_NAMESPACE"),
            temporal_task_queue=_read_required_env("TEMPORAL_TASK_QUEUE"),
            sqlite_state_path=_read_required_env("SQLITE_STATE_PATH"),
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
