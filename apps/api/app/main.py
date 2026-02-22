from __future__ import annotations

from fastapi import FastAPI

from .config import settings
from .routers import artifacts, computer_use, health, ingest, jobs, notifications, retrieval, subscriptions, videos, workflows

app = FastAPI(title=settings.app_name, version=settings.app_version)


@app.get("/healthz", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(subscriptions.router)
app.include_router(ingest.router)
app.include_router(jobs.router)
app.include_router(videos.router)
app.include_router(notifications.router)
app.include_router(notifications.reports_router)
app.include_router(artifacts.router)
app.include_router(health.router)
app.include_router(workflows.router)
app.include_router(retrieval.router)
app.include_router(computer_use.router)
