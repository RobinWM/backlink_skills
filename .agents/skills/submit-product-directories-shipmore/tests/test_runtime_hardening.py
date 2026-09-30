import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from agent_browser_adapter import AgentBrowserAdapter, AgentBrowserError
from final_action_guard import FinalActionJournal, FinalActionError
from lease_keeper import LeaseKeeper, assert_lease_guard_valid, LeaseGuardError
from shipmore_worker import WorkerRuntimeError, run_worker
from worker_identity import (
    WorkerIdentityError,
    WorkerProcessLock,
    get_worker_instance_id,
    worker_id_for_slot,
)


class FakeQueueClient:
    def __init__(self, claims=None, heartbeats=None, worker_id="worker-a"):
        self.claims = list(claims or [])
        self.heartbeats = list(heartbeats or [])
        self.worker_id = worker_id
        self.claim_calls = []
        self.heartbeat_calls = []

    def require_worker_id(self):
        return self.worker_id

    def heartbeat(self, run_item_id, lease_seconds):
        self.heartbeat_calls.append((run_item_id, lease_seconds))
        if self.heartbeats:
            value = self.heartbeats.pop(0)
            if isinstance(value, Exception):
                raise value
            return value
        return {"success": True}

    def claim(self, run_id, lease_seconds):
        self.claim_calls.append((run_id, lease_seconds))
        if not self.claims:
            return {"reason": "queue_empty"}
        return self.claims.pop(0)


class ImmediateChild:
    def __init__(self, code=0):
        self.code = code
    def poll(self):
        return self.code
    def terminate(self):
        self.code = -15


def _write_valid_guard(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "valid": True,
                "reason": "heartbeat_ok",
                "deadlineEpoch": time.time() + 300,
            }
        ),
        encoding="utf-8",
    )


def test_lease_keeper_writes_guard_and_invalidates_on_failure(tmp_path):
    guard = tmp_path / "lease.json"
    client = FakeQueueClient(
        heartbeats=[
            {"success": True},
            {"success": False, "reason": "lease_lost"},
        ]
    )
    keeper = LeaseKeeper(
        client,
        "item-1",
        guard_path=guard,
        interval_seconds=60,
    )
    keeper.heartbeat_once()
    assert assert_lease_guard_valid(guard)["valid"] is True

    with pytest.raises(LeaseGuardError):
        keeper.heartbeat_once()
    with pytest.raises(LeaseGuardError):
        assert_lease_guard_valid(guard)


def test_managed_adapter_blocks_mutation_when_guard_invalid(tmp_path):
    guard = tmp_path / "lease.json"
    guard.write_text(
        json.dumps(
            {"valid": False, "reason": "lease_lost", "deadlineEpoch": time.time()}
        ),
        encoding="utf-8",
    )
    adapter = AgentBrowserAdapter(
        "item-1",
        env={
            "SHIPMORE_MANAGED_LEASE": "1",
            "SHIPMORE_LEASE_GUARD_PATH": str(guard),
            "BACKLINK_WORKER_ID": "worker-a",
        },
        runner=lambda *a, **k: subprocess.CompletedProcess([], 0, "{}", ""),
    )
    with pytest.raises(AgentBrowserError, match="lease"):
        adapter.click("@e1")


def test_final_action_journal_is_local_exactly_once(tmp_path, monkeypatch):
    monkeypatch.setenv("SHIPMORE_FINAL_ACTION_JOURNAL_DIR", str(tmp_path))
    journal = FinalActionJournal("item-1", "submit")
    first = journal.prepare(worker_id="worker-a", session_id="session-a")
    assert first["state"] == "prepared"
    assert first["completionEventId"]

    journal.mark_attempting()
    with pytest.raises(FinalActionError, match="already fenced"):
        FinalActionJournal("item-1", "submit").prepare(
            worker_id="worker-a",
            session_id="session-a",
        )


