#!/usr/bin/env python3
"""Browser-provider-independent Shipmore mutation and final-action guard."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from final_action_guard import FinalActionError, FinalActionJournal, FINAL_ACTION_TYPES
from lease_keeper import (
    LeaseGuardError,
    assert_lease_guard_valid,
    refresh_lease_from_env,
)


ALLOWED_PROVIDERS = {"agent-browser", "ego-browser"}
DEFAULT_PROVIDER = "agent-browser"
DEFAULT_PROVIDER_LOCK_ROOT = Path.home() / ".shipmore" / "browser-providers"


class BrowserProviderGuardError(RuntimeError):
    pass


def provider_from_env(explicit: str | None = None) -> str:
    provider = (explicit or os.environ.get("BACKLINK_BROWSER_PROVIDER") or DEFAULT_PROVIDER).strip()
    if provider not in ALLOWED_PROVIDERS:
        raise BrowserProviderGuardError(
            f"unsupported browser provider: {provider}; expected one of {sorted(ALLOWED_PROVIDERS)}"
        )
    return provider


def _lock_root() -> Path:
    return Path(
        os.environ.get("SHIPMORE_BROWSER_PROVIDER_LOCK_DIR", str(DEFAULT_PROVIDER_LOCK_ROOT))
    ).expanduser()


def provider_lock_path(run_item_id: str) -> Path:
    value = (run_item_id or "").strip()
    if not value:
        raise BrowserProviderGuardError("run_item_id is required")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]
    return _lock_root() / f"{digest}.json"


def provider_identity(run_item_id: str, provider: str) -> str:
    digest = hashlib.sha256(run_item_id.encode("utf-8")).hexdigest()[:32]
    prefix = "agent" if provider == "agent-browser" else "ego"
    return f"shipmore-{prefix}-{digest}"


def lock_provider(run_item_id: str, provider: str | None = None) -> dict[str, Any]:
    selected = provider_from_env(provider)
    path = provider_lock_path(run_item_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        existing = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        existing = None
    except json.JSONDecodeError as exc:
        raise BrowserProviderGuardError("browser provider lock is corrupt") from exc

    if existing is not None:
        locked = str(existing.get("provider") or "")
        if locked != selected:
            raise BrowserProviderGuardError(
                f"Run Item browser provider already locked to {locked or 'unknown'}"
            )
        return existing

    record = {
        "version": 1,
        "runItemId": run_item_id,
        "provider": selected,
        "providerIdentity": provider_identity(run_item_id, selected),
    }
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        return lock_provider(run_item_id, selected)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(record, handle, ensure_ascii=False, separators=(",", ":"))
        handle.flush()
        os.fsync(handle.fileno())
    return record


def assert_mutation_allowed(run_item_id: str) -> dict[str, Any]:
    record = lock_provider(run_item_id)
    worker_id = (os.environ.get("BACKLINK_WORKER_ID") or "").strip()
    guard_path = (os.environ.get("SHIPMORE_LEASE_GUARD_PATH") or "").strip()
    managed = os.environ.get("SHIPMORE_MANAGED_LEASE") == "1"

    if managed and not guard_path:
        raise BrowserProviderGuardError(
            "managed Shipmore worker is missing SHIPMORE_LEASE_GUARD_PATH"
        )
    if guard_path:
        if not worker_id:
            raise BrowserProviderGuardError("BACKLINK_WORKER_ID is required")
        try:
            assert_lease_guard_valid(
                guard_path,
                expected_worker_id=worker_id,
                expected_run_item_id=run_item_id,
            )
        except LeaseGuardError as exc:
            raise BrowserProviderGuardError(str(exc)) from exc
    return record


def final_begin(run_item_id: str, action_type: str) -> dict[str, Any]:
    record = assert_mutation_allowed(run_item_id)
    worker_id = (os.environ.get("BACKLINK_WORKER_ID") or "").strip()
    if not worker_id:
        raise BrowserProviderGuardError("BACKLINK_WORKER_ID is required")

    try:
        refresh_lease_from_env(run_item_id)
    except LeaseGuardError as exc:
        raise BrowserProviderGuardError(str(exc)) from exc
    assert_mutation_allowed(run_item_id)

    journal = FinalActionJournal(run_item_id, action_type)
    try:
        prepared = journal.prepare(
            worker_id=worker_id,
            session_id=str(record["providerIdentity"]),
        )
        return journal.mark_attempting() | {
            "provider": record["provider"],
            "completionEventId": prepared["completionEventId"],
        }
    except FinalActionError as exc:
        raise BrowserProviderGuardError(str(exc)) from exc


def main() -> int:
    parser = argparse.ArgumentParser(description="Shipmore browser provider guard")
    sub = parser.add_subparsers(dest="command", required=True)

    select = sub.add_parser("select")
    select.add_argument("--run-item-id", required=True)
    select.add_argument("--provider", choices=sorted(ALLOWED_PROVIDERS))

    mutation = sub.add_parser("mutation-check")
    mutation.add_argument("--run-item-id", required=True)

    begin = sub.add_parser("final-begin")
    begin.add_argument("--run-item-id", required=True)
    begin.add_argument("--action-type", required=True, choices=sorted(FINAL_ACTION_TYPES))

    dispatched = sub.add_parser("final-dispatched")
    dispatched.add_argument("--run-item-id", required=True)
    dispatched.add_argument("--action-type", required=True, choices=sorted(FINAL_ACTION_TYPES))

    resolve = sub.add_parser("final-resolve")
    resolve.add_argument("--run-item-id", required=True)
    resolve.add_argument("--action-type", required=True, choices=sorted(FINAL_ACTION_TYPES))
    resolve.add_argument(
        "--outcome",
        required=True,
        choices=["confirmed", "outcome_unknown", "rejected"],
    )

    status = sub.add_parser("status")
    status.add_argument("--run-item-id", required=True)
    status.add_argument("--action-type", choices=sorted(FINAL_ACTION_TYPES))

    args = parser.parse_args()
    try:
        if args.command == "select":
            result = lock_provider(args.run_item_id, args.provider)
        elif args.command == "mutation-check":
            result = assert_mutation_allowed(args.run_item_id)
        elif args.command == "final-begin":
            result = final_begin(args.run_item_id, args.action_type)
        elif args.command == "final-dispatched":
            result = FinalActionJournal(args.run_item_id, args.action_type).mark_dispatched()
        elif args.command == "final-resolve":
            result = FinalActionJournal(args.run_item_id, args.action_type).resolve(args.outcome)
        else:
            result = {"provider": lock_provider(args.run_item_id)}
            if args.action_type:
                result["finalAction"] = FinalActionJournal(
                    args.run_item_id, args.action_type
                ).read()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (BrowserProviderGuardError, FinalActionError) as exc:
        print(str(exc), file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
