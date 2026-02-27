from __future__ import annotations

import argparse
import asyncio
import json
import sys
import types
from types import SimpleNamespace

import pytest
from worker import main as worker_main


def _fake_settings() -> SimpleNamespace:
    return SimpleNamespace(
        temporal_task_queue="video-analysis-worker",
        digest_daily_local_hour=9,
        digest_local_timezone="UTC",
    )


def test_build_parser_supports_all_subcommands() -> None:
    parser = worker_main._build_parser()
    commands = [
        ["run-worker"],
        ["start-poll-workflow", "--platform", "youtube", "--max-new-videos", "12"],
        ["start-process-workflow", "--job-id", "job-1"],
        ["start-daily-workflow", "--run-once", "--local-hour", "8"],
        ["start-notification-retry-workflow", "--interval-minutes", "5"],
        ["start-provider-canary-workflow", "--timeout-seconds", "12"],
        ["start-cleanup-workflow", "--older-than-hours", "6", "--cache-max-size-mb", "256"],
    ]
    for argv in commands:
        ns = parser.parse_args(argv)
        assert ns.command == argv[0]


@pytest.mark.parametrize(
    ("command", "patch_name", "result"),
    [
        ("start-poll-workflow", "start_poll_workflow", {"ok": True, "kind": "poll"}),
        ("start-process-workflow", "start_process_workflow", {"ok": True, "kind": "process"}),
        ("start-daily-workflow", "start_daily_workflow", {"ok": True, "kind": "daily"}),
        (
            "start-notification-retry-workflow",
            "start_notification_retry_workflow",
            {"ok": True, "kind": "retry"},
        ),
        (
            "start-provider-canary-workflow",
            "start_provider_canary_workflow",
            {"ok": True, "kind": "canary"},
        ),
        ("start-cleanup-workflow", "start_cleanup_workflow", {"ok": True, "kind": "cleanup"}),
    ],
)
def test_main_async_dispatches_commands(monkeypatch, capsys, command, patch_name, result) -> None:
    monkeypatch.setattr(worker_main.Settings, "from_env", staticmethod(_fake_settings))

    async def _stub(*_args, **_kwargs):
        return result

    monkeypatch.setattr(worker_main, patch_name, _stub)
    args = argparse.Namespace(
        command=command,
        subscription_id=None,
        platform=None,
        max_new_videos=50,
        job_id="job-1",
        run_once=True,
        local_hour=8,
        timezone_name="UTC",
        timezone_offset_minutes=0,
        workflow_id=f"{command}-id",
        interval_minutes=5,
        retry_batch_limit=10,
        interval_hours=1,
        timeout_seconds=8,
        older_than_hours=24,
        workspace_dir=None,
        cache_dir=None,
        cache_older_than_hours=None,
        cache_max_size_mb=None,
    )

    asyncio.run(worker_main._main_async(args))
    printed = capsys.readouterr().out.strip()
    assert json.loads(printed) == result


def test_main_async_run_worker_branch(monkeypatch) -> None:
    monkeypatch.setattr(worker_main.Settings, "from_env", staticmethod(_fake_settings))
    called = {"value": False}

    async def _run_worker(_settings):
        called["value"] = True

    monkeypatch.setattr(worker_main, "run_temporal_worker", _run_worker)
    args = argparse.Namespace(command="run-worker")
    asyncio.run(worker_main._main_async(args))
    assert called["value"] is True


def test_main_async_unsupported_command_raises(monkeypatch) -> None:
    monkeypatch.setattr(worker_main.Settings, "from_env", staticmethod(_fake_settings))
    with pytest.raises(ValueError, match="Unsupported command"):
        asyncio.run(worker_main._main_async(argparse.Namespace(command="unknown")))


