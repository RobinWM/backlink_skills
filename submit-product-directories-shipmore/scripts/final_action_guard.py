#!/usr/bin/env python3
"""Durable local fence for irreversible browser actions."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import time
import uuid
from typing import Any


DEFAULT_JOURNAL_ROOT = Path.home() / ".shipmore" / "final-actions"
FINAL_ACTION_TYPES = {"submit", "publish", "claim", "gmail_send"}


class FinalActionError(RuntimeError):
    pass


def _journal_root() -> Path:
    return Path(
        os.environ.get("SHIPMORE_FINAL_ACTION_JOURNAL_DIR", str(DEFAULT_JOURNAL_ROOT))
    ).expanduser()


def final_action_journal_path(run_item_id: str, action_type: str) -> Path:
    if action_type not in FINAL_ACTION_TYPES:
        raise FinalActionError(f"unsupported final action type: {action_type}")
    value = (run_item_id or "").strip()
    if not value:
        raise FinalActionError("run_item_id is required")
    digest = hashlib.sha256(f"{value}:{action_type}".encode("utf-8")).hexdigest()
    return _journal_root() / f"{digest}.json"


def _write_replace(path: Path, payload: dict[str, Any]) -> None:
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


class FinalActionJournal:
    def __init__(self, run_item_id: str, action_type: str) -> None:
        if action_type not in FINAL_ACTION_TYPES:
            raise FinalActionError(f"unsupported final action type: {action_type}")
        self.run_item_id = run_item_id
        self.action_type = action_type
        self.path = final_action_journal_path(run_item_id, action_type)

    def read(self) -> dict[str, Any] | None:
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except json.JSONDecodeError as exc:
            raise FinalActionError("final-action journal is corrupt") from exc
        if not isinstance(value, dict):
            raise FinalActionError("final-action journal is invalid")
        return value

    def prepare(self, *, worker_id: str, session_id: str) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.path.parent.chmod(0o700)
        except OSError:
            pass
        now = time.time()
        record = {
            "version": 1,
            "runItemId": self.run_item_id,
            "actionType": self.action_type,
            "state": "prepared",
            "workerId": worker_id,
            "sessionId": session_id,
            "preparedAtEpoch": now,
            "completionEventId": (
                f"shipmore:{self.run_item_id}:complete:{uuid.uuid4()}"
            ),
        }
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        try:
            fd = os.open(self.path, flags, 0o600)
        except FileExistsError as exc:
            existing = self.read() or {}
            raise FinalActionError(
                "final action already fenced locally "
                f"(state={existing.get('state') or 'unknown'})"
            ) from exc
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(record, handle, ensure_ascii=False, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        return record

    def transition(self, state: str, **metadata: Any) -> dict[str, Any]:
        record = self.read()
        if not record:
            raise FinalActionError("final-action journal has not been prepared")
        record["state"] = state
        record["updatedAtEpoch"] = time.time()
        for key, value in metadata.items():
            if value is not None:
                record[key] = value
        _write_replace(self.path, record)
        return record

    def mark_attempting(self) -> dict[str, Any]:
        return self.transition("attempting")

    def mark_dispatched(self) -> dict[str, Any]:
        return self.transition("dispatched")

    def resolve(self, outcome: str) -> dict[str, Any]:
        if outcome not in {"confirmed", "outcome_unknown", "rejected"}:
            raise FinalActionError(f"unsupported final outcome: {outcome}")
        return self.transition(outcome)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Shipmore final-action journal")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status")
    status.add_argument("--run-item-id", required=True)
    status.add_argument("--action-type", required=True, choices=sorted(FINAL_ACTION_TYPES))

    resolve = sub.add_parser("resolve")
    resolve.add_argument("--run-item-id", required=True)
    resolve.add_argument("--action-type", required=True, choices=sorted(FINAL_ACTION_TYPES))
    resolve.add_argument(
        "--outcome",
        required=True,
        choices=["confirmed", "outcome_unknown", "rejected"],
    )

    args = parser.parse_args()
    journal = FinalActionJournal(args.run_item_id, args.action_type)
    try:
        if args.command == "status":
            print(json.dumps(journal.read(), ensure_ascii=False, indent=2))
        else:
            print(
                json.dumps(
                    journal.resolve(args.outcome),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return 0
    except FinalActionError as exc:
        print(str(exc), file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
