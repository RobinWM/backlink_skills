#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from typing import Sequence

from worker_identity import WorkerIdentityError, get_worker_instance_id
from agent_browser_adapter import (
    AgentBrowserAdapter,
    AgentBrowserError,
    DEFAULT_NAMESPACE,
    DEFAULT_STATE_EXPIRE_DAYS,
)

DEFAULT_CONCURRENCY = 4
MAX_CONCURRENCY = 16


def stop_children(
    children: list[tuple[int, subprocess.Popen[str]]],
    *,
    wait_seconds: int = 10,
) -> None:
    for _, child in children:
        if child.poll() is None:
            child.terminate()
    for _, child in children:
        if child.poll() is not None:
            continue
        try:
            child.wait(timeout=wait_seconds)
        except subprocess.TimeoutExpired:
            child.kill()


def supervise_children(
    children: list[tuple[int, subprocess.Popen[str]]],
    *,
    poll_interval: float = 0.5,
) -> dict[int, int]:
    active = {slot: child for slot, child in children}
    failures: dict[int, int] = {}
    while active:
        for slot, child in list(active.items()):
            code = child.poll()
            if code is None:
                continue
            del active[slot]
            if code != 0:
                failures[slot] = code
                stop_children(list(active.items()))
                return failures
        if active:
            time.sleep(poll_interval)
    return failures


def build_worker_env(
    base_env: dict[str, str],
    *,
    run_id: str,
    worker_id_prefix: str | None,
    slot: int,
    concurrency: int,
) -> dict[str, str]:
    env = dict(base_env)
    resolved_prefix = (
        (worker_id_prefix or "").strip()
        or (env.get("SHIPMORE_WORKER_INSTANCE_ID") or "").strip()
        or get_worker_instance_id()
    )
    env["SHIPMORE_RUN_ID"] = run_id
    env["SHIPMORE_POOL_SLOT"] = str(slot)
    env["SHIPMORE_POOL_SIZE"] = str(concurrency)
    env["SHIPMORE_CONCURRENCY"] = str(concurrency)
    env["SHIPMORE_WORKER_INSTANCE_ID"] = resolved_prefix
    env["BACKLINK_WORKER_ID"] = f"{resolved_prefix}-{slot:02d}"
    env.setdefault("AGENT_BROWSER_STATE_EXPIRE_DAYS", str(DEFAULT_STATE_EXPIRE_DAYS))
    env.setdefault("AGENT_BROWSER_NAMESPACE", DEFAULT_NAMESPACE)
    return env


def run_pool(
    run_id: str,
    concurrency: int,
    worker_id_prefix: str | None,
    worker_command: Sequence[str],
    *,
    skip_preflight: bool = False,
) -> int:
    command = list(worker_command)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        raise ValueError("worker command is required after --")
    resolved = shutil.which(command[0], path=os.environ.get("PATH"))
    if resolved:
        command[0] = resolved
    if not 1 <= concurrency <= MAX_CONCURRENCY:
        raise ValueError(f"concurrency must be between 1 and {MAX_CONCURRENCY}")

    if not skip_preflight:
        adapter = AgentBrowserAdapter("pool-preflight")
        adapter.preflight(production=True)
        cleanup = adapter.clean_terminal_states()
        if cleanup.get("success") is False:
            raise AgentBrowserError(
                "lifecycle-aware terminal state cleanup failed"
            )

    children: list[tuple[int, subprocess.Popen[str]]] = []
    try:
        for slot in range(1, concurrency + 1):
            env = build_worker_env(
                os.environ,
                run_id=run_id,
                worker_id_prefix=worker_id_prefix,
                slot=slot,
                concurrency=concurrency,
            )
            children.append((slot, subprocess.Popen(command, env=env, text=True)))

        failures = supervise_children(children)
        if failures:
            print(
                "worker pool failures: "
                + ", ".join(f"slot {slot}={code}" for slot, code in failures.items()),
                file=sys.stderr,
            )
            return 1
        return 0
    except KeyboardInterrupt:
        stop_children(children)
        return 130


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=os.environ.get("SHIPMORE_RUN_ID"))
    parser.add_argument(
        "--concurrency",
        type=int,
        default=int(os.environ.get("SHIPMORE_CONCURRENCY", DEFAULT_CONCURRENCY)),
    )
    parser.add_argument(
        "--worker-id-prefix",
        default=os.environ.get("BACKLINK_WORKER_ID_PREFIX"),
    )
    parser.add_argument("--skip-preflight", action="store_true")
    parser.add_argument("worker_command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if not args.run_id:
        print("--run-id or SHIPMORE_RUN_ID is required", file=sys.stderr)
        return 2
    try:
        return run_pool(
            args.run_id,
            args.concurrency,
            args.worker_id_prefix,
            args.worker_command,
            skip_preflight=args.skip_preflight,
        )
    except (ValueError, AgentBrowserError, WorkerIdentityError) as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
