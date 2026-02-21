from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Video Digestor API")
    app_version: str = os.getenv("APP_VERSION", "0.1.0")
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5432/video_analysis",
    )
    temporal_target_host: str = os.getenv("TEMPORAL_TARGET_HOST", "localhost:7233")
    temporal_namespace: str = os.getenv("TEMPORAL_NAMESPACE", "default")
    temporal_task_queue: str = os.getenv("TEMPORAL_TASK_QUEUE", "video-analysis-worker")
    sqlite_state_path: str = os.getenv(
        "SQLITE_STATE_PATH",
        os.path.expanduser("~/.video-digestor/state/worker_state.db"),
    )


settings = Settings()
