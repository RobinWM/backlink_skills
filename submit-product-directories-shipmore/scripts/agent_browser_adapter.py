#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Callable, Sequence

from final_action_guard import FinalActionError, FinalActionJournal, FINAL_ACTION_TYPES
from lease_keeper import (
    LeaseGuardError,
    assert_lease_guard_valid,
    refresh_lease_from_env,
)

AGENT_BROWSER_VERSION = "0.38.1"
DEFAULT_STATE_EXPIRE_DAYS = 7
DEFAULT_NAMESPACE = "shipmore"
DEFAULT_TIMEOUT_SECONDS = 45


class AgentBrowserError(RuntimeError):
    pass


def deterministic_session_id(run_item_id: str) -> str:
    value = (run_item_id or "").strip()
    if not value:
        raise AgentBrowserError("run_item_id is required")
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:32]
    return f"shipmore-{digest}"


def _load_json_output(raw: str) -> dict[str, Any]:
    text = (raw or "").strip()
    for candidate in [text, *reversed(text.splitlines())]:
        candidate = candidate.strip()
        if not candidate.startswith("{"):
            continue
        try:
            value = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise AgentBrowserError("agent-browser returned invalid JSON output")


def _data_value(payload: dict[str, Any], *keys: str) -> Any:
    data = payload.get("data")
    if isinstance(data, dict):
        for key in keys:
            if key in data:
                return data[key]
        if len(data) == 1:
            return next(iter(data.values()))
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _doctor_failures(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        status = value.get("status")
        if isinstance(status, str) and status.lower() in {"fail", "failed", "error"}:
            found.append(str(value.get("message") or value.get("id") or status))
        for child in value.values():
            found.extend(_doctor_failures(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_doctor_failures(child))
    return found


class AgentBrowserAdapter:
    def __init__(
        self,
        run_item_id: str,
        *,
        executable: str = "agent-browser",
        auth_state_path: str | None = None,
        expected_version: str = AGENT_BROWSER_VERSION,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        env: dict[str, str] | None = None,
        runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    ):
        self.run_item_id = run_item_id
        self.session_id = deterministic_session_id(run_item_id)
        self.executable = executable
        self.auth_state_path = auth_state_path or os.environ.get(
            "BACKLINK_AGENT_BROWSER_AUTH_STATE"
        )
        self.expected_version = expected_version
        self.timeout = timeout
        self.runner = runner
        self.env = os.environ.copy()
        if env:
            self.env.update(env)
        self.env.setdefault(
            "AGENT_BROWSER_STATE_EXPIRE_DAYS",
            str(DEFAULT_STATE_EXPIRE_DAYS),
        )
        self.env.setdefault("AGENT_BROWSER_NAMESPACE", DEFAULT_NAMESPACE)
        self.lease_guard_path = self.env.get("SHIPMORE_LEASE_GUARD_PATH")
        self.managed_lease = self.env.get("SHIPMORE_MANAGED_LEASE") == "1"

    def _assert_mutation_allowed(self) -> None:
        if self.managed_lease and not self.lease_guard_path:
            raise AgentBrowserError(
                "managed Shipmore worker is missing SHIPMORE_LEASE_GUARD_PATH"
            )
        if self.lease_guard_path:
            worker_id = (self.env.get("BACKLINK_WORKER_ID") or "").strip()
            if self.managed_lease and not worker_id:
                raise AgentBrowserError(
                    "managed Shipmore worker is missing BACKLINK_WORKER_ID"
                )
            try:
                assert_lease_guard_valid(
                    self.lease_guard_path,
                    expected_worker_id=worker_id or None,
                )
            except LeaseGuardError as exc:
                raise AgentBrowserError(str(exc)) from exc

    def _redact(self, text: str) -> str:
        result = text or ""
        if self.auth_state_path:
            result = result.replace(self.auth_state_path, "[auth-state]")
        key = self.env.get("AGENT_BROWSER_ENCRYPTION_KEY")
        if key:
            result = result.replace(key, "[encryption-key]")
        return result

    def _run(
        self,
        args: Sequence[str],
        *,
        include_session: bool = True,
        restore: bool = True,
        global_args: Sequence[str] = (),
        json_output: bool = False,
        timeout: int | None = None,
        include_namespace: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        resolved_executable = shutil.which(
            self.executable,
            path=self.env.get("PATH"),
        ) or self.executable
        command = [resolved_executable]
        if include_namespace and self.env.get("AGENT_BROWSER_NAMESPACE"):
            command.extend(["--namespace", self.env["AGENT_BROWSER_NAMESPACE"]])
        if include_session:
            command.extend(["--session", self.session_id])
            if restore:
                command.extend(["--restore", "--restore-save", "auto"])
        command.extend(global_args)
        command.extend(args)
        if json_output:
            command.append("--json")
        try:
            completed = self.runner(
                command,
                capture_output=True,
                text=True,
                timeout=timeout or self.timeout,
                env=self.env,
                check=False,
            )
        except FileNotFoundError as exc:
            raise AgentBrowserError(
                f"agent-browser {self.expected_version} is not installed"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise AgentBrowserError("agent-browser command timed out") from exc
        if completed.returncode != 0:
            detail = self._redact(
                (completed.stderr or completed.stdout or "command failed").strip()
            )
            raise AgentBrowserError(detail)
        return completed

    def _run_json(self, args: Sequence[str], **kwargs: Any) -> dict[str, Any]:
        payload = _load_json_output(
            self._run(args, json_output=True, **kwargs).stdout
        )
        if payload.get("success") is False:
            raise AgentBrowserError(
                self._redact(
                    str(payload.get("message") or payload.get("error") or "command failed")
                )
            )
        return payload

    def version(self) -> str:
        output = self._run(
            ["--version"], include_session=False, restore=False, include_namespace=False
        ).stdout
        match = re.search(r"(\d+\.\d+\.\d+)", output)
        if not match:
            raise AgentBrowserError("Could not parse agent-browser version")
        return match.group(1)

    def doctor(self) -> dict[str, Any]:
        payload = self._run_json(
            ["doctor", "--offline", "--quick"],
            include_session=False,
            restore=False,
            include_namespace=False,
            timeout=max(self.timeout, 90),
        )
        failures = _doctor_failures(payload)
        if failures:
            raise AgentBrowserError(
                "agent-browser doctor failed: " + "; ".join(failures[:5])
            )
        return payload

    def preflight(self, *, production: bool = True) -> dict[str, Any]:
        current = self.version()
        if current != self.expected_version:
            raise AgentBrowserError(
                f"agent-browser version mismatch: expected {self.expected_version}, got {current}"
            )
        encryption_key = self.env.get("AGENT_BROWSER_ENCRYPTION_KEY", "")
        if production and not re.fullmatch(r"[0-9a-fA-F]{64}", encryption_key):
            raise AgentBrowserError(
                "AGENT_BROWSER_ENCRYPTION_KEY must be exactly 64 hex characters in production"
            )
        if self.auth_state_path:
            seed = Path(self.auth_state_path).expanduser()
            if not seed.is_file() or seed.stat().st_size <= 0:
                raise AgentBrowserError("auth seed is missing or empty")
        return {"version": current, "doctor": self.doctor()}

    def open(
        self,
        url: str,
        *,
        restore_check_url: str | None = None,
        restore_check_text: str | None = None,
        restore_check_fn: str | None = None,
    ) -> dict[str, Any]:
        self._assert_mutation_allowed()
        flags: list[str] = []
        if restore_check_url:
            flags.extend(["--restore-check-url", restore_check_url])
        if restore_check_text:
            flags.extend(["--restore-check-text", restore_check_text])
        if restore_check_fn:
            flags.extend(["--restore-check-fn", restore_check_fn])
        return self._run_json(["open", url], global_args=flags)

    def bootstrap(self, url: str, *, fresh_task: bool, **restore_checks: Any):
        self._assert_mutation_allowed()
        if fresh_task and self.auth_state_path:
            seed = Path(self.auth_state_path).expanduser().resolve()
            if not seed.is_file() or seed.stat().st_size <= 0:
                raise AgentBrowserError("auth seed is missing or empty")
            self._run_json(["open", "about:blank"])
            self._run_json(["state", "load", str(seed)])
        return self.open(url, **restore_checks)

    def snapshot(self) -> dict[str, Any]:
        return self._run_json(["snapshot", "-i"])

    def get_url(self) -> str:
        value = _data_value(self._run_json(["get", "url"]), "url", "value")
        if not isinstance(value, str):
            raise AgentBrowserError("Could not read current URL")
        return value

    def get_value(self, selector: str) -> str:
        value = _data_value(
            self._run_json(["get", "value", selector]),
            "value",
        )
        return "" if value is None else str(value)

    def _bool(self, name: str, selector: str) -> bool:
        value = _data_value(
            self._run_json(["is", name, selector]),
            name,
            "value",
            "result",
        )
        return bool(value)

    def _assert_writable(self, selector: str, *, require_visible: bool = True) -> None:
        self._assert_mutation_allowed()
        if require_visible and not self._bool("visible", selector):
            raise AgentBrowserError(f"{selector} is not visible")
        if not self._bool("enabled", selector):
            raise AgentBrowserError(f"{selector} is not enabled")
        readonly = _data_value(
            self._run_json(["get", "attr", selector, "readonly"]),
            "value",
            "readonly",
        )
        if readonly is not None:
            raise AgentBrowserError(f"{selector} is readonly")

    def safe_fill(self, selector: str, value: str) -> str:
        self._assert_writable(selector)
        self._run(["fill", selector, value])
        actual = self.get_value(selector)
        if actual != value:
            raise AgentBrowserError(
                f"fill read-back mismatch for {selector}: expected length "
                f"{len(value)}, got {len(actual)}"
            )
        return actual

    def safe_select(self, selector: str, options: Sequence[str]) -> str:
        if not options:
            raise AgentBrowserError("At least one option is required")
        self._assert_writable(selector)
        self._run(["select", selector, *options])
        return self.get_value(selector)

    def safe_check(self, selector: str, checked: bool = True) -> bool:
        self._assert_writable(selector)
        self._run(["check" if checked else "uncheck", selector])
        actual = self._bool("checked", selector)
        if actual != checked:
            raise AgentBrowserError(f"checkbox read-back mismatch for {selector}")
        return actual

    def safe_upload(self, selector: str, file_path: str) -> str:
        # Native file inputs are commonly hidden behind a visible custom upload button.
        self._assert_writable(selector, require_visible=False)
        path = Path(file_path).expanduser().resolve()
        if not path.is_file():
            raise AgentBrowserError("Upload source does not exist")
        if path.stat().st_size <= 0:
            raise AgentBrowserError("Upload source is empty")
        self._run(["upload", selector, str(path)])
        actual = self.get_value(selector)
        if not actual:
            raise AgentBrowserError("Upload has no read-back value")
        return actual

    def click(self, selector: str) -> None:
        self._assert_mutation_allowed()
        if not self._bool("visible", selector) or not self._bool("enabled", selector):
            raise AgentBrowserError(f"{selector} is not actionable")
        self._run(["click", selector])

    def final_click(
        self,
        action_type: str,
        selector: str,
        *,
        lease_seconds: int = 300,
    ) -> dict[str, Any]:
        if action_type not in FINAL_ACTION_TYPES:
            raise AgentBrowserError(f"unsupported final action type: {action_type}")
        if not self._bool("visible", selector) or not self._bool("enabled", selector):
            raise AgentBrowserError(f"{selector} is not actionable")

        try:
            refresh_lease_from_env(
                self.run_item_id,
                lease_seconds=lease_seconds,
            )
        except LeaseGuardError as exc:
            raise AgentBrowserError(
                f"final action heartbeat failed: {exc}"
            ) from exc

        self._assert_mutation_allowed()
        worker_id = (self.env.get("BACKLINK_WORKER_ID") or "").strip()
        if not worker_id:
            raise AgentBrowserError("BACKLINK_WORKER_ID is required for final action")

        journal = FinalActionJournal(self.run_item_id, action_type)
        try:
            record = journal.prepare(
                worker_id=worker_id,
                session_id=self.session_id,
            )
            journal.mark_attempting()
        except FinalActionError as exc:
            raise AgentBrowserError(str(exc)) from exc

        try:
            self._run(["click", selector])
        except AgentBrowserError:
            try:
                journal.resolve("outcome_unknown")
            except FinalActionError:
                pass
            raise

        return journal.mark_dispatched()

    def final_action_status(self, action_type: str) -> dict[str, Any] | None:
        return FinalActionJournal(self.run_item_id, action_type).read()

    def resolve_final_action(
        self,
        action_type: str,
        outcome: str,
    ) -> dict[str, Any]:
        try:
            return FinalActionJournal(self.run_item_id, action_type).resolve(outcome)
        except FinalActionError as exc:
            raise AgentBrowserError(str(exc)) from exc

    def wait_text(self, text: str) -> None:
        self._run(["wait", "--text", text])

    def diagnostics(self, screenshot_path: str | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {}
        checks = {
            "url": ["get", "url"],
            "snapshot": ["snapshot", "-i"],
            "errors": ["errors"],
            "console": ["console"],
            "network": ["network", "requests"],
        }
        for name, args in checks.items():
            try:
                result[name] = self._run_json(args)
            except AgentBrowserError as exc:
                result[name] = {"error": self._redact(str(exc))}
        if screenshot_path:
            try:
                result["screenshot"] = self._run(
                    ["screenshot", screenshot_path]
                ).stdout.strip()
            except AgentBrowserError as exc:
                result["screenshot"] = {"error": self._redact(str(exc))}
        return result

    def close(self) -> None:
        self._run(["close"])

    def clean_states(self, days: int = DEFAULT_STATE_EXPIRE_DAYS) -> None:
        if days < 1:
            raise AgentBrowserError("cleanup days must be >= 1")
        self._run(
            ["state", "clean", "--older-than", str(days)],
            include_session=False,
            restore=False,
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent-browser", default="agent-browser")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("session-id")
    p.add_argument("--run-item-id", required=True)
    p = sub.add_parser("preflight")
    p.add_argument("--dev", action="store_true")
    p = sub.add_parser("cleanup")
    p.add_argument("--days", type=int, default=DEFAULT_STATE_EXPIRE_DAYS)

    p = sub.add_parser("bootstrap")
    p.add_argument("--run-item-id", required=True)
    p.add_argument("--url", required=True)
    p.add_argument("--fresh-task", action="store_true")
    p.add_argument("--restore-check-url")
    p.add_argument("--restore-check-text")
    p.add_argument("--restore-check-fn")

    p = sub.add_parser("snapshot")
    p.add_argument("--run-item-id", required=True)

    p = sub.add_parser("safe-fill")
    p.add_argument("--run-item-id", required=True)
    p.add_argument("--selector", required=True)
    p.add_argument("--value", required=True)

    p = sub.add_parser("safe-upload")
    p.add_argument("--run-item-id", required=True)
    p.add_argument("--selector", required=True)
    p.add_argument("--file", required=True)

    p = sub.add_parser("safe-select")
    p.add_argument("--run-item-id", required=True)
    p.add_argument("--selector", required=True)
    p.add_argument("--option", action="append", required=True)

    p = sub.add_parser("safe-check")
    p.add_argument("--run-item-id", required=True)
    p.add_argument("--selector", required=True)
    p.add_argument("--unchecked", action="store_true")

    p = sub.add_parser("click")
    p.add_argument("--run-item-id", required=True)
    p.add_argument("--selector", required=True)

    p = sub.add_parser("diagnostics")
    p.add_argument("--run-item-id", required=True)
    p.add_argument("--screenshot")

    p = sub.add_parser("final-click")
    p.add_argument("--run-item-id", required=True)
    p.add_argument("--action-type", required=True, choices=sorted(FINAL_ACTION_TYPES))
    p.add_argument("--selector", required=True)
    p.add_argument("--lease-seconds", type=int, default=300)

    p = sub.add_parser("final-action-status")
    p.add_argument("--run-item-id", required=True)
    p.add_argument("--action-type", required=True, choices=sorted(FINAL_ACTION_TYPES))

    p = sub.add_parser("final-action-resolve")
    p.add_argument("--run-item-id", required=True)
    p.add_argument("--action-type", required=True, choices=sorted(FINAL_ACTION_TYPES))
    p.add_argument(
        "--outcome",
        required=True,
        choices=["confirmed", "outcome_unknown", "rejected"],
    )

    args = parser.parse_args()
    try:
        if args.command == "session-id":
            print(deterministic_session_id(args.run_item_id))
            return 0
        adapter = AgentBrowserAdapter(
            getattr(args, "run_item_id", "runtime"),
            executable=args.agent_browser,
        )
        if args.command == "preflight":
            print(json.dumps(adapter.preflight(production=not args.dev), indent=2))
        elif args.command == "cleanup":
            adapter.clean_states(args.days)
            print(json.dumps({"success": True, "days": args.days}))
        elif args.command == "bootstrap":
            result = adapter.bootstrap(
                args.url,
                fresh_task=args.fresh_task,
                restore_check_url=args.restore_check_url,
                restore_check_text=args.restore_check_text,
                restore_check_fn=args.restore_check_fn,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
        elif args.command == "snapshot":
            print(json.dumps(adapter.snapshot(), ensure_ascii=False, indent=2))
        elif args.command == "safe-fill":
            print(json.dumps({"value": adapter.safe_fill(args.selector, args.value)}))
        elif args.command == "safe-upload":
            print(json.dumps({"value": adapter.safe_upload(args.selector, args.file)}))
        elif args.command == "safe-select":
            print(json.dumps({"value": adapter.safe_select(args.selector, args.option)}))
        elif args.command == "safe-check":
            print(json.dumps({"checked": adapter.safe_check(args.selector, not args.unchecked)}))
        elif args.command == "click":
            adapter.click(args.selector)
            print(json.dumps({"success": True}))
        elif args.command == "diagnostics":
            print(json.dumps(adapter.diagnostics(args.screenshot), ensure_ascii=False, indent=2))
        elif args.command == "final-click":
            print(
                json.dumps(
                    adapter.final_click(
                        args.action_type,
                        args.selector,
                        lease_seconds=args.lease_seconds,
                    ),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "final-action-status":
            print(
                json.dumps(
                    adapter.final_action_status(args.action_type),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        elif args.command == "final-action-resolve":
            print(
                json.dumps(
                    adapter.resolve_final_action(args.action_type, args.outcome),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        return 0
    except AgentBrowserError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
