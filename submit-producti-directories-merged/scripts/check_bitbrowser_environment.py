#!/usr/bin/env python3
"""Read-only health check for local BitBrowser runtimes."""

from __future__ import annotations

import argparse
import json
import platform
import plistlib
from pathlib import Path


def app_version(path: Path) -> str | None:
    plist = path / "Contents" / "Info.plist"
    if not plist.exists():
        return None
    try:
        with plist.open("rb") as handle:
            data = plistlib.load(handle)
        return str(data.get("CFBundleShortVersionString") or "unknown")
    except (OSError, plistlib.InvalidFileException):
        return "unreadable"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    root = Path.home() / "Library/Application Support/BitBrowser/Chrome-bin"
    apps = sorted(root.glob("*/*/BitBrowser.app"))
    runtimes = [
        {"path": str(app), "version": app_version(app)}
        for app in apps
    ]
    report = {
        "os": platform.platform(),
        "machine": platform.machine(),
        "bitbrowser_root": str(root),
        "runtime_count": len(runtimes),
        "runtimes": runtimes,
        "recommended_backend": "Computer Use with the exact BitBrowser.app path",
        "browseract_enabled": False,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"OS: {report['os']}")
        print(f"Machine: {report['machine']}")
        print(f"BitBrowser runtimes: {len(runtimes)}")
        for runtime in runtimes:
            print(f"- {runtime['version']}: {runtime['path']}")
        print("Backend: Computer Use (BrowserAct disabled)")
    return 0 if runtimes else 1


if __name__ == "__main__":
    raise SystemExit(main())
