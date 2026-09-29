from pathlib import Path
import sys

import pytest


SKILL_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = SKILL_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from browser_action_guard import (  # noqa: E402
    BrowserProviderGuardError,
    assert_mutation_allowed,
    lock_provider,
    provider_from_env,
)


def test_provider_defaults_to_agent_browser(monkeypatch):
    monkeypatch.delenv("BACKLINK_BROWSER_PROVIDER", raising=False)
    assert provider_from_env() == "agent-browser"


def test_provider_lock_prevents_mid_item_switch(tmp_path, monkeypatch):
    monkeypatch.setenv("SHIPMORE_BROWSER_PROVIDER_LOCK_DIR", str(tmp_path))
    monkeypatch.setenv("BACKLINK_BROWSER_PROVIDER", "ego-browser")

    first = lock_provider("run-item-1")
    assert first["provider"] == "ego-browser"

    monkeypatch.setenv("BACKLINK_BROWSER_PROVIDER", "agent-browser")
    with pytest.raises(BrowserProviderGuardError, match="already locked"):
        lock_provider("run-item-1")


def test_direct_mode_mutation_check_locks_provider(tmp_path, monkeypatch):
    monkeypatch.setenv("SHIPMORE_BROWSER_PROVIDER_LOCK_DIR", str(tmp_path))
    monkeypatch.setenv("BACKLINK_BROWSER_PROVIDER", "ego-browser")
    monkeypatch.delenv("SHIPMORE_MANAGED_LEASE", raising=False)
    monkeypatch.delenv("SHIPMORE_LEASE_GUARD_PATH", raising=False)

    result = assert_mutation_allowed("run-item-2")
    assert result["provider"] == "ego-browser"


def test_managed_mode_requires_lease_guard(tmp_path, monkeypatch):
    monkeypatch.setenv("SHIPMORE_BROWSER_PROVIDER_LOCK_DIR", str(tmp_path))
    monkeypatch.setenv("BACKLINK_BROWSER_PROVIDER", "ego-browser")
    monkeypatch.setenv("SHIPMORE_MANAGED_LEASE", "1")
    monkeypatch.delenv("SHIPMORE_LEASE_GUARD_PATH", raising=False)

    with pytest.raises(BrowserProviderGuardError, match="missing SHIPMORE_LEASE_GUARD_PATH"):
        assert_mutation_allowed("run-item-3")


def test_rejects_unknown_provider(monkeypatch):
    monkeypatch.setenv("BACKLINK_BROWSER_PROVIDER", "not-a-browser")
    with pytest.raises(BrowserProviderGuardError, match="unsupported browser provider"):
        provider_from_env()
