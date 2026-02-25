from __future__ import annotations

from datetime import date, datetime, timezone
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette import status

from apps.api.app.db import get_db
from apps.api.app.routers import notifications as notifications_router
from apps.api.app.routers.notifications import reports_router, router


def _build_notifications_client() -> TestClient:
    app = FastAPI()
    app.include_router(router)
    app.include_router(reports_router)

    def _fake_db():
        yield SimpleNamespace()

    app.dependency_overrides[get_db] = _fake_db
    return TestClient(app)


def test_notifications_write_endpoints_require_write_access(monkeypatch) -> None:
    now = datetime.now(timezone.utc)
    monkeypatch.setenv("VD_API_KEY", "unit-test-token")
    monkeypatch.setattr(
        notifications_router,
        "update_notification_config",
        lambda *args, **kwargs: SimpleNamespace(
            enabled=True,
            to_email="ops@example.com",
            daily_digest_enabled=True,
            daily_digest_hour_utc=9,
            failure_alert_enabled=True,
            category_rules={},
            created_at=now,
            updated_at=now,
        ),
    )
    monkeypatch.setattr(
        notifications_router,
        "send_daily_report_notification",
        lambda *args, **kwargs: SimpleNamespace(
            id="00000000-0000-4000-8000-000000000001",
            status="sent",
            payload_json={"digest_date": "2026-02-20"},
            recipient_email="ops@example.com",
            subject="Daily",
            error_message=None,
            sent_at=now,
            created_at=now,
        ),
    )

    with _build_notifications_client() as client:
        put_payload = {
            "enabled": True,
            "to_email": "ops@example.com",
            "daily_digest_enabled": True,
            "daily_digest_hour_utc": 9,
            "failure_alert_enabled": True,
        }
        unauth = client.put("/api/v1/notifications/config", json=put_payload)
        forbidden = client.put(
            "/api/v1/notifications/config",
            json=put_payload,
            headers={"Authorization": "Bearer wrong-token"},
        )
        authorized = client.put(
            "/api/v1/notifications/config",
            json=put_payload,
            headers={"X-API-Key": "unit-test-token"},
        )

        report_forbidden = client.post(
            "/api/v1/reports/daily/send",
            json={"date": date.today().isoformat()},
            headers={"X-API-Key": "wrong-token"},
        )
        report_authorized = client.post(
            "/api/v1/reports/daily/send",
            json={"date": date.today().isoformat()},
            headers={"Authorization": "Bearer unit-test-token"},
        )

    assert unauth.status_code == status.HTTP_401_UNAUTHORIZED
    assert forbidden.status_code == status.HTTP_403_FORBIDDEN
    assert authorized.status_code == status.HTTP_200_OK
    assert report_forbidden.status_code == status.HTTP_403_FORBIDDEN
    assert report_authorized.status_code == status.HTTP_200_OK
