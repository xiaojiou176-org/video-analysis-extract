from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from ..repositories import SubscriptionsRepository


def _derive_rsshub_route(platform: str, source_type: str, source_value: str) -> str:
    if source_type == "url":
        return source_value
    if platform == "bilibili" and source_type == "bilibili_uid":
        return f"/bilibili/user/video/{source_value}"
    if platform == "youtube" and source_type == "youtube_channel_id":
        return f"/youtube/channel/{source_value}"
    return source_value


class SubscriptionsService:
    def __init__(self, db: Session) -> None:
        self.repo = SubscriptionsRepository(db)

    def list_subscriptions(self, *, platform: str | None = None, enabled_only: bool = False):
        return self.repo.list(platform=platform, enabled_only=enabled_only)

    def upsert_subscription(
        self,
        *,
        platform: str,
        source_type: str,
        source_value: str,
        rsshub_route: str | None,
        enabled: bool,
    ):
        resolved_route = rsshub_route or _derive_rsshub_route(platform, source_type, source_value)
        return self.repo.upsert(
            platform=platform,
            source_type=source_type,
            source_value=source_value,
            rsshub_route=resolved_route,
            enabled=enabled,
        )

    def delete_subscription(self, subscription_id: uuid.UUID) -> bool:
        return self.repo.delete(subscription_id)
