from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import get_db
from ..security import require_write_access, sanitize_exception_detail
from ..services import SubscriptionsService
from ..services.source_names import resolve_source_name

router = APIRouter(prefix="/api/v1/subscriptions", tags=["subscriptions"])


class SubscriptionUpsertRequest(BaseModel):
    platform: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_value: str = Field(min_length=1)
    adapter_type: str = "rsshub_route"
    source_url: str | None = None
    rsshub_route: str | None = None
    category: str = "misc"
    tags: list[str] = Field(default_factory=list)
    priority: int = Field(default=50, ge=0, le=100)
    enabled: bool = True


class SubscriptionResponse(BaseModel):
    id: uuid.UUID
    platform: str
    source_type: str
    source_value: str
    source_name: str
    adapter_type: str = "rsshub_route"
    source_url: str | None = None
    rsshub_route: str
    category: str = "misc"
    tags: list[str] = Field(default_factory=list)
    priority: int = 50
    enabled: bool
    created_at: datetime
    updated_at: datetime


def _to_subscription_response(row) -> SubscriptionResponse:
    source_type = str(getattr(row, "source_type", "") or "")
    source_value = str(getattr(row, "source_value", "") or "")
    return SubscriptionResponse(
        id=row.id,
        platform=row.platform,
        source_type=source_type,
        source_value=source_value,
        source_name=resolve_source_name(source_type=source_type, source_value=source_value, fallback=source_value),
        adapter_type=getattr(row, "adapter_type", "rsshub_route"),
        source_url=getattr(row, "source_url", None),
        rsshub_route=row.rsshub_route,
        category=getattr(row, "category", "misc"),
        tags=list(getattr(row, "tags", []) or []),
        priority=int(getattr(row, "priority", 50) or 50),
        enabled=row.enabled,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SubscriptionUpsertResponse(BaseModel):
    subscription: SubscriptionResponse
    created: bool


class BatchUpdateCategoryRequest(BaseModel):
    ids: list[uuid.UUID] = Field(default_factory=list)
    category: str = Field(min_length=1)


class BatchUpdateCategoryResponse(BaseModel):
    updated: int


@router.get("", response_model=list[SubscriptionResponse])
def list_subscriptions(
    platform: str | None = None,
    category: str | None = None,
    enabled_only: bool = Query(default=False),
    db: Session = Depends(get_db),
):
    service = SubscriptionsService(db)
    rows = service.list_subscriptions(platform=platform, category=category, enabled_only=enabled_only)
    return [_to_subscription_response(row) for row in rows]


@router.post(
    "",
    response_model=SubscriptionUpsertResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_write_access)],
)
def upsert_subscription(payload: SubscriptionUpsertRequest, db: Session = Depends(get_db)):
    service = SubscriptionsService(db)
    try:
        row, created = service.upsert_subscription(
            platform=payload.platform,
            source_type=payload.source_type,
            source_value=payload.source_value,
            adapter_type=payload.adapter_type,
            source_url=payload.source_url,
            rsshub_route=payload.rsshub_route,
            category=payload.category,
            tags=payload.tags,
            priority=payload.priority,
            enabled=payload.enabled,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=sanitize_exception_detail(exc)) from exc

    return SubscriptionUpsertResponse(
        subscription=_to_subscription_response(row),
        created=created,
    )


@router.post(
    "/batch-update-category",
    response_model=BatchUpdateCategoryResponse,
    dependencies=[Depends(require_write_access)],
)
def batch_update_category(payload: BatchUpdateCategoryRequest, db: Session = Depends(get_db)):
    service = SubscriptionsService(db)
    try:
        updated = service.batch_update_category(ids=payload.ids, category=payload.category)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=sanitize_exception_detail(exc)) from exc
    return BatchUpdateCategoryResponse(updated=updated)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_write_access)])
def delete_subscription(id: uuid.UUID, db: Session = Depends(get_db)):
    service = SubscriptionsService(db)
    deleted = service.delete_subscription(id)
    if not deleted:
        raise HTTPException(status_code=404, detail="subscription not found")
