import json
from pathlib import Path
import re
import subprocess
import sys

import pytest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from agent_browser_adapter import (
    AGENT_BROWSER_VERSION,
    AgentBrowserAdapter,
    AgentBrowserError,
    deterministic_session_id,
)
from shipmore_worker_pool import build_worker_env


class FakeRunner:
    def __init__(self, readonly=False):
        self.calls = []
        self.readonly = readonly

    def __call__(self, command, **kwargs):
        self.calls.append(command)
        joined = " ".join(command)
        if "--version" in command:
            stdout = f"agent-browser {AGENT_BROWSER_VERSION}\n"
        elif "doctor" in command:
            stdout = json.dumps({"success": True, "data": {"checks": []}})
        elif "is visible" in joined:
            stdout = json.dumps({"success": True, "data": {"visible": True}})
        elif "is enabled" in joined:
            stdout = json.dumps({"success": True, "data": {"enabled": True}})
        elif "get attr" in joined and "readonly" in joined:
            stdout = json.dumps(
                {"success": True, "data": {"value": "" if self.readonly else None}}
            )
        elif "get value" in joined:
            stdout = json.dumps({"success": True, "data": {"value": "ImgEnhancer"}})
        elif "is checked" in joined:
            stdout = json.dumps({"success": True, "data": {"checked": True}})
        else:
            stdout = json.dumps({"success": True, "data": {}})
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr="")


def test_session_id_is_stable_and_safe():
    a = deterministic_session_id("run/item:abc")
    assert a == deterministic_session_id("run/item:abc")
    assert a != deterministic_session_id("other")
    assert re.fullmatch(r"shipmore-[0-9a-f]{32}", a)


def test_preflight_pins_version_and_requires_encryption():
    runner = FakeRunner()
    adapter = AgentBrowserAdapter(
        "item-1",
        runner=runner,
        env={"AGENT_BROWSER_ENCRYPTION_KEY": "0" * 64},
    )
    assert adapter.preflight()["version"] == AGENT_BROWSER_VERSION

    adapter = AgentBrowserAdapter("item-1", runner=runner, env={})
    adapter.env.pop("AGENT_BROWSER_ENCRYPTION_KEY", None)
    with pytest.raises(AgentBrowserError, match="ENCRYPTION_KEY"):
        adapter.preflight()

    adapter = AgentBrowserAdapter(
        "item-1",
        runner=runner,
        env={"AGENT_BROWSER_ENCRYPTION_KEY": "not-hex"},
    )
    with pytest.raises(AgentBrowserError, match="64 hex"):
        adapter.preflight()


def test_safe_fill_reads_back_and_blocks_readonly():
    runner = FakeRunner()
    adapter = AgentBrowserAdapter("item-1", runner=runner)
    assert adapter.safe_fill("@e1", "ImgEnhancer") == "ImgEnhancer"

    runner = FakeRunner(readonly=True)
    adapter = AgentBrowserAdapter("item-1", runner=runner)
    with pytest.raises(AgentBrowserError, match="readonly"):
        adapter.safe_fill("@e1", "ImgEnhancer")
    assert not any(" fill " in f" {' '.join(call)} " for call in runner.calls)


def test_safe_upload_rejects_missing_and_empty(tmp_path):
    adapter = AgentBrowserAdapter("item-1", runner=FakeRunner())
    with pytest.raises(AgentBrowserError, match="does not exist"):
        adapter.safe_upload("@e1", str(tmp_path / "missing.png"))
    empty = tmp_path / "empty.png"
    empty.write_bytes(b"")
    with pytest.raises(AgentBrowserError, match="empty"):
        adapter.safe_upload("@e1", str(empty))


def test_worker_pool_assigns_unique_ids():
    a = build_worker_env({}, run_id="run-1", worker_id_prefix="codex", slot=1, concurrency=4)
    b = build_worker_env({}, run_id="run-1", worker_id_prefix="codex", slot=4, concurrency=4)
    assert a["BACKLINK_WORKER_ID"] == "codex-01"
    assert b["BACKLINK_WORKER_ID"] == "codex-04"
    assert a["SHIPMORE_RUN_ID"] == "run-1"
    assert a["SHIPMORE_POOL_SIZE"] == "4"
    assert a["AGENT_BROWSER_NAMESPACE"] == "shipmore"


def test_version_file_matches_adapter():
    path = SCRIPT_DIR.parent / "runtime" / "agent-browser.version"
    assert path.read_text(encoding="utf-8").strip() == AGENT_BROWSER_VERSION


def test_adapter_defaults_to_shipmore_namespace():
    adapter = AgentBrowserAdapter("item-1", runner=FakeRunner())
    assert adapter.env["AGENT_BROWSER_NAMESPACE"] == "shipmore"


def test_recovery_bootstrap_never_loads_shared_seed(tmp_path):
    seed = tmp_path / "auth.json"
    seed.write_text("{}", encoding="utf-8")
    runner = FakeRunner()
    adapter = AgentBrowserAdapter(
        "item-1",
        runner=runner,
        auth_state_path=str(seed),
    )
    adapter.bootstrap("https://example.test", fresh_task=False)
    assert not any("state load" in " ".join(call) for call in runner.calls)


def test_fresh_bootstrap_loads_seed_once(tmp_path):
    seed = tmp_path / "auth.json"
    seed.write_text("{}", encoding="utf-8")
    runner = FakeRunner()
    adapter = AgentBrowserAdapter(
        "item-1",
        runner=runner,
        auth_state_path=str(seed),
    )
    adapter.bootstrap("https://example.test", fresh_task=True)
    loads = [call for call in runner.calls if "state load" in " ".join(call)]
    assert len(loads) == 1
