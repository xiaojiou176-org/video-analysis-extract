from __future__ import annotations

from types import SimpleNamespace

from apps.api.app.services import notifications


def _config_with_rules(category_rules: dict[str, object]) -> SimpleNamespace:
    return SimpleNamespace(
        enabled=True,
        to_email="demo@example.com",
        daily_digest_enabled=True,
        daily_digest_hour_utc=9,
        failure_alert_enabled=True,
        category_rules=category_rules,
    )


def test_send_category_digest_respects_rule_cadence_and_dispatch_key(monkeypatch) -> None:
    config = _config_with_rules(
        {
            "default_rule": {"enabled": True, "cadence": "daily", "hour": 7},
            "category_rules": {"tech": {"enabled": True, "cadence": "instant", "min_priority": 50}},
        }
    )

    monkeypatch.setattr(notifications, "get_notification_config", lambda db: config)
    captured: dict[str, object] = {}

    def fake_dispatch_email(db, **kwargs):
        del db
        captured.update(kwargs)
        return SimpleNamespace(
            id="delivery-1",
            status="sent",
            provider_message_id="provider-1",
            error_message=None,
            recipient_email=kwargs["recipient_email"],
            subject=kwargs["subject"],
            sent_at=None,
            created_at=None,
        )

    monkeypatch.setattr(notifications, "_dispatch_email", fake_dispatch_email)

    row = notifications.send_category_digest(
        None,  # type: ignore[arg-type]
        category="tech",
        digest_markdown="digest body",
        priority=60,
        dispatch_key="tech:2026-02-23",
    )

    assert row.status == "sent"
    assert captured["skip_reason"] is None
    assert captured["dispatch_key"] == "tech:2026-02-23"


def test_hourly_cadence_fires_at_matching_hour(monkeypatch) -> None:
    from datetime import datetime, timezone

    config = _config_with_rules(
        {"category_rules": {"tech": {"enabled": True, "cadence": "hourly", "interval_hours": 2}}}
    )
    monkeypatch.setattr(notifications, "get_notification_config", lambda db: config)
    captured: dict[str, object] = {}

    def fake_dispatch_email(db, **kwargs):
        del db
        captured.update(kwargs)
        return SimpleNamespace(
            id="delivery-h",
            status="sent",
            provider_message_id=None,
            error_message=None,
            recipient_email=kwargs["recipient_email"],
            subject=kwargs["subject"],
            sent_at=None,
            created_at=None,
        )

    monkeypatch.setattr(notifications, "_dispatch_email", fake_dispatch_email)
    monkeypatch.setattr(
        notifications,
        "_utc_now",
        lambda: datetime(2026, 2, 23, 6, 30, tzinfo=timezone.utc),  # hour=6, 6%2==0 → fire
    )

    row = notifications.send_category_digest(
        None,  # type: ignore[arg-type]
        category="tech",
        digest_markdown="hourly digest",
        dispatch_key="tech:hourly:2026-02-23T06",
    )

    assert row.status == "sent"
    assert captured["skip_reason"] is None


def test_hourly_cadence_skips_at_non_matching_hour(monkeypatch) -> None:
    from datetime import datetime, timezone

    config = _config_with_rules(
        {"category_rules": {"tech": {"enabled": True, "cadence": "hourly", "interval_hours": 2}}}
    )
    monkeypatch.setattr(notifications, "get_notification_config", lambda db: config)
    captured: dict[str, object] = {}

    def fake_dispatch_email(db, **kwargs):
        del db
        captured.update(kwargs)
        return SimpleNamespace(status="skipped")

    monkeypatch.setattr(notifications, "_dispatch_email", fake_dispatch_email)
    monkeypatch.setattr(
        notifications,
        "_utc_now",
        lambda: datetime(2026, 2, 23, 7, 0, tzinfo=timezone.utc),  # hour=7, 7%2!=0 → skip
    )

    notifications.send_category_digest(
        None,  # type: ignore[arg-type]
        category="tech",
        digest_markdown="should skip",
        dispatch_key="tech:hourly:2026-02-23T07",
    )

    assert str(captured.get("skip_reason", "")).startswith("hourly cadence mismatch")


def test_send_category_digest_applies_min_priority_skip(monkeypatch) -> None:
    config = _config_with_rules(
        {
            "category_rules": {
                "ops": {"enabled": True, "cadence": "instant", "min_priority": 90},
            }
        }
    )
    monkeypatch.setattr(notifications, "get_notification_config", lambda db: config)
    captured: dict[str, object] = {}

    def fake_dispatch_email(db, **kwargs):
        del db
        captured.update(kwargs)
        return SimpleNamespace(status="skipped")

    monkeypatch.setattr(notifications, "_dispatch_email", fake_dispatch_email)

    notifications.send_category_digest(
        None,  # type: ignore[arg-type]
        category="ops",
        digest_markdown="digest body",
        priority=20,
        dispatch_key="ops:2026-02-23",
    )

    assert str(captured["skip_reason"]).startswith("priority below threshold")
