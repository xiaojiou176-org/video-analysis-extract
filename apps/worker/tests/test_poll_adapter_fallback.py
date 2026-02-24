from __future__ import annotations

from worker.temporal.activities_poll import _resolve_platform, _resolve_video_uid


def test_resolve_platform_uses_normalized_platform_first() -> None:
    platform = _resolve_platform(
        normalized={"video_platform": "youtube"},
        subscription={"platform": "rss_generic"},
    )
    assert platform == "youtube"


def test_resolve_platform_falls_back_to_subscription_platform() -> None:
    platform = _resolve_platform(
        normalized={"video_platform": None},
        subscription={"platform": "rss_generic"},
    )
    assert platform == "rss_generic"


def test_resolve_video_uid_falls_back_to_entry_hash() -> None:
    uid = _resolve_video_uid(normalized={"video_uid": "", "entry_hash": "abc123"})
    assert uid == "abc123"