def test_run_temporal_worker_registers_workflows_and_activities(monkeypatch) -> None:
    workflows_mod = types.ModuleType("worker.temporal.workflows")
    activities_mod = types.ModuleType("worker.temporal.activities")
    worker_mod = types.ModuleType("temporalio.worker")

    class _Workflow:
        @staticmethod
        async def run(*_args, **_kwargs):
            return {}

    class _Worker:
        def __init__(self, client, *, task_queue, workflows, activities):
            self.client = client
            self.task_queue = task_queue
            self.workflows = workflows
            self.activities = activities

        async def run(self):
            return None

    workflows_mod.PollFeedsWorkflow = _Workflow
    workflows_mod.ProcessJobWorkflow = _Workflow
    workflows_mod.DailyDigestWorkflow = _Workflow
    workflows_mod.CleanupWorkspaceWorkflow = _Workflow
    workflows_mod.NotificationRetryWorkflow = _Workflow
    workflows_mod.ProviderCanaryWorkflow = _Workflow
    for name in [
        "cleanup_workspace_activity",
        "mark_failed_activity",
        "mark_running_activity",
        "mark_succeeded_activity",
        "poll_feeds_activity",
        "provider_canary_activity",
        "reconcile_stale_queued_jobs_activity",
        "resolve_daily_digest_timing_activity",
        "retry_failed_deliveries_activity",
        "run_pipeline_activity",
        "send_daily_digest_activity",
        "send_video_digest_activity",
    ]:
        setattr(activities_mod, name, lambda *args, **kwargs: {"ok": True})
    worker_mod.Worker = _Worker

    monkeypatch.setitem(sys.modules, "worker.temporal.workflows", workflows_mod)
    monkeypatch.setitem(sys.modules, "worker.temporal.activities", activities_mod)
    monkeypatch.setitem(sys.modules, "temporalio.worker", worker_mod)
    monkeypatch.setattr(worker_main, "_connect_temporal", lambda _settings: asyncio.sleep(0, result=object()))

    asyncio.run(worker_main.run_temporal_worker(_fake_settings()))


def test_poll_and_process_workflow_start_paths(monkeypatch) -> None:
    workflows_mod = types.ModuleType("worker.temporal.workflows")
    common_mod = types.ModuleType("temporalio.common")

    class _Workflow:
        @staticmethod
        async def run(*_args, **_kwargs):
            return {}

    class _Handle:
        async def result(self):
            return {"ok": True}

    class _Client:
        async def start_workflow(self, *_args, **_kwargs):
            return _Handle()

    class _Reuse:
        REJECT_DUPLICATE = "reject"

    class _Conflict:
        USE_EXISTING = "existing"

    workflows_mod.PollFeedsWorkflow = _Workflow
    workflows_mod.ProcessJobWorkflow = _Workflow
    common_mod.WorkflowIDReusePolicy = _Reuse
    common_mod.WorkflowIDConflictPolicy = _Conflict
    monkeypatch.setitem(sys.modules, "worker.temporal.workflows", workflows_mod)
    monkeypatch.setitem(sys.modules, "temporalio.common", common_mod)
    monkeypatch.setattr(worker_main, "_connect_temporal", lambda _settings: asyncio.sleep(0, result=_Client()))

    poll = asyncio.run(worker_main.start_poll_workflow(_fake_settings(), platform="youtube"))
    process = asyncio.run(worker_main.start_process_workflow(_fake_settings(), "job-1"))
    assert poll["ok"] is True
    assert process["ok"] is True


def test_retry_and_canary_workflow_already_started_paths(monkeypatch) -> None:
    exceptions_mod = types.ModuleType("temporalio.exceptions")
    workflows_mod = types.ModuleType("worker.temporal.workflows")

    class WorkflowAlreadyStartedError(Exception):
        pass

    class _Workflow:
        @staticmethod
        async def run(*_args, **_kwargs):
            return {}

    class _Client:
        async def start_workflow(self, *_args, **_kwargs):
            raise WorkflowAlreadyStartedError

    exceptions_mod.WorkflowAlreadyStartedError = WorkflowAlreadyStartedError
    workflows_mod.NotificationRetryWorkflow = _Workflow
    workflows_mod.ProviderCanaryWorkflow = _Workflow
    monkeypatch.setitem(sys.modules, "temporalio.exceptions", exceptions_mod)
    monkeypatch.setitem(sys.modules, "worker.temporal.workflows", workflows_mod)
    monkeypatch.setattr(worker_main, "_connect_temporal", lambda _settings: asyncio.sleep(0, result=_Client()))

    retry = asyncio.run(worker_main.start_notification_retry_workflow(_fake_settings(), run_once=False))
    canary = asyncio.run(worker_main.start_provider_canary_workflow(_fake_settings(), run_once=False))
    assert retry["status"] == "already_running"
    assert canary["status"] == "already_running"
