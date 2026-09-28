#!/usr/bin/env python3
"""Persistent globally unique identity for a Shipmore worker host."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import socket
import uuid


DEFAULT_IDENTITY_PATH = Path.home() / ".shipmore" / "worker-instance-id"


class WorkerIdentityError(RuntimeError):
    pass


def _identity_path() -> Path:
    return Path(
        os.environ.get("SHIPMORE_WORKER_ID_FILE", str(DEFAULT_IDENTITY_PATH))
    ).expanduser()


def _safe_hostname() -> str:
    value = re.sub(r"[^A-Za-z0-9_-]+", "-", socket.gethostname()).strip("-_")
    return (value or "host")[:24]


def _create_identity(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    identity = f"shipmore-{_safe_hostname()}-{uuid.uuid4().hex[:16]}"
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return path.read_text(encoding="utf-8").strip()
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(identity + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return identity


def get_worker_instance_id() -> str:
    explicit = (os.environ.get("SHIPMORE_WORKER_INSTANCE_ID") or "").strip()
    if explicit:
        return explicit
    path = _identity_path()
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if not value:
            raise WorkerIdentityError("worker identity file is empty")
        return value
    return _create_identity(path)


def worker_id_for_slot(slot: int | None = None) -> str:
    base = get_worker_instance_id()
    if slot is None:
        return base
    if slot < 1:
        raise WorkerIdentityError("slot must be >= 1")
    return f"{base}-{slot:02d}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Shipmore worker identity")
    parser.add_argument("--slot", type=int)
    args = parser.parse_args()
    try:
        print(worker_id_for_slot(args.slot))
        return 0
    except WorkerIdentityError as exc:
        print(str(exc), file=os.sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
