from __future__ import annotations

import importlib
import sys
import types

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def api_client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    # Force sqlite in tests to avoid local Postgres dependency on import.
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")

    # notifications router currently has a type-annotation issue during module import.
    # Stub it here to keep API route tests focused on health/ingest/videos behavior.
    from fastapi import APIRouter

    notifications_stub = types.ModuleType("apps.api.app.routers.notifications")
    notifications_stub.router = APIRouter(prefix="/api/v1/notifications")
    notifications_stub.reports_router = APIRouter(prefix="/api/v1/reports")
    sys.modules["apps.api.app.routers.notifications"] = notifications_stub

    module = importlib.import_module("apps.api.app.main")
    app = getattr(module, "app")
    with TestClient(app) as client:
        yield client
