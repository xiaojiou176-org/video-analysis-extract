from __future__ import annotations

from typing import Any, Callable

from mcp.server.fastmcp import FastMCP

ApiCall = Callable[..., dict[str, Any]]


def _is_error_payload(payload: dict[str, Any]) -> bool:
    return {"code", "message", "details"}.issubset(payload.keys())


def _to_optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def register_report_tools(mcp: FastMCP, api_call: ApiCall) -> None:
    @mcp.tool(name="vd.reports.daily_send", description="Send daily report notification.")
    def send_daily_report(
        date: str | None = None,
        to_email: str | None = None,
        subject: str | None = None,
        body: str | None = None,
    ) -> dict[str, Any]:
        response = api_call(
            "POST",
            "/api/v1/reports/daily/send",
            json_body={
                "date": date,
                "to_email": to_email,
                "subject": subject,
                "body": body,
            },
        )

        if _is_error_payload(response):
            return response

        return {
            "sent": bool(response.get("sent", False)),
            "status": _to_optional_str(response.get("status")),
            "delivery_id": _to_optional_str(response.get("delivery_id")),
            "date": _to_optional_str(response.get("date")) or date,
            "recipient_email": _to_optional_str(response.get("recipient_email")),
            "subject": _to_optional_str(response.get("subject")),
            "error_message": _to_optional_str(response.get("error_message")),
            "sent_at": _to_optional_str(response.get("sent_at")),
            "created_at": _to_optional_str(response.get("created_at")),
        }
