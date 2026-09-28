#!/usr/bin/env python3
"""Conservative sanitization for browser diagnostic payloads."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlsplit, urlunsplit


SENSITIVE_KEY_RE = re.compile(
    r"(?i)(authorization|proxy-authorization|cookie|set-cookie|x-api-key|"
    r"api[-_]?key|access[-_]?token|refresh[-_]?token|id[-_]?token|"
    r"password|passwd|secret|otp|magic[-_]?link|verification[-_]?code)"
)
BODY_KEY_RE = re.compile(
    r"(?i)(postdata|requestbody|responsebody|formdata|payload|rawbody|body)"
)
EMAIL_RE = re.compile(
    r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
    re.I,
)
CREDENTIAL_TEXT_RE = re.compile(
    r"(?i)\b(authorization|cookie|set-cookie|x-api-key|api[-_]?key|"
    r"token|password|secret|otp)\s*[:=]\s*([^\s,;]+)"
)
HTTP_URL_RE = re.compile(r"https?://[^\s\"'<>]+")


def _sanitize_path(path: str) -> str:
    safe_segments = []
    for segment in path.split("/"):
        cleaned = EMAIL_RE.sub("[email]", segment)
        if len(cleaned) >= 24 and re.fullmatch(r"[A-Za-z0-9._~-]+", cleaned):
            cleaned = "[opaque]"
        safe_segments.append(cleaned)
    return "/".join(safe_segments)


def strip_url_secrets(url: str) -> str:
    try:
        parsed = urlsplit(url)
    except ValueError:
        return "[url]"
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return "[url]"
    return urlunsplit(
        (
            parsed.scheme,
            parsed.netloc,
            _sanitize_path(parsed.path),
            "",
            "",
        )
    )


def sanitize_text(value: str) -> str:
    result = EMAIL_RE.sub("[email]", value)
    result = CREDENTIAL_TEXT_RE.sub(
        lambda match: f"{match.group(1)}=[redacted]",
        result,
    )
    result = HTTP_URL_RE.sub(
        lambda match: strip_url_secrets(match.group(0)),
        result,
    )
    return result


def sanitize_diagnostic(value: Any, key: str | None = None) -> Any:
    normalized_key = key or ""
    if SENSITIVE_KEY_RE.search(normalized_key) or BODY_KEY_RE.search(normalized_key):
        return "[redacted]"
    if isinstance(value, dict):
        return {
            str(child_key): sanitize_diagnostic(child, str(child_key))
            for child_key, child in value.items()
        }
    if isinstance(value, list):
        return [sanitize_diagnostic(child, normalized_key) for child in value]
    if isinstance(value, str):
        if "url" in normalized_key.lower():
            return strip_url_secrets(value)
        return sanitize_text(value)
    return value
