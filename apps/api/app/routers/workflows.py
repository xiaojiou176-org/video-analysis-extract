from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])


class WorkflowRunRequest(BaseModel):
    workflow: str = Field(pattern=r"^(poll_feeds|daily_digest|notification_retry|cleanup|provider_canary)$")
    run_once: bool = True
    wait_for_result: bool = False
    workflow_id: str | None = None
    payload: dict = Field(default_factory=dict)


class WorkflowRunResponse(BaseModel):
    workflow: str
    workflow_name: str
    workflow_id: str
    run_id: str | None = None
    status: str
    started_at: datetime
    result: dict | None = None


_WORKFLOW_NAME_MAP = {
    "poll_feeds": "PollFeedsWorkflow",
    "daily_digest": "DailyDigestWorkflow",
    "notification_retry": "NotificationRetryWorkflow",
    "cleanup": "CleanupWorkspaceWorkflow",
    "provider_canary": "ProviderCanaryWorkflow",
}


@router.post("/run", response_model=WorkflowRunResponse)
async def run_workflow(payload: WorkflowRunRequest, db: Session = Depends(get_db)):
    del db  # reserved for future authorization / audit persistence

    try:
        from temporalio.client import Client
        from temporalio.exceptions import WorkflowAlreadyStartedError
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=503, detail=f"temporal client not available: {exc}") from exc

    workflow_name = _WORKFLOW_NAME_MAP[payload.workflow]
    request_payload = dict(payload.payload or {})
    request_payload.setdefault("run_once", payload.run_once)

    workflow_id = payload.workflow_id or f"api-{payload.workflow}-{uuid4()}"
    if not payload.run_once and payload.workflow_id is None:
        workflow_id = f"{payload.workflow}-workflow"

    try:
        client = await Client.connect(
            settings.temporal_target_host,
            namespace=settings.temporal_namespace,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"failed to connect temporal: {exc}") from exc

    try:
        handle = await client.start_workflow(
            workflow_name,
            request_payload,
            id=workflow_id,
            task_queue=settings.temporal_task_queue,
        )
    except WorkflowAlreadyStartedError:
        return WorkflowRunResponse(
            workflow=payload.workflow,
            workflow_name=workflow_name,
            workflow_id=workflow_id,
            status="already_running",
            started_at=datetime.utcnow(),
            result=None,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"failed to start workflow: {exc}") from exc

    run_id = getattr(handle, "first_execution_run_id", None) or getattr(handle, "run_id", None)

    if payload.wait_for_result:
        try:
            result = await handle.result()
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"workflow execution failed: {exc}") from exc
        return WorkflowRunResponse(
            workflow=payload.workflow,
            workflow_name=workflow_name,
            workflow_id=handle.id,
            run_id=run_id,
            status="completed",
            started_at=datetime.utcnow(),
            result=result if isinstance(result, dict) else {"value": result},
        )

    return WorkflowRunResponse(
        workflow=payload.workflow,
        workflow_name=workflow_name,
        workflow_id=handle.id,
        run_id=run_id,
        status="started",
        started_at=datetime.utcnow(),
        result=None,
    )
