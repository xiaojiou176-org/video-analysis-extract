from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..services import SubscriptionsService

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])


class SubscriptionUpsertRequest(BaseModel):
    platform: Literal["bilibili", "youtube"]
    source_type: Literal["bilibili_uid", "youtube_channel_id", "url"]
    source_value: str = Field(min_length=1)
    rsshub_route: str | None = None
    enabled: bool = True


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    platform: Literal["bilibili", "youtube"]
    source_type: Literal["bilibili_uid", "youtube_channel_id", "url"]
    source_value: str
    rsshub_route: str
    enabled: bool
    created_at: datetime
    updated_at: datetime


class SubscriptionUpsertResponse(BaseModel):
    subscription: SubscriptionResponse
    created: bool


@router.get("", response_model=list[SubscriptionResponse])
def list_subscriptions(
    platform: Literal["bilibili", "youtube"] | None = None,
    enabled_only: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    service = SubscriptionsService(db)
    rows = service.list_subscriptions(platform=platform, enabled_only=enabled_only)
    return [
        SubscriptionResponse(
            id=row.id,
            platform=row.platform,
            source_type=row.source_type,
            source_value=row.source_value,
            rsshub_route=row.rsshub_route,
            enabled=row.enabled,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.post("", response_model=SubscriptionUpsertResponse, status_code=status.HTTP_200_OK)
def upsert_subscription(payload: SubscriptionUpsertRequest, db: Session = Depends(get_db)):
    service = SubscriptionsService(db)
    row, created = service.upsert_subscription(
        platform=payload.platform,
        source_type=payload.source_type,
        source_value=payload.source_value,
        rsshub_route=payload.rsshub_route,
        enabled=payload.enabled,
    )

    return SubscriptionUpsertResponse(
        subscription=SubscriptionResponse(
            id=row.id,
            platform=row.platform,
            source_type=row.source_type,
            source_value=row.source_value,
            rsshub_route=row.rsshub_route,
            enabled=row.enabled,
            created_at=row.created_at,
            updated_at=row.updated_at,
        ),
        created=created,
    )


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subscription(id: uuid.UUID, db: Session = Depends(get_db)):
    service = SubscriptionsService(db)
    deleted = service.delete_subscription(id)
    if not deleted:
        raise HTTPException(status_code=404, detail="subscription not found")
