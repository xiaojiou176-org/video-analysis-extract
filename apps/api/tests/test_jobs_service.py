from __future__ import annotations

from apps.api.app.services.jobs import JobsService


def _service() -> JobsService:
    return JobsService.__new__(JobsService)


def test_extract_thought_metadata_supports_legacy_payload() -> None:
    payload = {
        "thought_metadata": {
            "provider": "gemini",
            "thought_tokens": 42,
            "planner": "legacy_planner",
        }
    }

    metadata = _service()._extract_thought_metadata(payload)

    assert metadata["provider"] == "gemini"
    assert metadata["planner"] == "legacy_planner"
    assert metadata["thinking"]["usage"]["thoughts_token_count"] == 42
    assert metadata["thought_count"] == 0
    assert metadata["thought_signatures"] == []


def test_extract_thought_metadata_supports_llm_meta_thinking_payload() -> None:
    payload = {
        "llm_meta": {
            "provider": "gemini",
            "thinking": {
                "enabled": True,
                "level": "HIGH",
                "include_thoughts": True,
                "thought_count": 2,
                "thought_signatures": ["sig-A", "sig-B"],
                "thought_signature_digest": "digest-1",
                "usage": {"thoughts_token_count": 12, "total_token_count": 144},
            },
        }
    }

    metadata = _service()._extract_thought_metadata(payload)

    assert metadata["provider"] == "gemini"
    assert metadata["thinking"]["enabled"] is True
    assert metadata["thinking"]["level"] == "high"
    assert metadata["thinking"]["include_thoughts"] is True
    assert metadata["thinking"]["thought_count"] == 2
    assert metadata["thought_count"] == 2
    assert metadata["thought_signatures"] == ["sig-A", "sig-B"]
    assert metadata["thought_signature_digest"] == "digest-1"


def test_extract_thought_metadata_returns_empty_structure_when_missing() -> None:
    metadata = _service()._extract_thought_metadata({"result": "ok"})

    assert metadata == {
        "thinking": {
            "enabled": None,
            "level": None,
            "include_thoughts": None,
            "thought_count": 0,
            "thought_signatures": [],
            "thought_signature_digest": None,
            "usage": {},
        },
        "thought_count": 0,
        "thought_signatures": [],
        "thought_signature_digest": None,
    }
