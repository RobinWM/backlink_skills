#!/usr/bin/env python3
"""Validate a consolidated backlink candidate-pool CSV before batch export."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


REQUIRED = {
    "record_id",
    "root_domain",
    "normalized_url",
    "entry_type",
    "condition",
    "fee_status",
    "suitable_brands",
    "source",
    "evidence_note",
    "pool",
    "status",
    "batch_id",
}
FEE_VALUES = {"明确免费", "明确付费", "费用待确认"}
POOL_VALUES = {"可执行池", "备用池"}
STATUS_VALUES = {
    "待检测",
    "已找到入口",
    "可进入批量表",
    "已分配批次",
    "已导出",
    "已排除",
}
TRACKING_KEYS = {"ref", "source", "campaign", "fbclid", "gclid"}


def clean(value: object) -> str:
    return "" if value is None else str(value).strip()


def normalized_url(value: str) -> tuple[str, str]:
    raw = clean(value)
    if not raw:
        return "", ""
    if "://" not in raw:
        raw = f"https://{raw.lstrip('/')}"
    parts = urlsplit(raw)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        return "", ""
    host = parts.hostname.lower().rstrip(".")
    if host.startswith("www."):
        host = host[4:]
    path = parts.path.rstrip("/") or "/"
    query = sorted(
        (key, value)
        for key, value in parse_qsl(parts.query, keep_blank_values=True)
        if not key.lower().startswith("utm_") and key.lower() not in TRACKING_KEYS
    )
    return urlunsplit((parts.scheme.lower(), host, path, urlencode(query), "")), host


def validate(path: Path) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        missing = sorted(REQUIRED - headers)
        if missing:
            return {"path": str(path), "rows": 0, "errors": [f"缺少字段: {', '.join(missing)}"], "warnings": []}

        rows = list(reader)

    ids: dict[str, int] = {}
    urls: dict[str, int] = {}
    exported_batches: dict[str, set[str]] = {}
    for number, row in enumerate(rows, start=2):
        record_id = clean(row.get("record_id"))
        url, host = normalized_url(clean(row.get("normalized_url")))
        display_domain = clean(row.get("root_domain")).lower().removeprefix("www.").rstrip(".")
        fee = clean(row.get("fee_status"))
        pool = clean(row.get("pool"))
        status = clean(row.get("status"))
        condition = clean(row.get("condition"))
        brands = clean(row.get("suitable_brands"))
        batch_id = clean(row.get("batch_id"))

        for field in ("record_id", "root_domain", "normalized_url", "entry_type", "condition", "fee_status", "suitable_brands", "source", "evidence_note", "pool", "status"):
            if not clean(row.get(field)):
                errors.append(f"第{number}行缺少 {field}")
        if fee not in FEE_VALUES:
            errors.append(f"第{number}行 fee_status 非法: {fee}")
        if pool not in POOL_VALUES:
            errors.append(f"第{number}行 pool 非法: {pool}")
        if status not in STATUS_VALUES:
            errors.append(f"第{number}行 status 非法: {status}")
        if not url:
            errors.append(f"第{number}行 URL 无效")
        elif display_domain and display_domain != host:
            warnings.append(f"第{number}行域名列与 URL 主机名不同: {display_domain} != {host}")
        if fee == "费用待确认" and "费用待确认" not in condition:
            errors.append(f"第{number}行费用待确认但投递条件未标注")
        if fee == "明确免费" and "费用待确认" in condition:
            errors.append(f"第{number}行标为明确免费但条件仍写费用待确认")
        if not brands:
            errors.append(f"第{number}行没有适合品牌")
        if pool == "备用池" and status in {"已分配批次", "已导出"}:
            errors.append(f"第{number}行备用池记录不能处于 {status}")
        if status in {"已分配批次", "已导出"} and not batch_id:
            errors.append(f"第{number}行 {status} 但 batch_id 为空")

        if record_id:
            if record_id in ids:
                errors.append(f"第{number}行 record_id 与第{ids[record_id]}行重复: {record_id}")
            ids[record_id] = number
        if url:
            if url in urls:
                errors.append(f"第{number}行 URL 与第{urls[url]}行重复: {url}")
            urls[url] = number
        if batch_id and status == "已导出":
            exported_batches.setdefault(batch_id, set()).add(record_id)

    return {
        "path": str(path),
        "rows": len(rows),
        "errors": errors,
        "warnings": warnings,
        "exported_batches": {key: len(value) for key, value in sorted(exported_batches.items())},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    report = validate(args.input)
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(f"{output}\n", encoding="utf-8")
    print(output)
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
