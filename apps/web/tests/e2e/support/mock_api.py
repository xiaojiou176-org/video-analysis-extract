from __future__ import annotations

import base64
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, urlparse

from support.runtime_utils import free_port, utc_now, wait_http_ok

PING_IMAGE_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9sYfA8kAAAAASUVORK5CYII="
)

MOCK_JOB_ID = "00000000-0000-4000-8000-000000000001"
MOCK_VIDEO_ID = "00000000-0000-4000-8000-000000000002"
MOCK_VIDEO_DB_ID = "00000000-0000-4000-8000-000000000003"
MOCK_DELIVERY_ID = "00000000-0000-4000-8000-000000000004"
SUBSCRIPTION_NAMESPACE = uuid.UUID("00000000-0000-4000-8000-0000000000aa")


def _is_valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, TypeError):
        return False


def _subscription_uuid(index: int) -> str:
    return str(uuid.uuid5(SUBSCRIPTION_NAMESPACE, f"mock-subscription-{index}"))


@dataclass
class MockApiState:
    lock: threading.Lock = field(default_factory=threading.Lock)
    subscriptions: list[dict[str, Any]] = field(default_factory=list)
    notification_config: dict[str, Any] = field(default_factory=dict)
    calls: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    job_id: str = MOCK_JOB_ID
    health_status: int = int(HTTPStatus.OK)
    health_delay_seconds: float = 0.0
    artifact_frame_files: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        with self.lock:
            now = utc_now()
            self.subscriptions = []
            self.notification_config = {
                "enabled": True,
                "to_email": "ops@example.com",
                "daily_digest_enabled": False,
                "daily_digest_hour_utc": None,
                "failure_alert_enabled": True,
                "category_rules": {},
                "created_at": now,
                "updated_at": now,
            }
            self.calls = {
                "http": [],
                "poll_ingest": [],
                "process_video": [],
                "upsert_subscription": [],
                "delete_subscription": [],
                "update_notification_config": [],
                "send_notification_test": [],
                "get_job": [],
                "get_artifact_markdown": [],
            }
            self.health_status = int(HTTPStatus.OK)
            self.health_delay_seconds = 0.0
            self.artifact_frame_files = ["screenshots/frame_0001.png", "screenshots/frame_0002.webp"]

    def record(self, key: str, payload: dict[str, Any]) -> None:
        with self.lock:
            self.calls[key].append(payload)

    def call_count(self, key: str) -> int:
        with self.lock:
            return len(self.calls[key])

    def last_call(self, key: str) -> dict[str, Any]:
        with self.lock:
            return dict(self.calls[key][-1])

    def current_job(self) -> dict[str, Any]:
        now = utc_now()
        return {
            "id": self.job_id,
            "video_id": MOCK_VIDEO_ID,
            "kind": "video_digest_v1",
            "status": "succeeded",
            "idempotency_key": "idem-e2e",
            "error_message": None,
            "artifact_digest_md": "artifacts/digest.md",
            "artifact_root": f"artifacts/{self.job_id}",
            "created_at": now,
            "updated_at": now,
            "step_summary": [
                {
                    "name": "fetch_transcript",
                    "status": "succeeded",
                    "attempt": 1,
                    "started_at": now,
                    "finished_at": now,
                    "error": None,
                },
                {
                    "name": "generate_markdown",
                    "status": "succeeded",
                    "attempt": 1,
                    "started_at": now,
                    "finished_at": now,
                    "error": None,
                },
            ],
            "steps": [],
            "degradations": [],
            "pipeline_final_status": "succeeded",
            "artifacts_index": {
                "digest_markdown": "artifacts/digest.md",
                "shots_zip": "artifacts/screenshots.zip",
            },
            "mode": "text_only",
        }

    def artifact_payload(self) -> dict[str, Any]:
        with self.lock:
            frame_files = list(self.artifact_frame_files)
        return {
            "markdown": "# Digest Summary\n\n- Key finding A\n- Key finding B\n",
            "meta": {
                "frame_files": frame_files,
                "job": {"id": self.job_id},
            },
        }


@dataclass(frozen=True)
class MockApiServer:
    base_url: str
    state: MockApiState


@dataclass(frozen=True)
class RunningMockServer:
    server: ThreadingHTTPServer
    thread: threading.Thread
    api_server: MockApiServer


