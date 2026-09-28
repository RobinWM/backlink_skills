#!/usr/bin/env python3
"""Persistent globally unique identity for a Shipmore worker host."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import socket
import uuid
from typing import IO


DEFAULT_IDENTITY_PATH = Path.home() / ".shipmore" / "worker-instance-id"


class WorkerIdentityError(RuntimeError):
    pass


class WorkerProcessLock:
    """Cross-platform advisory lock preventing duplicate live worker IDs."""

    def __init__(self, worker_id: str) -> None:
        digest = uuid.uuid5(uuid.NAMESPACE_URL, worker_id).hex
        root = Path(
            os.environ.get(
                "SHIPMORE_WORKER_LOCK_DIR",
                str(Path.home() / ".shipmore" / "worker-locks"),
            )
        ).expanduser()
        self.path = root / f"{digest}.lock"
        self.handle: IO[str] | None = None

    def acquire(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = open(self.path, "a+", encoding="utf-8")
        try:
            if os.name == "nt":
                import msvcrt

                handle.seek(0, os.SEEK_END)
                if handle.tell() == 0:
                    handle.write("\0")
                    handle.flush()
                handle.seek(0)
                try:
                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                except OSError as exc:
                    raise WorkerIdentityError(
                        "another live process already owns this worker ID"
                    ) from exc
            else:
                import fcntl

                try:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError as exc:
                    raise WorkerIdentityError(
                        "another live process already owns this worker ID"
                    ) from exc
        except Exception:
            handle.close()
            raise
        self.handle = handle

    def release(self) -> None:
        if not self.handle:
            return
        try:
            if os.name == "nt":
                import msvcrt

                self.handle.seek(0)
                msvcrt.locking(self.handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
        finally:
            self.handle.close()
            self.handle = None

    def __enter__(self) -> "WorkerProcessLock":
        self.acquire()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()


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
