#!/usr/bin/env python3
"""Validate the four visible columns before building an execution workbook."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


REQUIRED = ["域名", "URL", "投递条件", "适合品牌网站"]
TRACKING_KEYS = {"ref", "source", "campaign", "fbclid", "gclid"}


def normalize_url(value: str) -> tuple[str, str]:
    raw = value.strip()
    if not raw:
        return "", ""
    if "://" not in raw:
        raw = f"https://{raw.lstrip('/')}"
    parts = urlsplit(raw)
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        return "", ""
    host = parts.hostname.lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    path = parts.path.rstrip("/") or "/"
    query = sorted(
        (key, val)
        for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_KEYS
    )
    return urlunsplit((parts.scheme.lower(), host, path, urlencode(query), "")), host


def main() -> int:
    parser = argparse.ArgumentParser(description="校验外链执行表导出 CSV")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []
    seen_urls: dict[str, int] = {}
    with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        missing = [field for field in REQUIRED if field not in headers]
        rows = list(reader)

    if missing:
        errors.append(f"缺少字段: {', '.join(missing)}")
    for number, row in enumerate(rows, start=2):
        for field in REQUIRED:
            if not str(row.get(field, "")).strip():
                errors.append(f"第{number}行缺少 {field}")
        normalized, host = normalize_url(str(row.get("URL", "")))
        display_domain = str(row.get("域名", "")).strip().lower().removeprefix("www.").rstrip(".")
        if not normalized:
            errors.append(f"第{number}行 URL 无效")
        elif normalized in seen_urls:
            errors.append(f"第{number}行 URL 与第{seen_urls[normalized]}行重复")
        else:
            seen_urls[normalized] = number
        if host and display_domain and host != display_domain:
            warnings.append(f"第{number}行域名与 URL 主机名不同: {display_domain} != {host}")

    report = {
        "input": str(args.input),
        "rows": len(rows),
        "errors": errors,
        "warnings": warnings,
    }
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(f"{output}\n", encoding="utf-8")
    print(output)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
