from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

import pytest
from fastapi.routing import APIRoute
from pydantic import TypeAdapter

# Keep imports aligned with API test bootstrap so router modules can be imported standalone.
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")
os.environ.setdefault("TEMPORAL_TARGET_HOST", "127.0.0.1:7233")
os.environ.setdefault("TEMPORAL_NAMESPACE", "default")
os.environ.setdefault("TEMPORAL_TASK_QUEUE", "video-analysis-worker")
os.environ.setdefault(
    "SQLITE_STATE_PATH",
    os.path.join(tempfile.gettempdir(), "video-digestor-mock-contract-tests.db"),
)

PROJECT_ROOT = Path(__file__).resolve().parents[3]
E2E_TESTS_ROOT = PROJECT_ROOT / "apps" / "web" / "tests" / "e2e"
if str(E2E_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(E2E_TESTS_ROOT))

artifacts = importlib.import_module("apps.api.app.routers.artifacts")
ingest = importlib.import_module("apps.api.app.routers.ingest")
jobs = importlib.import_module("apps.api.app.routers.jobs")
notifications = importlib.import_module("apps.api.app.routers.notifications")
subscriptions = importlib.import_module("apps.api.app.routers.subscriptions")
videos = importlib.import_module("apps.api.app.routers.videos")

mock_api = importlib.import_module("support.mock_api")
MockApiServer = mock_api.MockApiServer
MockApiState = mock_api.MockApiState
start_mock_api_server = mock_api.start_mock_api_server
stop_mock_api_server = mock_api.stop_mock_api_server


def _json_request(
    base_url: str, method: str, path: str, payload: dict[str, Any] | None = None
) -> tuple[int, Any]:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{base_url}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    with urlopen(request, timeout=10) as response:  # nosec B310 - local test server only
        raw = response.read()
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return response.status, json.loads(raw.decode("utf-8") or "null")
        return response.status, raw.decode("utf-8")


def _route_status(router, method: str, route_path: str) -> int:
    for route in router.routes:
        if not isinstance(route, APIRoute):
            continue
        if method.upper() in route.methods and route.path == route_path:
            return int(route.status_code or 200)
    raise AssertionError(f"Route not found: {method} {router.prefix}{route_path}")


def _validate_model(model_cls: type, payload: Any) -> None:
    model_cls.model_validate(payload)


def _validate_list(item_model_cls: type, payload: Any) -> None:
    TypeAdapter(list[item_model_cls]).validate_python(payload)


@dataclass(frozen=True)
class ContractCase:
    name: str
    method: str
    mock_path: str
    payload: dict[str, Any] | None
    router: Any
    router_path: str
    validator: Callable[[Any], None]


