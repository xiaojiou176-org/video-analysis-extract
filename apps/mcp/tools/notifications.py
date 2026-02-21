from __future__ import annotations

from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

ApiCall = Callable[..., dict[str, Any]]


def _is_error_payload(payload: dict[str, Any]) -> bool:
    return {"code", "message", "details"}.issubset(payload.keys())


def _to_optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _to_optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _to_optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def _normalize_send_test_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if _is_error_payload(payload):
        return payload
    return {
        "delivery_id": _to_optional_str(payload.get("delivery_id")),
        "status": _to_optional_str(payload.get("status")),
        "provider_message_id": _to_optional_str(payload.get("provider_message_id")),
        "error_message": _to_optional_str(payload.get("error_message")),
        "recipient_email": _to_optional_str(payload.get("recipient_email")),
        "subject": _to_optional_str(payload.get("subject")),
        "sent_at": _to_optional_str(payload.get("sent_at")),
        "created_at": _to_optional_str(payload.get("created_at")),
    }


def _normalize_set_config_payload(payload: dict[str, Any]) -> dict[str, Any]:
    if _is_error_payload(payload):
        return payload
    return {
        "enabled": _to_optional_bool(payload.get("enabled")),
        "to_email": _to_optional_str(payload.get("to_email")),
        "daily_digest_enabled": _to_optional_bool(payload.get("daily_digest_enabled")),
        "daily_digest_hour_utc": _to_optional_int(payload.get("daily_digest_hour_utc")),
        "failure_alert_enabled": _to_optional_bool(payload.get("failure_alert_enabled")),
        "created_at": _to_optional_str(payload.get("created_at")),
        "updated_at": _to_optional_str(payload.get("updated_at")),
    }


def register_notification_tools(mcp: FastMCP, api_call: ApiCall) -> None:
    @mcp.tool(name="vd.notifications.send_test", description="Send a test notification.")
    def send_test_notification(
        to_email: str | None = None,
        subject: str | None = None,
        body: str | None = None,
    ) -> dict[str, Any]:
        response = api_call(
            "POST",
            "/api/v1/notifications/test",
            json_body={
                "to_email": to_email,
                "subject": subject,
                "body": body,
            },
        )
        return _normalize_send_test_payload(response)

    @mcp.tool(name="vd.notifications.set_config", description="Set notification config.")
    def set_notification_config(
        enabled: bool,
        to_email: str | None = None,
        daily_digest_enabled: bool = False,
        daily_digest_hour_utc: int | None = None,
        failure_alert_enabled: bool = True,
    ) -> dict[str, Any]:
        response = api_call(
            "PUT",
            "/api/v1/notifications/config",
            json_body={
                "enabled": enabled,
                "to_email": to_email,
                "daily_digest_enabled": daily_digest_enabled,
                "daily_digest_hour_utc": daily_digest_hour_utc,
                "failure_alert_enabled": failure_alert_enabled,
            },
        )
        return _normalize_set_config_payload(response)
