from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_ROOT / "SKILL.md"
RUNTIME_MD = SKILL_ROOT / "references" / "agent-browser-runtime.md"
ROUTING_MD = SKILL_ROOT / "references" / "browser-control-routing.md"


def test_skill_routes_browser_work_to_agent_browser():
    skill = SKILL_MD.read_text(encoding="utf-8")
    assert "references/agent-browser-runtime.md" in skill
    assert "agent-browser" in skill
    assert "ego-browser" not in skill
    assert "TaskSpace" not in skill


def test_runtime_requires_named_session_restore_and_readback():
    runtime = RUNTIME_MD.read_text(encoding="utf-8")
    required = (
        "--session <sessionId> --restore",
        "snapshot -i --json",
        "get value",
        "Submit",
        "Gmail Send",
        "一个 Run Item 对应一个独立 named session",
    )
    for phrase in required:
        assert phrase in runtime


def test_browser_contract_has_no_ego_runtime_dependency():
    for path in SKILL_ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".yaml"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert "ego-browser" not in text, path
        assert "Citro Labs" not in text, path
        assert "TaskSpace" not in text, path


def test_routing_keeps_codex_as_business_decision_agent():
    routing = ROUTING_MD.read_text(encoding="utf-8")
    assert "Codex 是唯一业务决策 Agent" in routing
    assert "字段业务含义" in routing
    assert "最终动作只执行一次" in routing
