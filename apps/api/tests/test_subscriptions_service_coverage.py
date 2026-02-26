from __future__ import annotations

import uuid
from typing import Any

import pytest

from apps.api.app.services.subscriptions import (
    SubscriptionsService,
    _derive_rsshub_route,
    _resolve_adapter,
    _validate_subscription_source_url,
)


class _RepoStub:
    def __init__(self) -> None:
        self.last_upsert: dict[str, Any] | None = None

    def list(self, **kwargs: Any) -> list[str]:
        return [f"listed:{kwargs['platform']}:{kwargs['category']}:{kwargs['enabled_only']}"]

    def upsert(self, **kwargs: Any) -> tuple[dict[str, Any], bool]:
        self.last_upsert = dict(kwargs)
        return kwargs, True

    def batch_update_category(self, *, ids: list[uuid.UUID], category: str) -> int:
        return len(ids) if category else 0

    def delete(self, _subscription_id: uuid.UUID) -> bool:
        return True


@pytest.mark.parametrize(
    ("url", "field", "message"),
    [
        ("", "source_url", "must not be empty"),
        ("ftp://example.com/feed", "source_url", "must use http or https"),
        ("https:///feed", "source_url", "host is required"),
        ("https://localhost/feed", "source_url", "blocked internal host"),
        ("https://127.0.0.1/feed", "source_url", "blocked internal address"),
    ],
)
def test_validate_subscription_source_url_rejects_invalid_inputs(
    url: str, field: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        _validate_subscription_source_url(url, field_name=field)


def test_validate_subscription_source_url_accepts_public_domain() -> None:
    assert (
        _validate_subscription_source_url(" https://example.com/feed.xml ", field_name="source_url")
        == "https://example.com/feed.xml"
    )


def test_derive_rsshub_route_supports_known_platforms_and_fallback() -> None:
    assert (
        _derive_rsshub_route("youtube", "youtube_channel_id", "UC123") == "/youtube/channel/UC123"
    )
    assert _derive_rsshub_route("bilibili", "bilibili_uid", "777") == "/bilibili/user/video/777"
    assert _derive_rsshub_route("x", "url", "https://x.com/feed") == "https://x.com/feed"
    assert _derive_rsshub_route("x", "other", "value") == "value"


def test_resolve_adapter_covers_generic_route_and_errors() -> None:
    assert _resolve_adapter(
        platform="youtube",
        adapter_type="rss_generic",
        source_type="url",
        source_value="https://example.com/feed.xml",
        source_url=None,
        rsshub_route=None,
    ) == (
        "rss_generic",
        "https://example.com/feed.xml",
        "https://example.com/feed.xml",
    )

    assert _resolve_adapter(
        platform="youtube",
        adapter_type="rsshub_route",
        source_type="youtube_channel_id",
        source_value="UC999",
        source_url="https://example.com/f.xml",
        rsshub_route=None,
    ) == ("rsshub_route", "https://example.com/f.xml", "/youtube/channel/UC999")

    with pytest.raises(ValueError, match="source_url is required"):
        _resolve_adapter(
            platform="youtube",
            adapter_type="rss_generic",
            source_type="url",
            source_value="",
            source_url=None,
            rsshub_route=None,
        )

    with pytest.raises(ValueError, match="adapter_type must be one of"):
        _resolve_adapter(
            platform="youtube",
            adapter_type="bad_adapter",
            source_type="url",
            source_value="https://example.com/feed.xml",
            source_url=None,
            rsshub_route=None,
        )


def test_subscriptions_service_requires_db_when_repo_missing() -> None:
    with pytest.raises(ValueError, match="db is required"):
        SubscriptionsService(db=None, repo=None)


def test_subscriptions_service_normalizes_fields_and_delegates_to_repo() -> None:
    repo = _RepoStub()
    service = SubscriptionsService(db=None, repo=repo)

    listed = service.list_subscriptions(platform="youtube", category="Tech", enabled_only=True)
    assert listed == ["listed:youtube:Tech:True"]

    payload, created = service.upsert_subscription(
        platform="youtube",
        source_type="url",
        source_value="https://example.com/feed.xml",
        adapter_type="rss_generic",
        source_url=None,
        rsshub_route=None,
        category="  News ",
        tags=[" A ", "", "B"],
        priority=None,
        enabled=True,
    )

    assert created is True
    assert payload["category"] == "news"
    assert payload["tags"] == ["A", "B"]
    assert payload["priority"] == 50
    assert repo.last_upsert is not None

    deleted = service.delete_subscription(uuid.uuid4())
    assert deleted is True


def test_subscriptions_service_rejects_out_of_range_priority_and_empty_batch_category() -> None:
    service = SubscriptionsService(db=None, repo=_RepoStub())

    with pytest.raises(ValueError, match=r"priority must be in \[0, 100\]"):
        service.upsert_subscription(
            platform="youtube",
            source_type="youtube_channel_id",
            source_value="UC123",
            adapter_type="rsshub_route",
            source_url=None,
            rsshub_route=None,
            category="misc",
            tags=[],
            priority=101,
            enabled=True,
        )

    with pytest.raises(ValueError, match="category is required"):
        service.batch_update_category(ids=[uuid.uuid4()], category="   ")

    updated = service.batch_update_category(ids=[uuid.uuid4(), uuid.uuid4()], category="  SPORTS ")
    assert updated == 2
