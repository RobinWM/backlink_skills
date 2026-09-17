#!/usr/bin/env python3
"""Validate packaging invariants of the minimal visual payload."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from html.parser import HTMLParser
from pathlib import Path

TEMPLATE_ID = "BLOG_3P_VISUAL_PAYLOAD"
TEMPLATE_VERSION = "2"
TEMPLATE_ASSET_SHA256 = "e03ef4a8af8fd911c47fe9a3ee7983eddd36c628a7eb334bf7b60cc5ac22b8c6"
EXPECTED_ORDER = ["blog-title", "article-body", "seo-metadata", "seo-title", "seo-tags", "seo-description"]
CTA_FIELDS = ("anchor_text", "product_name", "product_destination_url", "product_evidence_path", "reader_task_relevance", "relationship_disclosure")


def normalize_text(value: str) -> str:
    return " ".join(value.split())


def required_cta_from_package(path: Path) -> dict[str, str]:
    try:
        package = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"article-package must be valid JSON: {exc}") from exc
    if not isinstance(package, dict) or package.get("schema_version") not in {"1.2", "1.3"}:
        raise ValueError("article-package must use schema_version 1.2 or 1.3")
    cta = package.get("cta")
    if not isinstance(cta, dict) or cta.get("mode") != "SECONDARY_RECOMMENDATION":
        raise ValueError("article-package must declare a required SECONDARY_RECOMMENDATION CTA")
    missing = [field for field in CTA_FIELDS if not isinstance(cta.get(field), str) or not cta[field].strip()]
    if missing:
        raise ValueError("article-package required CTA is missing: " + ", ".join(missing))
    return {field: cta[field].strip() for field in CTA_FIELDS}


class PayloadParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_body = 0
        self.template = False
        self.template_assets = ""
        self.ids = []
        self.bad_links = []
        self.cards = 0
        self.coverage_zones = []
        self.card_alt_texts = []
        self._current_card_text = None
        self.body_text = []
        self.anchors = []
        self._anchor_href = None
        self._anchor_text = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag == "main" and data.get("data-template-id") == TEMPLATE_ID and data.get("data-template-version") == TEMPLATE_VERSION:
            self.template = True
            self.template_assets = data.get("data-template-assets-sha256", "")
        if data.get("id"):
            self.ids.append(data["id"])
        if data.get("id") == "article-body":
            self.in_body = 1
        elif self.in_body:
            self.in_body += 1
        if self.in_body and tag == "a" and not data.get("href", "").strip():
            self.bad_links.append("empty href")
        if self.in_body and tag == "a":
            self._anchor_href = data.get("href", "").strip()
            self._anchor_text = []
        if self.in_body and "image-placeholder" in data.get("class", "").split():
            self.cards += 1
            self.coverage_zones.append(data.get("data-coverage-zone", "UNSPECIFIED").upper())
            self._current_card_text = []

    def handle_data(self, data):
        if self.in_body:
            self.body_text.append(data)
        if self._anchor_href is not None:
            self._anchor_text.append(data)
        if self._current_card_text is not None:
            self._current_card_text.append(data)

    def handle_endtag(self, tag):
        if tag == "a" and self._anchor_href is not None:
            self.anchors.append((self._anchor_href, normalize_text("".join(self._anchor_text))))
            self._anchor_href = None
            self._anchor_text = []
        if tag == "aside" and self._current_card_text is not None:
            self.card_alt_texts.append("".join(self._current_card_text))
            self._current_card_text = None
        if self.in_body:
            self.in_body -= 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--payload", type=Path, required=True)
    parser.add_argument("--article-package", type=Path, required=True)
    parser.add_argument(
        "--title-transfer-mode", "--heading-transport", "--mode",
        dest="title_transfer_mode",
        choices=["SEPARATE_TITLE_FIELD", "TITLE_IN_BODY", "BODY_H1_REQUIRED"],
        default="SEPARATE_TITLE_FIELD",
        help="Local copy-selection metadata only; not evidence of public heading hierarchy.",
    )
    parser.add_argument("--required-coverage-zones", default="")
    parser.add_argument("--minimum-image-cards", type=int, default=0)
    args = parser.parse_args()
    source = args.payload.read_text(encoding="utf-8")
    try:
        cta = required_cta_from_package(args.article_package)
    except ValueError as exc:
        print("PAYLOAD_INVALID\n" + str(exc))
        return 1
    parsed = PayloadParser()
    parsed.feed(source)
    parsed.close()
    errors = []
    if not parsed.template:
        errors.append(f"payload must use fixed template {TEMPLATE_ID}@{TEMPLATE_VERSION}")
    if parsed.template_assets != TEMPLATE_ASSET_SHA256:
        errors.append("fixed-template asset signature is missing or invalid")
    if f"{TEMPLATE_ID}@{TEMPLATE_VERSION}: compiler-generated minimal template" not in source:
        errors.append("missing fixed-template compiler signature")
    style = re.search(r"<style>(.*?)</style>", source, re.DOTALL)
    if not style or hashlib.sha256(style.group(1).encode("utf-8")).hexdigest() != TEMPLATE_ASSET_SHA256:
        errors.append("fixed-template CSS was modified")
    if re.search(r"<script\\b|<button\\b", source, re.IGNORECASE):
        errors.append("minimal visual payload must not contain scripts or copy buttons")
    positions = [parsed.ids.index(value) if value in parsed.ids else -1 for value in EXPECTED_ORDER]
    if positions != sorted(positions) or -1 in positions:
        errors.append("payload must follow title, body, SEO title, tags and description order")
    # Local markup is an authoring and copy-selection aid only. Platform paste
    # behavior varies, so it cannot establish or fail public heading hierarchy.
    errors.extend(parsed.bad_links)
    expected_anchor = normalize_text(cta["anchor_text"])
    expected_href = cta["product_destination_url"]
    if not any(href == expected_href and text == expected_anchor for href, text in parsed.anchors):
        errors.append("payload must preserve the required CTA's exact visible anchor text and href")
    disclosure = cta["relationship_disclosure"]
    if disclosure != "NOT_APPLICABLE" and normalize_text(disclosure) not in normalize_text("".join(parsed.body_text)):
        errors.append("payload must preserve the required CTA relationship disclosure")
    required_zones = [zone.strip().upper() for zone in args.required_coverage_zones.split(",") if zone.strip()]
    missing_zones = [zone for zone in required_zones if zone not in parsed.coverage_zones]
    if missing_zones:
        errors.append("missing image-placeholder coverage zones: " + ",".join(missing_zones))
    if parsed.cards < args.minimum_image_cards:
        errors.append(f"minimum image placeholders is {args.minimum_image_cards}, found {parsed.cards}")
    if len(parsed.card_alt_texts) != parsed.cards or any("Alt：" not in text and "Alt:" not in text for text in parsed.card_alt_texts):
        errors.append("every image placeholder needs visible Alt text")
    if errors:
        print("PAYLOAD_INVALID\n" + "\n".join(errors))
        return 1
    print(
        "PAYLOAD_VALID"
        + "\ntitle_transfer_mode=" + ("TITLE_IN_BODY" if args.title_transfer_mode == "BODY_H1_REQUIRED" else args.title_transfer_mode)
        + f"\nimage_placeholders={parsed.cards}\ncoverage_zones=" + ",".join(parsed.coverage_zones)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
