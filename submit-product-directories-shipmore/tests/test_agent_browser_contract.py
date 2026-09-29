from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_ROOT / "SKILL.md"
RUNTIME_MD = SKILL_ROOT / "references" / "agent-browser-runtime.md"
ROUTING_MD = SKILL_ROOT / "references" / "browser-control-routing.md"


def test_skill_routes_browser_work_through_locked_provider():
    skill = SKILL_MD.read_text(encoding="utf-8")
    assert "BACKLINK_BROWSER_PROVIDER" in skill
    assert "references/agent-browser-runtime.md" in skill
    assert "references/ego-browser-runtime.md" in skill
    assert "browser_action_guard.py select" in skill
    assert "同一个 Run Item" in skill


def test_runtime_requires_named_session_restore_and_readback():
    runtime = RUNTIME_MD.read_text(encoding="utf-8")
    required = (
        "--session <sessionId> --restore",
        "snapshot -i --json",
        "get value",
        "Submit",
        "Gmail Send",
        "每个 Run Item 必须有自己的 named session",
        "BACKLINK_AGENT_BROWSER_AUTH_STATE",
        "state load",
        "非 fresh 路径绝不加载共享 seed",
        "AGENT_BROWSER_NAMESPACE=shipmore",
        "agent_browser_adapter.py",
        "AGENT_BROWSER_STATE_EXPIRE_DAYS=36500",
        "SHIPMORE_TERMINAL_STATE_RETENTION_DAYS=7",
    )
    for phrase in required:
        assert phrase in runtime


def test_ego_provider_is_explicit_and_experimental():
    routing = ROUTING_MD.read_text(encoding="utf-8")
    ego = (SKILL_ROOT / "references" / "ego-browser-runtime.md").read_text(encoding="utf-8")
    assert "ego-browser     # 默认 provider" in routing
    assert "agent-browser   # 可显式选择的备用 provider" in routing
    assert "不得中途切换" in routing
    assert "browser_action_guard.py mutation-check" in ego
    assert "browser_action_guard.py final-begin" in ego
    assert "blocked_manual_verification" in ego


def test_routing_keeps_codex_as_business_decision_agent():
    routing = ROUTING_MD.read_text(encoding="utf-8")
    assert "Codex 是唯一业务决策 Agent" in routing
    assert "字段业务含义" in routing
    assert "最终动作只执行一次" in routing


def test_auth_seed_is_bootstrap_only():
    runtime = RUNTIME_MD.read_text(encoding="utf-8")
    skill = SKILL_MD.read_text(encoding="utf-8")
    assert "agent-browser --auto-connect state save" in runtime
    assert "已有 restore state 永远优先" in skill or "已有 Run Item 状态必须优先恢复" in skill
    assert "不得对正在恢复的 Run Item 使用" in runtime


def test_production_runtime_files_exist():
    assert (SKILL_ROOT / "scripts" / "agent_browser_adapter.py").is_file()
    assert (SKILL_ROOT / "scripts" / "shipmore_worker_pool.py").is_file()
    assert (SKILL_ROOT / "references" / "parallel-execution.md").is_file()
    assert (SKILL_ROOT / "runtime" / "agent-browser.version").read_text(encoding="utf-8").strip() == "0.38.1"
    assert (SKILL_ROOT / "scripts" / "runtime_cleanup.py").is_file()
    assert (SKILL_ROOT / "scripts" / "diagnostic_sanitizer.py").is_file()
    assert (SKILL_ROOT / "scripts" / "browser_action_guard.py").is_file()
    assert (SKILL_ROOT / "references" / "ego-browser-runtime.md").is_file()


def test_backlink_wording_cannot_be_used_as_ineligible_shortcut():
    skill = SKILL_MD.read_text(encoding="utf-8")
    worker = (SKILL_ROOT / "references" / "worker-loop.md").read_text(encoding="utf-8")
    status = (SKILL_ROOT / "references" / "status-mapping.md").read_text(encoding="utf-8")
    checklist = (SKILL_ROOT / "EXEC-CHECKLIST.md").read_text(encoding="utf-8")

    assert "这些文字本身绝不能作为 `ineligible` 依据" in skill
    assert "纯 backlink/reciprocal/permanent backlink" in worker
    assert "install badge 字样" in status
    assert "没有再错误进入 Badge 安装分支" in checklist


def test_badge_requires_native_verifier_before_unsupported_classification():
    skill = SKILL_MD.read_text(encoding="utf-8")
    worker = (SKILL_ROOT / "references" / "worker-loop.md").read_text(encoding="utf-8")
    routing = (SKILL_ROOT / "references" / "entry-and-content-routing.md").read_text(encoding="utf-8")
    checklist = (SKILL_ROOT / "EXEC-CHECKLIST.md").read_text(encoding="utf-8")

    for phrase in ("Verify Badge", "Check Backlink", "实际执行一次"):
        assert phrase in skill
        assert phrase in worker

    assert "不得仅凭说明文字" in skill
    assert "原生校验明确失败" in routing
    assert "当前不存在尚未解决的 Badge 验证 pending 状态" in checklist
    assert "没有安全 Badge 变更入口" in worker
    assert "不能修改 Product 网站" in worker


def test_badge_verification_can_be_deferred_until_form_ready():
    skill = SKILL_MD.read_text(encoding="utf-8")
    worker = (SKILL_ROOT / "references" / "worker-loop.md").read_text(encoding="utf-8")
    status = (SKILL_ROOT / "references" / "status-mapping.md").read_text(encoding="utf-8")
    routing = (SKILL_ROOT / "references" / "entry-and-content-routing.md").read_text(encoding="utf-8")
    checklist = (SKILL_ROOT / "EXEC-CHECKLIST.md").read_text(encoding="utf-8")

    assert "必须继续完成安全、可逆的表单准备以解锁 verifier" in skill
    assert "安全表单准备" in worker
    assert "延后的 Badge/Backlink 原生验证" in worker
    assert "要求先填完整表单" in status
    assert "可以依赖表单状态" in routing
    assert "verifier 之前 disabled、隐藏或要求先完整填表时，没有因此提前停止" in checklist


def test_badge_pending_blocks_final_action_not_form_preparation():
    worker = (SKILL_ROOT / "references" / "worker-loop.md").read_text(encoding="utf-8")
    checklist = (SKILL_ROOT / "EXEC-CHECKLIST.md").read_text(encoding="utf-8")

    assert "不要执行最终 Submit/Publish/Claim" in worker
    assert "当前不存在尚未解决的 Badge 验证 pending 状态" in checklist