def _mock_handler(state: MockApiState) -> type[BaseHTTPRequestHandler]:
    class MockHandler(BaseHTTPRequestHandler):
        server_version = "MockVDAPI/1.0"

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
            return

        def _send_json(self, status: int, payload: Any) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, status: int, body: str, content_type: str = "text/plain; charset=utf-8") -> None:
            raw = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _send_binary(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_no_content(self) -> None:
            self.send_response(HTTPStatus.NO_CONTENT)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def _read_json(self) -> dict[str, Any]:
            raw_size = self.headers.get("Content-Length", "0")
            size = int(raw_size) if raw_size.isdigit() else 0
            if size <= 0:
                return {}
            raw = self.rfile.read(size).decode("utf-8")
            payload = json.loads(raw)
            return payload if isinstance(payload, dict) else {}

        def _record_http(
            self,
            *,
            method: str,
            path: str,
            query: str,
            status: int,
            payload: dict[str, Any] | None = None,
        ) -> None:
            state.record(
                "http",
                {
                    "method": method,
                    "path": path,
                    "query": query,
                    "status": status,
                    "payload": payload,
                },
            )

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)

            if path == "/api/v1/subscriptions":
                with state.lock:
                    subscriptions = list(state.subscriptions)
                self._record_http(
                    method="GET",
                    path=path,
                    query=parsed.query,
                    status=int(HTTPStatus.OK),
                )
                self._send_json(HTTPStatus.OK, subscriptions)
                return

            if path == "/healthz":
                with state.lock:
                    delay_seconds = state.health_delay_seconds
                    status_code = state.health_status
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
                status = HTTPStatus(status_code)
                self._record_http(
                    method="GET",
                    path=path,
                    query=parsed.query,
                    status=int(status),
                )
                self._send_json(status, {"status": "ok" if status == HTTPStatus.OK else "degraded"})
                return

            if path == "/api/v1/videos":
                now = utc_now()
                videos = [
                    {
                        "id": MOCK_VIDEO_ID,
                        "platform": "youtube",
                        "video_uid": "yt-e2e-001",
                        "source_url": "https://youtube.com/watch?v=e2e001",
                        "title": "E2E Demo",
                        "published_at": now,
                        "first_seen_at": now,
                        "last_seen_at": now,
                        "status": "running",
                        "last_job_id": state.job_id,
                    }
                ]
                self._record_http(
                    method="GET",
                    path=path,
                    query=parsed.query,
                    status=int(HTTPStatus.OK),
                )
                self._send_json(HTTPStatus.OK, videos)
                return

            if path.startswith("/api/v1/jobs/"):
                requested_job_id = path.rsplit("/", 1)[-1]
                if not _is_valid_uuid(requested_job_id):
                    self._record_http(
                        method="GET",
                        path=path,
                        query=parsed.query,
                        status=int(HTTPStatus.UNPROCESSABLE_ENTITY),
                    )
                    self._send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "job_id must be a valid UUID"})
                    return
                state.record("get_job", {"job_id": requested_job_id})
                if requested_job_id != state.job_id:
                    self._record_http(
                        method="GET",
                        path=path,
                        query=parsed.query,
                        status=int(HTTPStatus.NOT_FOUND),
                    )
                    self._send_json(HTTPStatus.NOT_FOUND, {"detail": "job not found"})
                    return
                self._record_http(
                    method="GET",
                    path=path,
                    query=parsed.query,
                    status=int(HTTPStatus.OK),
                )
                self._send_json(HTTPStatus.OK, state.current_job())
                return

            if path == "/api/v1/artifacts/markdown":
                job_id = query.get("job_id", [""])[0]
                video_url = query.get("video_url", [""])[0]
                if not job_id and not video_url:
                    self._record_http(
                        method="GET",
                        path=path,
                        query=parsed.query,
                        status=int(HTTPStatus.BAD_REQUEST),
                    )
                    self._send_json(HTTPStatus.BAD_REQUEST, {"detail": "either job_id or video_url is required"})
                    return
                if job_id and not _is_valid_uuid(job_id):
                    self._record_http(
                        method="GET",
                        path=path,
                        query=parsed.query,
                        status=int(HTTPStatus.UNPROCESSABLE_ENTITY),
                    )
                    self._send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "job_id must be a valid UUID"})
                    return
                state.record(
                    "get_artifact_markdown",
                    {
                        "job_id": job_id,
                        "video_url": video_url,
                        "include_meta": query.get("include_meta", [""])[0],
                    },
                )
                include_meta = query.get("include_meta", ["false"])[0].lower() == "true"
                payload = state.artifact_payload()
                if include_meta:
                    self._record_http(
                        method="GET",
                        path=path,
                        query=parsed.query,
                        status=int(HTTPStatus.OK),
                    )
                    self._send_json(HTTPStatus.OK, payload)
                    return
                self._record_http(
                    method="GET",
                    path=path,
                    query=parsed.query,
                    status=int(HTTPStatus.OK),
                )
                self._send_text(HTTPStatus.OK, payload["markdown"], "text/markdown; charset=utf-8")
                return

            if path == "/api/v1/artifacts/assets":
                job_id = query.get("job_id", [""])[0]
                path_param = query.get("path", [""])[0]
                if not job_id or not path_param:
                    self._record_http(
                        method="GET",
                        path=path,
                        query=parsed.query,
                        status=int(HTTPStatus.UNPROCESSABLE_ENTITY),
                    )
                    self._send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "job_id and path are required"})
                    return
                if not _is_valid_uuid(job_id):
                    self._record_http(
                        method="GET",
                        path=path,
                        query=parsed.query,
                        status=int(HTTPStatus.UNPROCESSABLE_ENTITY),
                    )
                    self._send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "job_id must be a valid UUID"})
                    return
                if job_id != state.job_id:
                    self._record_http(
                        method="GET",
                        path=path,
                        query=parsed.query,
                        status=int(HTTPStatus.NOT_FOUND),
                    )
                    self._send_json(HTTPStatus.NOT_FOUND, {"detail": "artifact asset not found"})
                    return
                path_param = path_param.lower()
                if path_param.endswith(".webp"):
                    self._record_http(
                        method="GET",
                        path=path,
                        query=parsed.query,
                        status=int(HTTPStatus.OK),
                    )
                    self._send_binary(HTTPStatus.OK, PING_IMAGE_BYTES, "image/webp")
                    return
                if path_param.endswith(".jpg") or path_param.endswith(".jpeg"):
                    self._record_http(
                        method="GET",
                        path=path,
                        query=parsed.query,
                        status=int(HTTPStatus.OK),
                    )
                    self._send_binary(HTTPStatus.OK, PING_IMAGE_BYTES, "image/jpeg")
                    return
                self._record_http(
                    method="GET",
                    path=path,
                    query=parsed.query,
                    status=int(HTTPStatus.OK),
                )
                self._send_binary(HTTPStatus.OK, PING_IMAGE_BYTES, "image/png")
                return

            if path == "/api/v1/notifications/config":
                with state.lock:
                    notification_config = dict(state.notification_config)
                self._record_http(
                    method="GET",
                    path=path,
                    query=parsed.query,
                    status=int(HTTPStatus.OK),
                )
                self._send_json(HTTPStatus.OK, notification_config)
                return

            self._record_http(
                method="GET",
                path=path,
                query=parsed.query,
                status=int(HTTPStatus.NOT_FOUND),
            )
            self._send_json(HTTPStatus.NOT_FOUND, {"detail": f"Unhandled GET path: {path}"})

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            payload = self._read_json()

            if path == "/api/v1/ingest/poll":
                state.record("poll_ingest", payload)
                self._record_http(
                    method="POST",
                    path=path,
                    query=parsed.query,
                    status=int(HTTPStatus.ACCEPTED),
                    payload=payload,
                )
                self._send_json(HTTPStatus.ACCEPTED, {"enqueued": 2, "candidates": []})
                return

            if path == "/api/v1/videos/process":
                state.record("process_video", payload)
                response = {
                    "job_id": state.job_id,
                    "video_db_id": MOCK_VIDEO_DB_ID,
                    "video_uid": "yt-e2e-001",
                    "status": "queued",
                    "idempotency_key": "idem-e2e",
                    "mode": payload.get("mode", "full"),
                    "overrides": payload.get("overrides", {}),
                    "force": bool(payload.get("force", False)),
                    "reused": False,
                    "workflow_id": "wf-e2e-001",
                }
                self._record_http(
                    method="POST",
                    path=path,
                    query=parsed.query,
                    status=int(HTTPStatus.ACCEPTED),
                    payload=payload,
                )
                self._send_json(HTTPStatus.ACCEPTED, response)
                return

            if path == "/api/v1/subscriptions":
                state.record("upsert_subscription", payload)
                now = utc_now()
                with state.lock:
                    new_id = _subscription_uuid(len(state.subscriptions) + 1)
                    subscription = {
                        "id": new_id,
                        "platform": payload.get("platform", "youtube"),
                        "source_type": payload.get("source_type", "url"),
                        "source_value": payload.get("source_value", ""),
                        "source_name": payload.get("source_name") or payload.get("source_value", ""),
                        "adapter_type": payload.get("adapter_type") or "rsshub_route",
                        "source_url": payload.get("source_url"),
                        "rsshub_route": payload.get("rsshub_route") or "",
                        "category": payload.get("category") or "misc",
                        "tags": payload.get("tags") or [],
                        "priority": int(payload.get("priority", 50) or 50),
                        "enabled": bool(payload.get("enabled", False)),
                        "created_at": now,
                        "updated_at": now,
                    }
                    state.subscriptions.append(subscription)
                self._record_http(
                    method="POST",
                    path=path,
                    query=parsed.query,
                    status=int(HTTPStatus.OK),
                    payload=payload,
                )
                self._send_json(HTTPStatus.OK, {"subscription": subscription, "created": True})
                return

            if path == "/api/v1/notifications/test":
                state.record("send_notification_test", payload)
                now = utc_now()
                to_email = payload.get("to_email") or "ops@example.com"
                self._record_http(
                    method="POST",
                    path=path,
                    query=parsed.query,
                    status=int(HTTPStatus.OK),
                    payload=payload,
                )
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "delivery_id": MOCK_DELIVERY_ID,
                        "status": "sent",
                        "provider_message_id": "provider-001",
                        "error_message": None,
                        "recipient_email": to_email,
                        "subject": payload.get("subject") or "Video Digestor test notification",
                        "sent_at": now,
                        "created_at": now,
                    },
                )
                return

            self._record_http(
                method="POST",
                path=path,
                query=parsed.query,
                status=int(HTTPStatus.NOT_FOUND),
                payload=payload,
            )
            self._send_json(HTTPStatus.NOT_FOUND, {"detail": f"Unhandled POST path: {path}"})

        def do_PUT(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            payload = self._read_json()

            if path == "/api/v1/notifications/config":
                state.record("update_notification_config", payload)
                now = utc_now()
                with state.lock:
                    state.notification_config = {
                        "enabled": bool(payload.get("enabled", False)),
                        "to_email": payload.get("to_email"),
                        "daily_digest_enabled": bool(payload.get("daily_digest_enabled", False)),
                        "daily_digest_hour_utc": payload.get("daily_digest_hour_utc"),
                        "failure_alert_enabled": bool(payload.get("failure_alert_enabled", False)),
                        "category_rules": payload.get("category_rules") or {},
                        "created_at": state.notification_config.get("created_at", now),
                        "updated_at": now,
                    }
                    response = dict(state.notification_config)
                self._record_http(
                    method="PUT",
                    path=path,
                    query=parsed.query,
                    status=int(HTTPStatus.OK),
                    payload=payload,
                )
                self._send_json(HTTPStatus.OK, response)
                return

            self._record_http(
                method="PUT",
                path=path,
                query=parsed.query,
                status=int(HTTPStatus.NOT_FOUND),
                payload=payload,
            )
            self._send_json(HTTPStatus.NOT_FOUND, {"detail": f"Unhandled PUT path: {path}"})

        def do_DELETE(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            if path.startswith("/api/v1/subscriptions/"):
                subscription_id = path.rsplit("/", 1)[-1]
                if not _is_valid_uuid(subscription_id):
                    self._record_http(
                        method="DELETE",
                        path=path,
                        query=parsed.query,
                        status=int(HTTPStatus.UNPROCESSABLE_ENTITY),
                    )
                    self._send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "subscription id must be a valid UUID"})
                    return
                state.record("delete_subscription", {"id": subscription_id})
                with state.lock:
                    before = len(state.subscriptions)
                    state.subscriptions = [item for item in state.subscriptions if item["id"] != subscription_id]
                    deleted = len(state.subscriptions) != before
                if not deleted:
                    self._record_http(
                        method="DELETE",
                        path=path,
                        query=parsed.query,
                        status=int(HTTPStatus.NOT_FOUND),
                    )
                    self._send_json(HTTPStatus.NOT_FOUND, {"detail": "subscription not found"})
                    return
                self._record_http(
                    method="DELETE",
                    path=path,
                    query=parsed.query,
                    status=int(HTTPStatus.NO_CONTENT),
                )
                self._send_no_content()
                return

            self._record_http(
                method="DELETE",
                path=path,
                query=parsed.query,
                status=int(HTTPStatus.NOT_FOUND),
            )
            self._send_json(HTTPStatus.NOT_FOUND, {"detail": f"Unhandled DELETE path: {path}"})

    return MockHandler


def start_mock_api_server() -> RunningMockServer:
    port = free_port()
    state = MockApiState()
    server = ThreadingHTTPServer(("127.0.0.1", port), _mock_handler(state))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    wait_http_ok(f"{base_url}/api/v1/subscriptions")
    return RunningMockServer(server=server, thread=thread, api_server=MockApiServer(base_url=base_url, state=state))


def stop_mock_api_server(running: RunningMockServer) -> None:
    running.server.shutdown()
    running.server.server_close()
    running.thread.join(timeout=5)


def seed_subscription(state: MockApiState, subscription_id: str, source_value: str) -> None:
    if not _is_valid_uuid(subscription_id):
        raise ValueError("subscription_id must be a valid UUID")
    now = utc_now()
    with state.lock:
        state.subscriptions = [
            {
                "id": subscription_id,
                "platform": "youtube",
                "source_type": "url",
                "source_value": source_value,
                "source_name": source_value,
                "adapter_type": "rsshub_route",
                "source_url": None,
                "rsshub_route": "/youtube/channel/seeded",
                "category": "misc",
                "tags": [],
                "priority": 50,
                "enabled": True,
                "created_at": now,
                "updated_at": now,
            }
        ]
