#!/usr/bin/env python3
"""Long-lived Shipmore runtime around one-item agent processor invocations."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Sequence

from lease_keeper import (
    DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    DEFAULT_LEASE_SECONDS,
    LeaseGuardError,
    LeaseKeeper,
    lease_guard_path,
)
from shipmore_queue_client import ShipmoreClientError, ShipmoreQueueClient
from worker_identity import get_worker_instance_id


STOP_REASONS = {"run_paused", "run_terminal", "queue_empty"}
ACTIVE_REASONS = {"claimed", "reused"}


class WorkerRuntimeError(RuntimeError):
    pass


def _claim_reason(response: dict[str, Any]) -> str:
    reason = response.get("reason")
    if isinstance(reason, str):
        return reason
    data = response.get("data")
    if isinstance(data, dict) and isinstance(data.get("reason"), str):
        return data["reason"]
    return ""


def _claim_data(response: dict[str, Any]) -> dict[str, Any]:
    data = response.get("data")
    if not isinstance(data, dict):
        raise WorkerRuntimeError("claim response is missing data")
    return data


def _resolved_worker_id() -> str:
    explicit = (os.environ.get("BACKLINK_WORKER_ID") or "").strip()
    return explicit or get_worker_instance_id()


def _resolve_command(command: Sequence[str]) -> list[str]:
    result = list(command)
    if result and result[0] == "--":
        result = result[1:]
    if not result:
        raise WorkerRuntimeError("item processor command is required after --")
    resolved = shutil.which(result[0], path=os.environ.get("PATH"))
    if resolved:
        result[0] = resolved
    return result


def _child_env(
    *,
    run_id: str,
    worker_id: str,
    worker_instance_id: str,
    run_item_id: str,
    claim_reason: str,
    guard_path: Path,
) -> dict[str, str]:
    env = os.environ.copy()
    env["SHIPMORE_RUN_ID"] = run_id
    env["BACKLINK_WORKER_ID"] = worker_id
    env["SHIPMORE_WORKER_INSTANCE_ID"] = worker_instance_id
    env["SHIPMORE_RUN_ITEM_ID"] = run_item_id
    env["SHIPMORE_CLAIM_REASON"] = claim_reason
    env["SHIPMORE_RECOVERY_MODE"] = "1" if claim_reason == "reused" else "0"
    env["SHIPMORE_MANAGED_LEASE"] = "1"
    env["SHIPMORE_LEASE_GUARD_PATH"] = str(guard_path)
    return env


def _wait_child(child: subprocess.Popen[str]) -> int:
    while True:
        code = child.poll()
        if code is not None:
            return code
        time.sleep(1)


def run_worker(
    client: ShipmoreQueueClient,
    *,
    run_id: str,
    item_command: Sequence[str],
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    heartbeat_interval: int = DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
    max_items: int | None = None,
    popen_factory=subprocess.Popen,
) -> int:
    command = _resolve_command(item_command)
    worker_id = client.require_worker_id()
    worker_instance_id = (
        os.environ.get("SHIPMORE_WORKER_INSTANCE_ID") or worker_id
    ).strip()
    pending_claim: dict[str, Any] | None = None
    completed_items = 0

    while max_items is None or completed_items < max_items:
        claim = pending_claim or client.claim(run_id, lease_seconds)
        pending_claim = None
        reason = _claim_reason(claim)

        if reason in STOP_REASONS:
            return 0
        if reason == "run_not_found":
            raise WorkerRuntimeError("Shipmore run was not found")
        if reason not in ACTIVE_REASONS:
            raise WorkerRuntimeError(f"unexpected claim reason: {reason or 'missing'}")

        task = _claim_data(claim)
        run_item_id = str(task.get("id") or "").strip()
        if not run_item_id:
            raise WorkerRuntimeError("claim data is missing runItemId")

        guard = lease_guard_path(run_item_id)
        keeper = LeaseKeeper(
            client,
            run_item_id,
            lease_seconds=lease_seconds,
            interval_seconds=heartbeat_interval,
            guard_path=guard,
        )
        try:
            keeper.start()
        except LeaseGuardError as exc:
            raise WorkerRuntimeError(
                f"initial heartbeat failed for {run_item_id}: {exc}"
            ) from exc

        env = _child_env(
            run_id=run_id,
            worker_id=worker_id,
            worker_instance_id=worker_instance_id,
            run_item_id=run_item_id,
            claim_reason=reason,
            guard_path=guard,
        )
        child = popen_factory(command, env=env, text=True)
        try:
            child_code = _wait_child(child)
        except KeyboardInterrupt:
            if child.poll() is None:
                child.terminate()
            keeper.stop("worker_interrupted")
            raise
        finally:
            keeper.stop("item_processor_exited")

        # Re-claim with the same stable worker ID. If the item was completed,
        # this safely leases the next item. If it was not completed, Shipmore
        # returns reason=reused with the same Run Item and we stop rather than
        # launching the processor a second time.
        post_claim = client.claim(run_id, lease_seconds)
        post_reason = _claim_reason(post_claim)

        if post_reason == "reused":
            post_data = _claim_data(post_claim)
            post_id = str(post_data.get("id") or "")
            if post_id == run_item_id:
                raise WorkerRuntimeError(
                    "item processor exited without terminal completion; "
                    "refusing automatic re-execution of the same Run Item"
                )

        if post_reason in ACTIVE_REASONS:
            pending_claim = post_claim
            completed_items += 1
            if child_code != 0:
                print(
                    f"item processor exited {child_code}, but Shipmore confirms "
                    "the previous item is terminal; continuing with next item",
                    file=sys.stderr,
                )
            continue

        if post_reason in STOP_REASONS:
            return 0
        if post_reason == "run_not_found":
            raise WorkerRuntimeError("Shipmore run disappeared after item processing")
        raise WorkerRuntimeError(
            f"unexpected post-item claim reason: {post_reason or 'missing'}"
        )

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Long-lived Shipmore worker runtime")
    parser.add_argument("--run-id", default=os.environ.get("SHIPMORE_RUN_ID"))
    parser.add_argument(
        "--lease-seconds",
        type=int,
        default=int(os.environ.get("SHIPMORE_LEASE_SECONDS", DEFAULT_LEASE_SECONDS)),
    )
    parser.add_argument(
        "--heartbeat-interval",
        type=int,
        default=int(
            os.environ.get(
                "SHIPMORE_HEARTBEAT_INTERVAL_SECONDS",
                DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
            )
        ),
    )
    parser.add_argument("--max-items", type=int)
    parser.add_argument("item_command", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if not args.run_id:
        print("--run-id or SHIPMORE_RUN_ID is required", file=sys.stderr)
        return 2

    worker_id = _resolved_worker_id()
    base_url = (os.environ.get("BACKLINK_APP_URL") or "").strip()
    token = (os.environ.get("BACKLINK_AGENT_TOKEN") or "").strip()
    if not base_url or not token:
        print("BACKLINK_APP_URL and BACKLINK_AGENT_TOKEN are required", file=sys.stderr)
        return 2

    client = ShipmoreQueueClient(
        base_url=base_url,
        token=token,
        worker_id=worker_id,
    )
    try:
        return run_worker(
            client,
            run_id=args.run_id,
            item_command=args.item_command,
            lease_seconds=args.lease_seconds,
            heartbeat_interval=args.heartbeat_interval,
            max_items=args.max_items,
        )
    except (WorkerRuntimeError, ShipmoreClientError, LeaseGuardError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
