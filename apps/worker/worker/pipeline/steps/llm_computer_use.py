from __future__ import annotations

from typing import Any, Callable

from worker.pipeline.steps.llm_client_helpers import ComputerUseHandler

ComputerUseExecutor = Callable[[dict[str, Any]], dict[str, Any]]


def _coerce_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _resolve_computer_use_payload(
    *,
    state: dict[str, Any],
    llm_policy: dict[str, Any],
    section_policy: dict[str, Any],
) -> dict[str, Any]:
    metadata = _coerce_dict(state.get("metadata"))
    state_payload = _coerce_dict(state.get("computer_use"))
    llm_payload = _coerce_dict(llm_policy.get("computer_use"))
    section_payload = _coerce_dict(section_policy.get("computer_use"))
    return {
        "executor": (
            section_payload.get("executor")
            or section_policy.get("computer_use_executor")
            or llm_payload.get("executor")
            or llm_policy.get("computer_use_executor")
            or state_payload.get("executor")
            or "no_op"
        ),
        "url": (
            section_payload.get("url")
            or section_policy.get("computer_use_url")
            or llm_payload.get("url")
            or llm_policy.get("computer_use_url")
            or state_payload.get("url")
            or state.get("source_url")
            or metadata.get("webpage_url")
            or ""
        ),
        "screenshot": (
            section_payload.get("screenshot")
            or section_policy.get("computer_use_screenshot")
            or llm_payload.get("screenshot")
            or llm_policy.get("computer_use_screenshot")
            or state_payload.get("screenshot")
            or ""
        ),
        "context": (
            section_payload.get("context")
            or section_policy.get("computer_use_context")
            or llm_payload.get("context")
            or llm_policy.get("computer_use_context")
            or state_payload.get("context")
            or {}
        ),
    }


def _normalize_action(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    action_name = str(payload.get("action") or payload.get("type") or payload.get("name") or "").strip().lower()
    action_args = {
        key: value
        for key, value in payload.items()
        if key not in {"action", "type", "name", "url", "screenshot", "context"}
    }
    return action_name, action_args


def _execute_noop(action_name: str, action_args: dict[str, Any]) -> dict[str, Any]:
    if not action_name:
        return {"ok": False, "status": "error", "error": "computer_use_action_missing"}
    return {
        "ok": True,
        "status": "ok",
        "message": "computer_use_noop_executed",
        "action": {"name": action_name, "args": action_args},
    }


def _execute_browser_stub(action_name: str, action_args: dict[str, Any]) -> dict[str, Any]:
    if not action_name:
        return {"ok": False, "status": "error", "error": "computer_use_action_missing"}
    return {
        "ok": True,
        "status": "ok",
        "message": "computer_use_browser_stub_executed",
        "action": {"name": action_name, "args": action_args},
    }


def _executor_name(raw: Any) -> str:
    candidate = str(raw or "").strip().lower()
    if candidate in {"browser", "browser_stub"}:
        return "browser_stub"
    return "no_op"


def build_default_computer_use_handler(
    *,
    state: dict[str, Any],
    llm_policy: dict[str, Any],
    section_policy: dict[str, Any],
) -> ComputerUseHandler:
    base_payload = _resolve_computer_use_payload(
        state=state,
        llm_policy=llm_policy,
        section_policy=section_policy,
    )
    executor = _executor_name(base_payload.get("executor"))

    def _handler(**payload: Any) -> dict[str, Any]:
        incoming = dict(payload or {})
        action_name, action_args = _normalize_action(incoming)
        url = str(incoming.get("url") or base_payload.get("url") or "").strip()
        screenshot = str(incoming.get("screenshot") or base_payload.get("screenshot") or "").strip()
        context = incoming.get("context")
        if context is None:
            context = base_payload.get("context")
        context_payload = _coerce_dict(context) if isinstance(context, dict) else {"value": context}

        if executor == "browser_stub":
            result = _execute_browser_stub(action_name, action_args)
        else:
            result = _execute_noop(action_name, action_args)

        return {
            **result,
            "executor": executor,
            "target": {
                "url": url,
                "screenshot": screenshot,
                "context": context_payload,
            },
        }

    return _handler