def test_worker_identity_is_persistent_and_slot_scoped(tmp_path, monkeypatch):
    identity_file = tmp_path / "worker-id"
    monkeypatch.setenv("SHIPMORE_WORKER_ID_FILE", str(identity_file))
    monkeypatch.delenv("SHIPMORE_WORKER_INSTANCE_ID", raising=False)
    first = get_worker_instance_id()
    second = get_worker_instance_id()
    assert first == second
    assert worker_id_for_slot(2) == f"{first}-02"


def test_managed_worker_processes_one_item_then_stops_on_empty(tmp_path, monkeypatch):
    monkeypatch.setenv("SHIPMORE_LEASE_GUARD_DIR", str(tmp_path / "guards"))
    client = FakeQueueClient(
        claims=[
            {"reason": "claimed", "data": {"id": "item-1"}},
            {"reason": "queue_empty"},
        ]
    )
    launched = []

    def popen(command, **kwargs):
        launched.append((command, kwargs["env"]))
        return ImmediateChild(0)

    code = run_worker(
        client,
        run_id="run-1",
        item_command=["processor"],
        heartbeat_interval=60,
        popen_factory=popen,
    )
    assert code == 0
    assert len(launched) == 1
    assert launched[0][1]["SHIPMORE_MANAGED_LEASE"] == "1"
    assert launched[0][1]["SHIPMORE_RUN_ITEM_ID"] == "item-1"


def test_managed_worker_refuses_automatic_second_execution(tmp_path, monkeypatch):
    monkeypatch.setenv("SHIPMORE_LEASE_GUARD_DIR", str(tmp_path / "guards"))
    client = FakeQueueClient(
        claims=[
            {"reason": "claimed", "data": {"id": "item-1"}},
            {"reason": "reused", "data": {"id": "item-1"}},
        ]
    )

    with pytest.raises(WorkerRuntimeError, match="refusing automatic re-execution"):
        run_worker(
            client,
            run_id="run-1",
            item_command=["processor"],
            heartbeat_interval=60,
            popen_factory=lambda command, **kwargs: ImmediateChild(0),
        )


def test_lease_guard_rejects_different_worker(tmp_path):
    guard = tmp_path / "lease.json"
    guard.write_text(
        json.dumps(
            {
                "valid": True,
                "reason": "heartbeat_ok",
                "workerId": "worker-a",
                "deadlineEpoch": time.time() + 300,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(LeaseGuardError, match="another worker"):
        assert_lease_guard_valid(guard, expected_worker_id="worker-b")


def test_final_click_checks_existing_run_item_guard_before_heartbeat(
    tmp_path, monkeypatch
):
    guard = tmp_path / "lease.json"
    guard.write_text(
        json.dumps(
            {
                "valid": True,
                "reason": "heartbeat_ok",
                "workerId": "worker-a",
                "runItemId": "item-1",
                "deadlineEpoch": time.time() + 300,
            }
        ),
        encoding="utf-8",
    )
    called = {"refresh": False}

    def fake_refresh(*args, **kwargs):
        called["refresh"] = True
        return {"success": True}

    monkeypatch.setattr("agent_browser_adapter.refresh_lease_from_env", fake_refresh)
    adapter = AgentBrowserAdapter(
        "item-2",
        env={
            "SHIPMORE_MANAGED_LEASE": "1",
            "SHIPMORE_LEASE_GUARD_PATH": str(guard),
            "BACKLINK_WORKER_ID": "worker-a",
        },
        runner=lambda *a, **k: subprocess.CompletedProcess(
            [], 0, json.dumps({"success": True, "data": {"visible": True}}), ""
        ),
    )
    with pytest.raises(AgentBrowserError, match="another Run Item"):
        adapter.final_click("submit", "@e1")
    assert called["refresh"] is False


def test_worker_process_lock_rejects_duplicate_live_worker(tmp_path, monkeypatch):
    monkeypatch.setenv("SHIPMORE_WORKER_LOCK_DIR", str(tmp_path / "locks"))
    first = WorkerProcessLock("worker-a")
    second = WorkerProcessLock("worker-a")
    first.acquire()
    try:
        with pytest.raises(WorkerIdentityError, match="another live process"):
            second.acquire()
    finally:
        first.release()

    second.acquire()
    second.release()
