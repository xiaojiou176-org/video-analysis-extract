from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from apps.mcp.tools._common import (
    ApiCall,
    invalid_argument,
    is_error_payload,
    to_optional_bool,
    to_optional_dict,
    to_optional_str,
    validate_object_keys,
)


def _normalize_action_item(item: Any, default_step: int) -> dict[str, Any]:
    source = item if isinstance(item, dict) else {}
    step = source.get("step")
    if not isinstance(step, int) or step < 1:
        step = default_step
    action = to_optional_str(source.get("action")) or "observe"
    return {
        "step": step,
        "action": action,
        "target": to_optional_str(source.get("target")),
        "input_text": to_optional_str(source.get("input_text")),
        "reasoning": to_optional_str(source.get("reasoning")),
    }


def register_computer_use_tools(mcp: FastMCP, api_call: ApiCall) -> None:
    @mcp.tool(
        name="vd.computer_use.run",
        description="Plan computer-use actions from an instruction and screenshot with safety policy checks.",
    )
    def run_computer_use(
        instruction: str,
        screenshot_base64: str,
        safety: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized_safety, safety_error = validate_object_keys(
            safety or {},
            allowed_keys={"confirm_before_execute", "blocked_actions", "max_actions"},
        )
        if safety_error is not None or normalized_safety is None:
            return invalid_argument(
                f"safety {safety_error or 'is invalid'}",
                method="POST",
                path="/api/v1/computer-use/run",
                field="safety",
            )
        response = api_call(
            "POST",
            "/api/v1/computer-use/run",
            json_body={
                "instruction": instruction,
                "screenshot_base64": screenshot_base64,
                "safety": normalized_safety,
            },
        )
        if is_error_payload(response):
            return response

        raw_actions = response.get("actions")
        raw_blocked_actions = response.get("blocked_actions")
        return {
            "actions": [
                _normalize_action_item(item, default_step=index)
                for index, item in enumerate(
                    raw_actions if isinstance(raw_actions, list) else [], start=1
                )
            ],
            "require_confirmation": bool(to_optional_bool(response.get("require_confirmation"))),
            "blocked_actions": [
                value
                for value in (
                    to_optional_str(item)
                    for item in (
                        raw_blocked_actions if isinstance(raw_blocked_actions, list) else []
                    )
                )
                if value is not None
            ],
            "final_text": to_optional_str(response.get("final_text")) or "",
            "thought_metadata": to_optional_dict(response.get("thought_metadata")) or {},
        }
