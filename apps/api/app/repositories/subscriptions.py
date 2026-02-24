from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Subscription


class SubscriptionsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(
        self,
        *,
        platform: str | None = None,
        category: str | None = None,
        enabled_only: bool = False,
    ) -> list[Subscription]:
        stmt = select(Subscription)
        if platform is not None:
            stmt = stmt.where(Subscription.platform == platform)
        if category is not None:
            stmt = stmt.where(Subscription.category == category)
        if enabled_only:
            stmt = stmt.where(Subscription.enabled.is_(True))
        stmt = stmt.order_by(Subscription.created_at.desc())
        return list(self.db.scalars(stmt).all())

    def upsert(
        self,
        *,
        platform: str,
        source_type: str,
        source_value: str,
        adapter_type: str,
        source_url: str | None,
        rsshub_route: str,
        category: str,
        tags: list[str],
        priority: int,
        enabled: bool,
    ) -> tuple[Subscription, bool]:
        stmt = select(Subscription).where(
            Subscription.platform == platform,
            Subscription.source_type == source_type,
            Subscription.source_value == source_value,
        )
        existing = self.db.scalar(stmt)
        created = existing is None

        if existing is None:
            existing = Subscription(
                platform=platform,
                source_type=source_type,
                source_value=source_value,
                adapter_type=adapter_type,
                source_url=source_url,
                rsshub_route=rsshub_route,
                category=category,
                tags=tags,
                priority=priority,
                enabled=enabled,
            )
            self.db.add(existing)
        else:
            existing.adapter_type = adapter_type
            existing.source_url = source_url
            existing.rsshub_route = rsshub_route
            existing.category = category
            existing.tags = tags
            existing.priority = priority
            existing.enabled = enabled

        self.db.commit()
        self.db.refresh(existing)
        return existing, created

    def batch_update_category(
        self,
        *,
        ids: list[uuid.UUID],
        category: str,
    ) -> int:
        if not ids:
            return 0
        stmt = select(Subscription).where(Subscription.id.in_(ids))
        rows = list(self.db.scalars(stmt).all())
        for row in rows:
            row.category = category
        self.db.commit()
        return len(rows)

    def get(self, subscription_id: uuid.UUID) -> Subscription | None:
        return self.db.get(Subscription, subscription_id)

    def delete(self, subscription_id: uuid.UUID) -> bool:
        instance = self.db.get(Subscription, subscription_id)
        if instance is None:
            return False
        self.db.delete(instance)
        self.db.commit()
        return True
