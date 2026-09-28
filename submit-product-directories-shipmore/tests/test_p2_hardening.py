import argparse
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import shipmore_queue_client
from agent_browser_adapter import AgentBrowserAdapter, AgentBrowserError
from diagnostic_sanitizer import sanitize_diagnostic
from runtime_cleanup import (
    cleanup_terminal_sessions,
    deterministic_session_id,
    mark_terminal_session,
)
from shipmore_worker_pool import supervise_children


def test_diagnostics_remove_sensitive_headers_bodies_emails_and_url_queries():
    payload = {
        "url": "https://example.com/callback?token=abc#fragment",
        "headers": {
            "Authorization": "Bearer top-secret",
            "Cookie": "session=abc",
            "Accept": "application/json",
        },
        "requestBody": "email=user@example.com&password=hunter2",
        "message": (
            "user=user@example.com token=abc "
            "https://example.com/path?magic=123#frag"
        ),
    }
    safe = sanitize_diagnostic(payload)
    serialized = json.dumps(safe)
    assert "top-secret" not in serialized
    assert "session=abc" not in serialized
    assert "user@example.com" not in serialized
    assert "hunter2" not in serialized
    assert "?token=" not in serialized
    assert "?magic=" not in serialized
    assert safe["headers"]["Accept"] == "application/json"


def test_fresh_task_rejects_existing_restore_state():
    adapter = AgentBrowserAdapter("item-restore")
    session_id = adapter.session_id

    def runner(command, **kwargs):
        joined = " ".join(command)
        stdout = session_id + "\n" if "state list" in joined else ""
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    adapter.runner = runner
    with pytest.raises(AgentBrowserError, match="restore state already exists"):
        adapter.bootstrap("https://example.test", fresh_task=True)


def test_fresh_task_rejects_active_session_without_saved_state():
    adapter = AgentBrowserAdapter("item-active")
    session_id = adapter.session_id

    def runner(command, **kwargs):
        joined = " ".join(command)
        if "state list" in joined:
            stdout = ""
        elif "session list" in joined:
            stdout = session_id + "\n"
        else:
            stdout = "{}"
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")

    adapter.runner = runner
    with pytest.raises(AgentBrowserError, match="already active"):
        adapter.bootstrap("https://example.test", fresh_task=True)


def test_fresh_task_rejects_recovery_mode_without_browser_probe():
    called = []

    def runner(command, **kwargs):
        called.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    adapter = AgentBrowserAdapter(
        "item-recovery",
        env={"SHIPMORE_RECOVERY_MODE": "1"},
        runner=runner,
    )
    with pytest.raises(AgentBrowserError, match="recovery mode"):
        adapter.bootstrap("https://example.test", fresh_task=True)
    assert called == []


def test_terminal_cleanup_only_clears_eligible_records(tmp_path, monkeypatch):
    monkeypatch.setenv("SHIPMORE_TERMINAL_SESSION_DIR", str(tmp_path / "terminal"))
    first = mark_terminal_session(
        "item-old",
        status="completed",
        submission_status="published",
        retention_days=7,
        now=100,
    )
    mark_terminal_session(
        "item-new",
        status="skipped",
        submission_status="duplicate_no_action",
        retention_days=7,
        now=700000,
    )

    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        joined = " ".join(command)
        if "state list" in joined:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=first["sessionId"] + "\n",
                stderr="",
            )
        return subprocess.CompletedProcess(command, 0, stdout="cleared", stderr="")

    result = cleanup_terminal_sessions(
        executable="agent-browser",
        namespace="shipmore",
        now=100 + 8 * 86400,
        runner=runner,
    )
    assert result["success"] is True
    assert result["cleaned"] == ["item-old"]
    assert result["deferred"] == ["item-new"]
    assert len(calls) == 2
    assert calls[1][-3:] == ["state", "clear", first["sessionId"]]


def test_complete_success_registers_terminal_cleanup(monkeypatch):
    captured = {}

    def fake_mark(run_item_id, **kwargs):
        captured["runItemId"] = run_item_id
        captured.update(kwargs)
        return {"success": True}

    monkeypatch.setattr(shipmore_queue_client, "mark_terminal_session", fake_mark)
    client = shipmore_queue_client.ShipmoreQueueClient(
        "https://shipmore.test",
        "token",
        "worker-a",
    )
    client.post = lambda payload, url=None: {"success": True, "reason": "completed"}

    args = SimpleNamespace(
        status="completed",
        last_error=None,
        submission_status="submitted",
        public_listing_url=None,
        retry_diagnostic_json=None,
        event_id="event-1",
        run_item_id="item-1",
        verification_status="not_checked",
        exact_result="submitted",
        evidence_reference=None,
        backend_checked_at=None,
        mailbox_checked_at=None,
        public_page_checked_at=None,
        follow_up_at=None,
        follow_up_note=None,
    )
    result = client.complete(args)
    assert result["success"] is True
    assert captured["runItemId"] == "item-1"
    assert captured["status"] == "completed"
    assert captured["submission_status"] == "submitted"


class FakeChild:
    def __init__(self, code=None):
        self.code = code
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.code

    def terminate(self):
        self.terminated = True
        self.code = -15

    def wait(self, timeout=None):
        return self.code

    def kill(self):
        self.killed = True
        self.code = -9


def test_supervisor_detects_later_slot_failure_without_waiting_for_first():
    slow = FakeChild(None)
    failed = FakeChild(7)
    failures = supervise_children(
        [(1, slow), (2, failed)],
        poll_interval=0,
    )
    assert failures == {2: 7}
    assert slow.terminated is True


def test_supervisor_allows_clean_workers_to_finish():
    first = FakeChild(0)
    second = FakeChild(0)
    assert supervise_children([(1, first), (2, second)], poll_interval=0) == {}


def test_cleanup_session_id_matches_adapter_contract():
    adapter = AgentBrowserAdapter("same-item")
    assert deterministic_session_id("same-item") == adapter.session_id


def test_terminal_cleanup_treats_missing_state_as_already_clean(tmp_path, monkeypatch):
    monkeypatch.setenv("SHIPMORE_TERMINAL_SESSION_DIR", str(tmp_path / "terminal"))
    mark_terminal_session(
        "item-no-state",
        status="skipped",
        submission_status="duplicate_no_action",
        retention_days=0,
        now=100,
    )

    calls = []

    def runner(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    result = cleanup_terminal_sessions(
        executable="agent-browser",
        namespace="shipmore",
        now=101,
        runner=runner,
    )
    assert result["success"] is True
    assert result["cleaned"] == ["item-no-state"]
    assert len(calls) == 1
    assert "state list" in " ".join(calls[0])


def test_pool_launch_failure_terminates_started_workers(monkeypatch):
    import shipmore_worker_pool as pool

    first = FakeChild(None)
    calls = {"count": 0}

    def popen(command, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return first
        raise OSError("boom")

    monkeypatch.setattr(pool.subprocess, "Popen", popen)
    with pytest.raises(ValueError, match="failed to start worker slot 2"):
        pool.run_pool(
            "run-1",
            2,
            "codex",
            ["worker"],
            skip_preflight=True,
        )
    assert first.terminated is True


def test_follow_up_submission_status_is_not_cleanup_eligible(tmp_path, monkeypatch):
    monkeypatch.setenv("SHIPMORE_TERMINAL_SESSION_DIR", str(tmp_path / "terminal"))
    result = mark_terminal_session(
        "item-awaiting",
        status="completed",
        submission_status="awaiting_approval",
        retention_days=0,
        now=100,
    )
    assert result["cleanupEligible"] is False
    assert list((tmp_path / "terminal").glob("*.json")) == []
