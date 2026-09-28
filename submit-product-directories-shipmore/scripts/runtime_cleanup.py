#!/usr/bin/env python3
"""Lifecycle-aware cleanup for terminal Shipmore browser runtime state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any, Callable

DEFAULT_RETENTION_DAYS = 7
DEFAULT_NAMESPACE = "shipmore"
DEFAULT_REGISTRY_ROOT = Path.home() / ".shipmore" / "terminal-sessions"
TERMINAL_ITEM_STATUSES = {"completed", "blocked", "failed", "skipped"}
CLEANUP_ELIGIBLE_SUBMISSION_STATUSES = {
    "published",
    "unavailable",
    "paid_only",
    "ineligible",
    "duplicate_no_action",
    "terminated_by_user",
    "rejected",
}


class RuntimeCleanupError(RuntimeError):
    pass


def deterministic_session_id(run_item_id: str) -> str:
    value = (run_item_id or "").strip()
    if not value:
        raise RuntimeCleanupError("run_item_id is required")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]
    return f"shipmore-{digest}"


def _registry_root() -> Path:
    return Path(
        os.environ.get(
            "SHIPMORE_TERMINAL_SESSION_DIR",
            str(DEFAULT_REGISTRY_ROOT),
        )
    ).expanduser()


def _record_path(run_item_id: str) -> Path:
    digest = hashlib.sha256(run_item_id.encode("utf-8")).hexdigest()[:32]
    return _registry_root() / f"{digest}.json"


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    temp = path.with_suffix(f".{os.getpid()}.tmp")
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"))
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temp.chmod(0o600)
    except OSError:
        pass
    os.replace(temp, path)


def mark_terminal_session(
    run_item_id: str,
    *,
    status: str,
    submission_status: str,
    retention_days: int | None = None,
    now: float | None = None,
) -> dict[str, Any]:
    if status not in TERMINAL_ITEM_STATUSES:
        raise RuntimeCleanupError(f"status is not terminal: {status}")
    if submission_status not in CLEANUP_ELIGIBLE_SUBMISSION_STATUSES:
        return {
            "version": 1,
            "runItemId": run_item_id,
            "sessionId": deterministic_session_id(run_item_id),
            "status": status,
            "submissionStatus": submission_status,
            "cleanupEligible": False,
        }
    if retention_days is None:
        retention_days = int(
            os.environ.get(
                "SHIPMORE_TERMINAL_STATE_RETENTION_DAYS",
                DEFAULT_RETENTION_DAYS,
            )
        )
    if retention_days < 0:
        raise RuntimeCleanupError("retention_days must be >= 0")
    now = time.time() if now is None else now
    payload = {
        "version": 1,
        "runItemId": run_item_id,
        "sessionId": deterministic_session_id(run_item_id),
        "status": status,
        "submissionStatus": submission_status,
        "cleanupEligible": True,
        "terminalAtEpoch": now,
        "cleanupAfterEpoch": now + retention_days * 86400,
    }
    _atomic_write(_record_path(run_item_id), payload)
    return payload


def list_terminal_records() -> list[tuple[Path, dict[str, Any]]]:
    root = _registry_root()
    if not root.exists():
        return []
    records: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            records.append((path, payload))
    return records


def cleanup_terminal_sessions(
    *,
    executable: str = "agent-browser",
    namespace: str | None = None,
    now: float | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    now = time.time() if now is None else now
    namespace = (
        namespace
        or os.environ.get("AGENT_BROWSER_NAMESPACE")
        or DEFAULT_NAMESPACE
    )
    resolved = shutil.which(executable, path=os.environ.get("PATH")) or executable

    cleaned: list[str] = []
    deferred: list[str] = []
    failed: list[dict[str, str]] = []

    records = list_terminal_records()
    if not records:
        return {
            "success": True,
            "cleaned": [],
            "deferred": [],
            "failed": [],
        }

    list_command = [
        resolved,
        "--namespace",
        namespace,
        "state",
        "list",
    ]
    listed = runner(
        list_command,
        capture_output=True,
        text=True,
        check=False,
    )
    if listed.returncode != 0:
        return {
            "success": False,
            "cleaned": [],
            "deferred": [],
            "failed": [
                {
                    "error": (
                        listed.stderr
                        or listed.stdout
                        or "state list failed"
                    ).strip()
                }
            ],
        }
    saved_states = listed.stdout or ""

    for path, record in records:
        run_item_id = str(record.get("runItemId") or "")
        session_id = str(record.get("sessionId") or "")
        cleanup_after = record.get("cleanupAfterEpoch")
        if not run_item_id or not session_id or not isinstance(
            cleanup_after, (int, float)
        ):
            failed.append(
                {"record": str(path), "error": "invalid terminal cleanup record"}
            )
            continue
        if cleanup_after > now:
            deferred.append(run_item_id)
            continue

        if session_id not in saved_states:
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            cleaned.append(run_item_id)
            continue

        command = [
            resolved,
            "--namespace",
            namespace,
            "state",
            "clear",
            session_id,
        ]
        completed = runner(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            failed.append(
                {
                    "runItemId": run_item_id,
                    "error": (
                        completed.stderr
                        or completed.stdout
                        or "state clear failed"
                    ).strip(),
                }
            )
            continue

        try:
            path.unlink()
        except FileNotFoundError:
            pass
        cleaned.append(run_item_id)

    return {
        "success": not failed,
        "cleaned": cleaned,
        "deferred": deferred,
        "failed": failed,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Clear agent-browser restore state only for terminal Shipmore items"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    mark = sub.add_parser("mark-terminal")
    mark.add_argument("--run-item-id", required=True)
    mark.add_argument("--status", required=True)
    mark.add_argument("--submission-status", required=True)
    mark.add_argument("--retention-days", type=int)

    clean = sub.add_parser("cleanup")
    clean.add_argument("--agent-browser", default="agent-browser")
    clean.add_argument("--namespace")

    args = parser.parse_args()
    try:
        if args.command == "mark-terminal":
            result = mark_terminal_session(
                args.run_item_id,
                status=args.status,
                submission_status=args.submission_status,
                retention_days=args.retention_days,
            )
        else:
            result = cleanup_terminal_sessions(
                executable=args.agent_browser,
                namespace=args.namespace,
            )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0 if result.get("success", True) else 1
    except (RuntimeCleanupError, OSError, ValueError) as exc:
        print(str(exc), file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
