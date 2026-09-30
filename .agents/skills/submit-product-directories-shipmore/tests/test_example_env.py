from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_ENV = SKILL_ROOT / "example.env"


def parse_env_keys(text: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        result[key.strip()] = value.strip()
    return result


def test_example_env_lists_all_shipmore_runtime_variables():
    values = parse_env_keys(EXAMPLE_ENV.read_text(encoding="utf-8"))
    expected = {
        "BACKLINK_APP_URL",
        "BACKLINK_AGENT_TOKEN",
        "BACKLINK_WORKER_ID",
        "BACKLINK_WORKER_ID_PREFIX",
        "BACKLINK_BROWSER_PROVIDER",
        "BACKLINK_EGO_BROWSER_SKILL",
        "BACKLINK_AGENT_BROWSER_AUTH_STATE",
        "AGENT_BROWSER_ENCRYPTION_KEY",
        "AGENT_BROWSER_STATE_EXPIRE_DAYS",
        "AGENT_BROWSER_NAMESPACE",
        "DIRECTORY_ACCOUNT_PASSWORD",
        "SHIPMORE_DEBUG_IGNORE_HISTORY",
        "SHIPMORE_RUN_ID",
        "SHIPMORE_CONCURRENCY",
        "SHIPMORE_LEASE_SECONDS",
        "SHIPMORE_HEARTBEAT_INTERVAL_SECONDS",
        "SHIPMORE_TERMINAL_STATE_RETENTION_DAYS",
        "SHIPMORE_BROWSER_PROVIDER_LOCK_DIR",
        "SHIPMORE_FINAL_ACTION_JOURNAL_DIR",
        "SHIPMORE_LEASE_GUARD_DIR",
        "SHIPMORE_TERMINAL_SESSION_DIR",
        "SHIPMORE_WORKER_ID_FILE",
        "SHIPMORE_WORKER_INSTANCE_ID",
        "SHIPMORE_WORKER_LOCK_DIR",
        "SHIPMORE_POOL_SLOT",
        "SHIPMORE_POOL_SIZE",
        "SHIPMORE_RUN_ITEM_ID",
        "SHIPMORE_CLAIM_REASON",
        "SHIPMORE_RECOVERY_MODE",
        "SHIPMORE_MANAGED_LEASE",
        "SHIPMORE_LEASE_GUARD_PATH",
    }

    assert expected <= set(values)


def test_example_env_defaults_match_runtime():
    values = parse_env_keys(EXAMPLE_ENV.read_text(encoding="utf-8"))

    assert values["BACKLINK_APP_URL"] == "https://shipmore.app"
    assert values["BACKLINK_BROWSER_PROVIDER"] == "ego-browser"
    assert values["AGENT_BROWSER_STATE_EXPIRE_DAYS"] == "36500"
    assert values["AGENT_BROWSER_NAMESPACE"] == "shipmore"
    assert values["SHIPMORE_DEBUG_IGNORE_HISTORY"] == "1"
    assert values["SHIPMORE_CONCURRENCY"] == "4"
    assert values["SHIPMORE_LEASE_SECONDS"] == "300"
    assert values["SHIPMORE_HEARTBEAT_INTERVAL_SECONDS"] == "60"
    assert values["SHIPMORE_TERMINAL_STATE_RETENTION_DAYS"] == "7"


def test_example_env_does_not_ship_real_secrets():
    values = parse_env_keys(EXAMPLE_ENV.read_text(encoding="utf-8"))

    assert values["BACKLINK_AGENT_TOKEN"] == ""
    assert values["AGENT_BROWSER_ENCRYPTION_KEY"] == ""
    assert values["DIRECTORY_ACCOUNT_PASSWORD"] == ""
