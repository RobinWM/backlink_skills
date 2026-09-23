#!/usr/bin/env python3
"""Inventory Semrush CSV exports without changing source files."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path


def inspect_csv(path: Path) -> dict[str, object]:
    row_count = 0
    nonblank_rows = 0
    error = ""
    headers: list[str] = []
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            headers = next(reader, [])
            for row in reader:
                row_count += 1
                if any(str(value).strip() for value in row):
                    nonblank_rows += 1
    except (OSError, UnicodeError, csv.Error) as exc:
        error = f"{type(exc).__name__}: {exc}"
    return {
        "file": str(path),
        "size_bytes": path.stat().st_size if path.exists() else 0,
        "headers": headers,
        "data_rows": row_count,
        "nonblank_data_rows": nonblank_rows,
        "error": error,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="审计 Semrush CSV 导出文件")
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()

    paths = sorted(args.input_dir.rglob("*.csv"))
    files = [inspect_csv(path) for path in paths]
    header_counts = Counter(tuple(item["headers"]) for item in files if not item["error"])
    report = {
        "input_directory": str(args.input_dir),
        "csv_files": len(files),
        "total_nonblank_data_rows": sum(int(item["nonblank_data_rows"]) for item in files),
        "empty_files": [item["file"] for item in files if not item["error"] and item["nonblank_data_rows"] == 0],
        "read_errors": [item for item in files if item["error"]],
        "header_variants": [
            {"headers": list(headers), "file_count": count}
            for headers, count in header_counts.most_common()
        ],
        "files": files,
    }
    output = json.dumps(report, ensure_ascii=False, indent=2)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(f"{output}\n", encoding="utf-8")
    print(output)
    return 1 if report["read_errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
