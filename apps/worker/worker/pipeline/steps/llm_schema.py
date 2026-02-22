from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class TimestampReference(_StrictModel):
    ts_s: int = Field(default=0, ge=0)
    label: str = ""
    reason: str = ""


class CodeSnippet(_StrictModel):
    title: str = ""
    language: str = "text"
    snippet: str = ""
    range_start_s: int = Field(default=0, ge=0)
    range_end_s: int = Field(default=0, ge=0)


class OutlineChapter(_StrictModel):
    chapter_no: int = Field(default=1, ge=1)
    title: str = ""
    anchor: str = ""
    start_s: int = Field(default=0, ge=0)
    end_s: int = Field(default=0, ge=0)
    summary: str = ""
    bullets: list[str] = Field(default_factory=list)
    key_terms: list[str] = Field(default_factory=list)
    code_snippets: list[CodeSnippet] = Field(default_factory=list)


class OutlinePayload(_StrictModel):
    title: str = ""
    tldr: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    risk_or_pitfalls: list[str] = Field(default_factory=list)
    chapters: list[OutlineChapter] = Field(default_factory=list)
    timestamp_references: list[TimestampReference] = Field(default_factory=list)
    generated_by: Literal["gemini"] = "gemini"
    generated_at: str | None = None


class DigestPayload(_StrictModel):
    title: str = ""
    summary: str = ""
    tldr: list[str] = Field(default_factory=list)
    highlights: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    code_blocks: list[CodeSnippet] = Field(default_factory=list)
    timestamp_references: list[TimestampReference] = Field(default_factory=list)
    fallback_notes: list[str] = Field(default_factory=list)
    generated_by: Literal["gemini"] = "gemini"
    generated_at: str | None = None


def outline_response_schema() -> dict:
    return OutlinePayload.model_json_schema()


def digest_response_schema() -> dict:
    return DigestPayload.model_json_schema()
