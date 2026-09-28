#!/usr/bin/env python3
"""Automatic Shipmore lease heartbeat and browser mutation guard."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import threading
import time
import uuid
from typing import Any, Callable

from shipmore_queue_client import ShipmoreClientError, ShipmoreQueueClient


DEFAULT_LEASE_SECONDS = 300
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 60
DEFAULT_GUARD_ROOT = Path.home() / ".shipmore" / "lease-guards"


class LeaseGuardError(RuntimeError):
    pass


def _guard_root() -> Path:
    return Path(
        os.environ.get("SHIPMORE_LEASE_GUARD_DIR", str(DEFAULT_GUARD_ROOT))
    ).expanduser()


def lease_guard_path(run_item_id: str) -> Path:
    value = (run_item_id or "").strip()
    if not value:
        raise LeaseGuardError("run_item_id is required")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]
    return _guard_root() / f"{digest}.json"


def _atomic_json_write(path: Path, payload: dict[str, Any]) -> None:
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


def read_lease_guard(path: str | Path) -> dict[str, Any]:
    guard_path = Path(path).expanduser()
    try:
        payload = json.loads(guard_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise LeaseGuardError("lease guard file is missing") from exc
    except json.JSONDecodeError as exc:
        raise LeaseGuardError("lease guard file is invalid") from exc
    if not isinstance(payload, dict):
        raise LeaseGuardError("lease guard payload is invalid")
    return payload


def assert_lease_guard_valid(
    path: str | Path,
    *,
    expected_worker_id: str | None = None,
    expected_run_item_id: str | None = None,
) -> dict[str, Any]:
    payload = read_lease_guard(path)
    if payload.get("valid") is not True:
        raise LeaseGuardError(
            f"Shipmore lease is not valid: {payload.get('reason') or 'unknown'}"
        )
    if expected_worker_id:
        actual_worker_id = str(payload.get("workerId") or "")
        if actual_worker_id != expected_worker_id:
            raise LeaseGuardError(
                "Shipmore lease guard belongs to another worker"
            )
    if expected_run_item_id:
        actual_run_item_id = str(payload.get("runItemId") or "")
        if actual_run_item_id != expected_run_item_id:
            raise LeaseGuardError(
                "Shipmore lease guard belongs to another Run Item"
            )
    deadline = payload.get("deadlineEpoch")
    if not isinstance(deadline, (int, float)) or deadline <= time.time():
        raise LeaseGuardError("Shipmore lease guard has expired")
    return payload


class LeaseKeeper:
    def __init__(
        self,
        client: ShipmoreQueueClient,
        run_item_id: str,
        *,
        lease_seconds: int = DEFAULT_LEASE_SECONDS,
        interval_seconds: int = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
        guard_path: str | Path | None = None,
        clock: Callable[[], float] = time.time,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if interval_seconds <= 0:
            raise LeaseGuardError("heartbeat interval must be positive")
        if lease_seconds <= interval_seconds:
            raise LeaseGuardError("lease must be longer than heartbeat interval")
        self.client = client
        self.run_item_id = run_item_id
        self.lease_seconds = lease_seconds
        self.interval_seconds = interval_seconds
        self.path = Path(guard_path) if guard_path else lease_guard_path(run_item_id)
        self.clock = clock
        self.sleeper = sleeper
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.lost = False
        self.last_error: str | None = None
        self.keeper_id = uuid.uuid4().hex

    def _write(self, *, valid: bool, reason: str) -> None:
        now = self.clock()
        _atomic_json_write(
            self.path,
            {
                "version": 1,
                "valid": valid,
                "reason": reason,
                "workerId": self.client.require_worker_id(),
                "runItemId": self.run_item_id,
                "keeperId": self.keeper_id,
                "heartbeatEpoch": now,
                "deadlineEpoch": now + self.lease_seconds if valid else now,
            },
        )

    def heartbeat_once(self) -> dict[str, Any]:
        try:
            result = self.client.heartbeat(self.run_item_id, self.lease_seconds)
            if result.get("success") is False:
                raise LeaseGuardError(
                    str(result.get("reason") or result.get("error") or "heartbeat rejected")
                )
        except (ShipmoreClientError, LeaseGuardError) as exc:
            self.lost = True
            self.last_error = str(exc)
            self._write(valid=False, reason=f"heartbeat_failed:{self.last_error}")
            raise LeaseGuardError(self.last_error) from exc

        self.lost = False
        self.last_error = None
        self._write(valid=True, reason="heartbeat_ok")
        return result

    def _loop(self) -> None:
        while not self._stop_event.wait(self.interval_seconds):
            try:
                self.heartbeat_once()
            except LeaseGuardError:
                # Keep probing. Mutations remain blocked until a later heartbeat succeeds.
                continue

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            raise LeaseGuardError("lease keeper is already running")
        self.heartbeat_once()
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._loop,
            name=f"shipmore-lease-{self.run_item_id[:12]}",
            daemon=True,
        )
        self._thread.start()

    def stop(self, reason: str = "worker_stopped") -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(2, min(self.interval_seconds, 10)))
        try:
            current = read_lease_guard(self.path)
        except LeaseGuardError:
            current = None
        if not current or current.get("keeperId") == self.keeper_id:
            self._write(valid=False, reason=reason)

    def __enter__(self) -> "LeaseKeeper":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop("worker_context_exited")


def client_from_env(worker_id: str | None = None) -> ShipmoreQueueClient:
    base_url = (os.environ.get("BACKLINK_APP_URL") or "").strip()
    token = (os.environ.get("BACKLINK_AGENT_TOKEN") or "").strip()
    resolved_worker_id = (worker_id or os.environ.get("BACKLINK_WORKER_ID") or "").strip()
    if not base_url:
        raise LeaseGuardError("BACKLINK_APP_URL is required")
    if not token:
        raise LeaseGuardError("BACKLINK_AGENT_TOKEN is required")
    if not resolved_worker_id:
        raise LeaseGuardError("BACKLINK_WORKER_ID is required")
    return ShipmoreQueueClient(
        base_url=base_url,
        token=token,
        worker_id=resolved_worker_id,
    )


def refresh_lease_from_env(
    run_item_id: str,
    *,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
) -> dict[str, Any]:
    client = client_from_env()
    guard = Path(
        os.environ.get("SHIPMORE_LEASE_GUARD_PATH")
        or lease_guard_path(run_item_id)
    )
    try:
        result = client.heartbeat(run_item_id, lease_seconds)
        if result.get("success") is False:
            raise LeaseGuardError(
                str(result.get("reason") or result.get("error") or "heartbeat rejected")
            )
    except (ShipmoreClientError, LeaseGuardError) as exc:
        now = time.time()
        _atomic_json_write(
            guard,
            {
                "version": 1,
                "valid": False,
                "reason": f"final_action_heartbeat_failed:{exc}",
                "workerId": client.require_worker_id(),
                "runItemId": run_item_id,
                "heartbeatEpoch": now,
                "deadlineEpoch": now,
            },
        )
        raise LeaseGuardError(str(exc)) from exc

    now = time.time()
    _atomic_json_write(
        guard,
        {
            "version": 1,
            "valid": True,
            "reason": "final_action_heartbeat_ok",
            "workerId": client.require_worker_id(),
            "runItemId": run_item_id,
            "heartbeatEpoch": now,
            "deadlineEpoch": now + lease_seconds,
        },
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Shipmore lease keeper helper")
    sub = parser.add_subparsers(dest="command", required=True)

    guard = sub.add_parser("guard-path")
    guard.add_argument("--run-item-id", required=True)

    check = sub.add_parser("check")
    check.add_argument("--path", required=True)

    beat = sub.add_parser("heartbeat-once")
    beat.add_argument("--run-item-id", required=True)
    beat.add_argument("--lease-seconds", type=int, default=DEFAULT_LEASE_SECONDS)

    args = parser.parse_args()
    try:
        if args.command == "guard-path":
            print(lease_guard_path(args.run_item_id))
        elif args.command == "check":
            print(json.dumps(assert_lease_guard_valid(args.path), indent=2))
        elif args.command == "heartbeat-once":
            print(
                json.dumps(
                    refresh_lease_from_env(
                        args.run_item_id,
                        lease_seconds=args.lease_seconds,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return 0
    except (LeaseGuardError, ShipmoreClientError) as exc:
        print(str(exc), file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