CONTRACT_CASES: tuple[ContractCase, ...] = (
    ContractCase(
        name="subscriptions-list",
        method="GET",
        mock_path="/api/v1/subscriptions",
        payload=None,
        router=subscriptions.router,
        router_path="/api/v1/subscriptions",
        validator=lambda body: _validate_list(subscriptions.SubscriptionResponse, body),
    ),
    ContractCase(
        name="subscriptions-upsert",
        method="POST",
        mock_path="/api/v1/subscriptions",
        payload={
            "platform": "youtube",
            "source_type": "url",
            "source_value": "https://youtube.com/@contract-check",
            "rsshub_route": "/youtube/channel/contract-check",
            "enabled": True,
        },
        router=subscriptions.router,
        router_path="/api/v1/subscriptions",
        validator=lambda body: _validate_model(subscriptions.SubscriptionUpsertResponse, body),
    ),
    ContractCase(
        name="notifications-config-get",
        method="GET",
        mock_path="/api/v1/notifications/config",
        payload=None,
        router=notifications.router,
        router_path="/api/v1/notifications/config",
        validator=lambda body: _validate_model(notifications.NotificationConfigResponse, body),
    ),
    ContractCase(
        name="notifications-config-put",
        method="PUT",
        mock_path="/api/v1/notifications/config",
        payload={
            "enabled": True,
            "to_email": "ops-contract@example.com",
            "daily_digest_enabled": True,
            "daily_digest_hour_utc": 6,
            "failure_alert_enabled": True,
        },
        router=notifications.router,
        router_path="/api/v1/notifications/config",
        validator=lambda body: _validate_model(notifications.NotificationConfigResponse, body),
    ),
    ContractCase(
        name="notifications-test-send",
        method="POST",
        mock_path="/api/v1/notifications/test",
        payload={
            "to_email": "qa-contract@example.com",
            "subject": "contract-test",
            "body": "contract check",
        },
        router=notifications.router,
        router_path="/api/v1/notifications/test",
        validator=lambda body: _validate_model(notifications.NotificationSendResponse, body),
    ),
    ContractCase(
        name="ingest-poll",
        method="POST",
        mock_path="/api/v1/ingest/poll",
        payload={"max_new_videos": 50},
        router=ingest.router,
        router_path="/api/v1/ingest/poll",
        validator=lambda body: _validate_model(ingest.IngestPollResponse, body),
    ),
    ContractCase(
        name="videos-list",
        method="GET",
        mock_path="/api/v1/videos",
        payload=None,
        router=videos.router,
        router_path="/api/v1/videos",
        validator=lambda body: _validate_list(videos.VideoResponse, body),
    ),
    ContractCase(
        name="videos-process",
        method="POST",
        mock_path="/api/v1/videos/process",
        payload={
            "video": {"platform": "youtube", "url": "https://www.youtube.com/watch?v=contract001"},
            "mode": "text_only",
            "overrides": {},
            "force": False,
        },
        router=videos.router,
        router_path="/api/v1/videos/process",
        validator=lambda body: _validate_model(videos.VideoProcessResponse, body),
    ),
    ContractCase(
        name="jobs-get",
        method="GET",
        mock_path="/api/v1/jobs/00000000-0000-4000-8000-000000000001",
        payload=None,
        router=jobs.router,
        router_path="/api/v1/jobs/{job_id}",
        validator=lambda body: _validate_model(jobs.JobResponse, body),
    ),
    ContractCase(
        name="artifact-markdown-with-meta",
        method="GET",
        mock_path="/api/v1/artifacts/markdown?job_id=00000000-0000-4000-8000-000000000001&include_meta=true",
        payload=None,
        router=artifacts.router,
        router_path="/api/v1/artifacts/markdown",
        validator=lambda body: _validate_model(artifacts.MarkdownArtifactMetaResponse, body),
    ),
)


@pytest.fixture(scope="module")
def mock_api_server() -> MockApiServer:
    running = start_mock_api_server()
    try:
        yield running.api_server
    finally:
        stop_mock_api_server(running)


@pytest.fixture(autouse=True)
def _reset_mock_state(mock_api_server: MockApiServer) -> MockApiState:
    mock_api_server.state.reset()
    return mock_api_server.state


@pytest.mark.parametrize("case", CONTRACT_CASES, ids=lambda case: case.name)
def test_e2e_mock_contract_matches_api_router_key_fields(
    case: ContractCase, mock_api_server: MockApiServer
) -> None:
    expected_status = _route_status(case.router, case.method, case.router_path)
    actual_status, payload = _json_request(
        mock_api_server.base_url,
        case.method,
        case.mock_path,
        payload=case.payload,
    )

    assert actual_status == expected_status
    case.validator(payload)


def test_e2e_mock_contract_delete_subscription_status(mock_api_server: MockApiServer) -> None:
    _, created_payload = _json_request(
        mock_api_server.base_url,
        "POST",
        "/api/v1/subscriptions",
        payload={
            "platform": "youtube",
            "source_type": "url",
            "source_value": "https://youtube.com/@contract-delete",
            "rsshub_route": "/youtube/channel/contract-delete",
            "enabled": True,
        },
    )
    subscription_id = created_payload["subscription"]["id"]
    uuid.UUID(subscription_id)

    expected_status = _route_status(subscriptions.router, "DELETE", "/api/v1/subscriptions/{id}")
    delete_status, delete_payload = _json_request(
        mock_api_server.base_url,
        "DELETE",
        f"/api/v1/subscriptions/{subscription_id}",
    )

    assert delete_status == expected_status
    assert delete_payload == ""
