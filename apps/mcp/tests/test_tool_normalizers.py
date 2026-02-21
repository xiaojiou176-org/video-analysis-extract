from __future__ import annotations

from apps.mcp.tools.artifacts import _normalize_markdown_payload
from apps.mcp.tools.jobs import _normalize_job_payload
from apps.mcp.tools.notifications import (
    _normalize_send_test_payload,
    _normalize_set_config_payload,
)


def test_artifact_normalizer_marks_payload_found_when_markdown_present() -> None:
    payload = _normalize_markdown_payload(
        {
            "markdown": "# digest",
            "job_id": "job-1",
            "video_url": "https://example.com/video",
        }
    )

    assert payload["found"] is True
    assert payload["markdown"] == "# digest"
    assert payload["job_id"] == "job-1"


def test_job_normalizer_keeps_extended_pipeline_fields() -> None:
    normalized = _normalize_job_payload(
        {
            "id": "job-1",
            "status": "running",
            "mode": "text_only",
            "pipeline_final_status": "partial",
            "artifacts_index": {
                "digest_markdown": "/tmp/artifacts/digest.md",
                "step_json": "/tmp/artifacts/steps.json",
            },
            "step_summary": [
                {
                    "name": "fetch_metadata",
                    "status": "succeeded",
                    "attempt": 1,
                    "started_at": "2026-02-21T10:00:00Z",
                    "finished_at": "2026-02-21T10:00:03Z",
                }
            ],
            "steps": [
                {
                    "name": "llm_digest",
                    "status": "failed",
                    "attempt": 2,
                    "started_at": "2026-02-21T10:01:00Z",
                    "finished_at": "2026-02-21T10:01:02Z",
                    "error": {"detail": "upstream timeout"},
                    "error_kind": "timeout",
                    "retry_meta": {"max_attempts": 2},
                    "result": {"fallback_used": True},
                    "cache_key": "llm_digest:v1",
                }
            ],
            "degradations": [
                {
                    "step": "llm_digest",
                    "status": "failed",
                    "reason": "fallback_to_local_template",
                    "error": {"detail": "upstream timeout"},
                    "error_kind": "timeout",
                    "retry_meta": {"attempt": 2},
                    "cache_meta": {"hit": False},
                }
            ],
        }
    )

    assert normalized["id"] == "job-1"
    assert normalized["status"] == "running"
    assert normalized["mode"] == "text_only"
    assert normalized["pipeline_final_status"] == "partial"
    assert normalized["artifacts_index"]["digest_markdown"] == "/tmp/artifacts/digest.md"
    assert normalized["step_summary"][0]["name"] == "fetch_metadata"
    assert normalized["step_summary"][0]["attempt"] == 1
    assert normalized["steps"][0]["name"] == "llm_digest"
    assert normalized["steps"][0]["error_kind"] == "timeout"
    assert normalized["steps"][0]["retry_meta"] == {"max_attempts": 2}
    assert normalized["degradations"][0]["reason"] == "fallback_to_local_template"
    assert normalized["degradations"][0]["cache_meta"] == {"hit": False}


def test_notification_normalizers_return_expected_core_fields() -> None:
    send_test = _normalize_send_test_payload(
        {
            "delivery_id": "delivery-1",
            "status": "sent",
            "provider_message_id": "provider-1",
            "recipient_email": "demo@example.com",
            "subject": "hello",
            "created_at": "2026-02-21T10:00:00Z",
        }
    )
    set_config = _normalize_set_config_payload(
        {
            "enabled": True,
            "to_email": "demo@example.com",
            "daily_digest_enabled": False,
            "daily_digest_hour_utc": 8,
            "failure_alert_enabled": True,
            "updated_at": "2026-02-21T10:00:00Z",
        }
    )

    assert send_test["delivery_id"] == "delivery-1"
    assert send_test["status"] == "sent"
    assert send_test["recipient_email"] == "demo@example.com"
    assert set_config["enabled"] is True
    assert set_config["daily_digest_hour_utc"] == 8
    assert set_config["updated_at"] == "2026-02-21T10:00:00Z"
