#!/usr/bin/env python3
"""Audit an external-link auto-submission merged-skill campaign record."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


ALLOWED_STATUSES = {
    "not attempted",
    "form in progress",
    "draft saved",
    "submitted",
    "email sent — awaiting reply",
    "email send outcome unknown",
    "submission outcome unknown",
    "awaiting approval",
    "awaiting email verification",
    "published",
    "blocked — manual verification",
    "blocked — missing verified data",
    "blocked — account or email policy",
    "unavailable",
    "paid-only",
    "ineligible",
    "duplicate — no action",
    "terminated by user",
}

ALLOWED_VERIFICATION = {
    "not checked",
    "automatic verification passed",
    "awaiting manual verification",
    "manual verification completed",
    "verification unavailable before form",
    "verification expired/reset",
    "no verification presented",
    "deferred by user",
}

REQUIRED_CONTROLS = {
    "SPD version",
    "Campaign ID",
    "Product canonical ID",
    "Canonical URL",
    "Source-list reference",
    "Batch authorization reference",
    "Execution-shard size",
    "Maximum active tabs",
    "Credential policy",
    "Evidence policy",
    "Duplicate policy",
    "Ambiguous-outcome policy",
    "Ranking manipulation prohibited",
}

REQUIRED_SITE_FIELDS = {
    "Queue ID",
    "Website",
    "Platform domain",
    "Route",
    "Account alias",
    "Idempotency key",
    "Execution shard",
    "Legitimacy gate",
    "Authorization reference",
    "Status",
    "Content surface",
    "Content-surface evidence",
    "Verification preflight",
    "Duplicate check",
    "Duplicate evidence",
    "Direct-attempt authorization",
    "CDP retry decision",
    "CDP retry evidence",
    "Outcome-check attempts",
    "Handover page",
    "Fields entered",
    "Fields omitted",
    "Agreements/subscriptions",
    "Submit timestamp",
    "Exact result",
    "Evidence reference",
    "Last checked",
    "Follow-up",
}

ALLOWED_CONTENT_SURFACES = {
    "not applicable",
    "short note — no action",
    "long post — no action",
    "unknown — no action",
}
NO_ACTION_CONTENT_SURFACES = ALLOWED_CONTENT_SURFACES - {"not applicable"}

WEB_FORM_CHANNEL = "web form"
OFFICIAL_CONTACT_EMAIL_CHANNEL = "official contact email"
ALLOWED_ACTION_CHANNELS = {WEB_FORM_CHANNEL, OFFICIAL_CONTACT_EMAIL_CHANNEL}
EMAIL_SENT_STATUS = "email sent — awaiting reply"
EMAIL_UNKNOWN_STATUS = "email send outcome unknown"
EMAIL_STATUSES = {EMAIL_SENT_STATUS, EMAIL_UNKNOWN_STATUS}
EMAIL_ROUTE = "contact email backlink request"
ALLOWED_MAILBOX_PRE_SEND_CHECKS = {
    "cleared",
    "prior outreach found",
    "inconclusive — user-authorized direct attempt",
}
ALLOWED_GMAIL_SEND_RECEIPTS = {
    "not applicable",
    "gmail confirmed sent",
    "sent copy verified",
    "no clear receipt",
    "send failed",
}

TERMINAL_OR_PENDING = {
    "submitted",
    EMAIL_SENT_STATUS,
    EMAIL_UNKNOWN_STATUS,
    "submission outcome unknown",
    "awaiting approval",
    "awaiting email verification",
    "published",
}

EXECUTED = TERMINAL_OR_PENDING | {"form in progress", "draft saved"}
UNRESOLVED_VERIFICATION = {
    "awaiting manual verification",
    "verification expired/reset",
    "deferred by user",
}

ALLOWED_DUPLICATE_CHECKS = {
    "not checked",
    "cleared",
    "duplicate confirmed",
    "user-confirmed duplicate",
    "inconclusive",
    "not available — user-authorized direct attempt",
    "inconclusive — user-authorized direct attempt",
}

ALLOWED_CDP_RETRY_DECISIONS = {
    "not applicable",
    "no retry",
    "retry approved",
    "retry denied",
}

TRACKING_KEYS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "gclid", "fbclid", "msclkid", "ref", "referrer",
}
SENSITIVE_QUERY_KEYS = {
    "token", "key", "api_key", "apikey", "code", "state", "session",
    "auth", "password", "otp", "signature", "sig",
}


def clean(value: str) -> str:
    return re.sub(r"[*`]", "", value).strip()


def parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for match in re.finditer(r"^- ([^:\n]+):\s*(.*)$", body, re.MULTILINE):
        fields[clean(match.group(1))] = clean(match.group(2))
    return fields


def normalize_url(value: str) -> str:
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return value.strip()
    host = (parts.hostname or "").lower()
    if not host:
        return value.strip()
    port = f":{parts.port}" if parts.port else ""
    query = [
        (key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
        if key.lower() not in TRACKING_KEYS
    ]
    path = parts.path or "/"
    if path != "/":
        path = path.rstrip("/")
    return urlunsplit(((parts.scheme or "https").lower(), host + port, path, urlencode(query), ""))


def is_public_http_url(value: str) -> bool:
    """Return whether value is a non-credentialed HTTP(S) URL with a host."""
    try:
        parts = urlsplit(value.strip())
    except ValueError:
        return False
    return (
        parts.scheme.lower() in {"http", "https"}
        and bool(parts.hostname)
        and not parts.username
        and not parts.password
    )


def normalize_platform_domain(value: str) -> str:
    """Normalize a declared platform root enough to coalesce apex and www."""
    candidate = value.strip()
    if not candidate:
        return ""
    if "://" not in candidate:
        candidate = "//" + candidate
    try:
        host = (urlsplit(candidate).hostname or "").lower().rstrip(".")
    except ValueError:
        return ""
    return host.removeprefix("www.")


def parse_record(text: str) -> tuple[dict[str, str], list[dict[str, object]]]:
    controls_match = re.search(
        r"^## Campaign controls\s*$([\s\S]*?)(?=^## |\Z)", text, re.MULTILINE
    )
    controls = parse_fields(controls_match.group(1)) if controls_match else {}

    sites: list[dict[str, object]] = []
    headings = list(re.finditer(r"^## (?!Campaign controls$|Source list$)(.+)$", text, re.MULTILINE))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        body = text[heading.end():end]
        fields = parse_fields(body)
        sites.append({"name": heading.group(1).strip(), "fields": fields})
    return controls, sites


def audit(text: str) -> dict[str, object]:
    """Audit a public, shareable record that must not contain sensitive data."""
    errors: list[str] = []
    warnings: list[str] = []
    controls, sites = parse_record(text)

    missing_controls = sorted(REQUIRED_CONTROLS - controls.keys())
    if missing_controls:
        errors.append("missing campaign controls: " + ", ".join(missing_controls))
    if controls.get("SPD version") != "V1 Batch":
        errors.append("SPD version must be V1 Batch")
    if controls.get("Ranking manipulation prohibited", "").lower() != "yes":
        errors.append("Ranking manipulation prohibited must be yes")
    declared_scope = controls.get("Record scope", "shareable")
    if "Record scope" not in controls:
        warnings.append("Record scope missing; treating this legacy record as shareable")
    elif declared_scope != "shareable":
        errors.append("Record scope must be shareable")
    for numeric in ("Execution-shard size", "Maximum active tabs"):
        value = controls.get(numeric, "")
        if not value.isdigit() or int(value) < 1:
            errors.append(f"{numeric} must be a positive integer")

    if not re.search(r"^## Source list\s*$\n(?:\s*\n)*1\.\s+\S+", text, re.MULTILINE):
        errors.append("Source list must contain at least one URL")

    email_matches = sorted(set(re.findall(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", text, re.IGNORECASE)))
    if email_matches:
        errors.append("raw email address found; use a contact alias")
    secret_label = re.search(
        r"^-\s*(?:password|passcode|otp|recovery code|cookie|session id|oauth code|magic link)\s*:\s*(?!not applicable|none|redacted)\S+",
        text,
        re.IGNORECASE | re.MULTILINE,
    )
    if secret_label:
        errors.append("secret-bearing field found in shareable record")
    for url in re.findall(r"https?://[^\s)>]+", text):
        keys = {key.lower() for key, _ in parse_qsl(urlsplit(url).query, keep_blank_values=True)}
        if keys & SENSITIVE_QUERY_KEYS:
            errors.append("URL with sensitive authentication parameter found")
            break

    seen_keys: dict[str, str] = {}
    seen_queue_ids: dict[str, str] = {}
    seen_urls: dict[str, str] = {}
    seen_email_scopes: dict[str, str] = {}
    status_counts: Counter[str] = Counter()
    verification_counts: Counter[str] = Counter()
    manual_queue: list[str] = []

    for site in sites:
        name = str(site["name"])
        fields = site["fields"]
        assert isinstance(fields, dict)
        missing = sorted(REQUIRED_SITE_FIELDS - fields.keys())
        if missing:
            errors.append(f"{name}: missing fields: " + ", ".join(missing))

        status = fields.get("Status", "")
        content_surface = fields.get("Content surface", "")
        content_surface_evidence = fields.get("Content-surface evidence", "")
        verification = fields.get("Verification preflight", "")
        duplicate_check = fields.get("Duplicate check", "")
        duplicate_evidence = fields.get("Duplicate evidence", "").lower()
        cdp_retry_decision = fields.get("CDP retry decision", "").lower()
        cdp_retry_evidence = fields.get("CDP retry evidence", "").lower()
        outcome_check_attempts = fields.get("Outcome-check attempts", "")
        handover_page = fields.get("Handover page", "").lower()
        action_channel = fields.get("Action channel", WEB_FORM_CHANNEL).lower()
        recipient_alias = fields.get("Recipient contact alias", "not applicable").lower()
        contact_source_evidence = fields.get("Contact-source evidence", "not applicable").lower()
        mailbox_pre_send_check = fields.get("Mailbox pre-send check", "not applicable").lower()
        mailbox_pre_send_evidence = fields.get("Mailbox pre-send evidence", "not applicable").lower()
        email_send_attempts = fields.get("Email send attempts", "0")
        gmail_send_receipt = fields.get("Gmail send receipt", "not applicable").lower()
        status_counts[status or "missing"] += 1
        verification_counts[verification or "missing"] += 1
        if status not in ALLOWED_STATUSES:
            errors.append(f"{name}: invalid status: {status or 'missing'}")
        if action_channel not in ALLOWED_ACTION_CHANNELS:
            errors.append(f"{name}: invalid Action channel: {action_channel or 'missing'}")
        if content_surface not in ALLOWED_CONTENT_SURFACES:
            errors.append(f"{name}: invalid Content surface: {content_surface or 'missing'}")
        elif (
            content_surface != "not applicable"
            and content_surface_evidence.strip().lower()
            in {"", "not applicable", "none", "n/a"}
        ):
            errors.append(f"{name}: Content-surface evidence required for {content_surface}")
        elif status in EXECUTED and content_surface in NO_ACTION_CONTENT_SURFACES:
            errors.append(
                f"{name}: executed status '{status}' is incompatible with Content surface "
                f"'{content_surface}'"
            )
        if verification not in ALLOWED_VERIFICATION:
            errors.append(f"{name}: invalid verification state: {verification or 'missing'}")
        if duplicate_check not in ALLOWED_DUPLICATE_CHECKS:
            errors.append(f"{name}: invalid duplicate check: {duplicate_check or 'missing'}")
        if cdp_retry_decision not in ALLOWED_CDP_RETRY_DECISIONS:
            errors.append(f"{name}: invalid CDP retry decision: {cdp_retry_decision or 'missing'}")
        if cdp_retry_decision in {"retry approved", "retry denied"} and cdp_retry_evidence in {"", "not applicable", "none"}:
            errors.append(f"{name}: {cdp_retry_decision} requires CDP retry evidence")
        if not outcome_check_attempts.isdigit() or int(outcome_check_attempts) < 0 or int(outcome_check_attempts) > 3:
            errors.append(f"{name}: Outcome-check attempts must be an integer from 0 to 3")
        if verification in UNRESOLVED_VERIFICATION and content_surface not in NO_ACTION_CONTENT_SURFACES:
            manual_queue.append(name)
        if action_channel == OFFICIAL_CONTACT_EMAIL_CHANNEL:
            route = fields.get("Route", "").lower()
            sender_alias = fields.get("Account alias", "").lower()
            platform_root = normalize_platform_domain(fields.get("Platform domain", ""))
            website_host = normalize_platform_domain(fields.get("Website", ""))
            if route != EMAIL_ROUTE:
                errors.append(f"{name}: official contact email requires Route '{EMAIL_ROUTE}'")
            if content_surface != "not applicable":
                errors.append(f"{name}: official contact email requires Content surface not applicable")
            if sender_alias in {"", "not applicable", "none"}:
                errors.append(f"{name}: official contact email requires a Gmail sender alias")
            elif "@" in sender_alias:
                errors.append(f"{name}: Gmail sender alias must not contain a raw email address")
            if recipient_alias in {"", "not applicable", "none"}:
                errors.append(f"{name}: official contact email requires a Recipient contact alias")
            elif "@" in recipient_alias:
                errors.append(f"{name}: Recipient contact alias must not contain a raw email address")
            if contact_source_evidence in {"", "not applicable", "none"}:
                errors.append(f"{name}: official contact email requires Contact-source evidence")
            if mailbox_pre_send_check not in ALLOWED_MAILBOX_PRE_SEND_CHECKS:
                errors.append(f"{name}: invalid Mailbox pre-send check")
            if mailbox_pre_send_evidence in {"", "not applicable", "none"}:
                errors.append(f"{name}: official contact email requires Mailbox pre-send evidence")
            if not email_send_attempts.isdigit() or email_send_attempts not in {"0", "1"}:
                errors.append(f"{name}: Email send attempts must be 0 or 1")
            if gmail_send_receipt not in ALLOWED_GMAIL_SEND_RECEIPTS:
                errors.append(f"{name}: invalid Gmail send receipt")
            if not platform_root or "." not in platform_root:
                errors.append(f"{name}: official contact email requires a public platform root domain")
            elif not (
                website_host == platform_root
                or website_host.endswith("." + platform_root)
            ):
                errors.append(
                    f"{name}: official contact email Platform domain must match the Website host"
                )
            else:
                email_scope = "|".join(
                    (controls.get("Product canonical ID", "").lower(), platform_root, EMAIL_ROUTE)
                )
                if email_scope in seen_email_scopes:
                    errors.append(
                        f"{name}: duplicate official Contact email scope also used by "
                        f"{seen_email_scopes[email_scope]}"
                    )
                else:
                    seen_email_scopes[email_scope] = name

        queue_id = fields.get("Queue ID", "").strip()
        if not queue_id:
            errors.append(f"{name}: Queue ID must not be empty")
        elif queue_id in seen_queue_ids:
            errors.append(f"{name}: duplicate Queue ID also used by {seen_queue_ids[queue_id]}")
        else:
            seen_queue_ids[queue_id] = name

        idem = fields.get("Idempotency key", "")
        if idem:
            if idem in seen_keys:
                errors.append(f"{name}: duplicate idempotency key also used by {seen_keys[idem]}")
            else:
                seen_keys[idem] = name

        website = fields.get("Website", "")
        if not is_public_http_url(website):
            errors.append(f"{name}: Website must be an http(s) URL with a hostname and no embedded credentials")
        normalized = normalize_url(website) if website else ""
        if normalized:
            if normalized in seen_urls:
                errors.append(f"{name}: duplicate normalized website also used by {seen_urls[normalized]}")
            else:
                seen_urls[normalized] = name

        if status in EXECUTED and fields.get("Legitimacy gate") != "passed":
            errors.append(f"{name}: executed without a passed legitimacy gate")
        if status in EXECUTED and fields.get("Authorization reference", "") in {"", "not applicable", "none"}:
            errors.append(f"{name}: executed without an authorization reference")
        if status in EXECUTED and verification in UNRESOLVED_VERIFICATION:
            errors.append(f"{name}: executed while verification remained unresolved")
        direct_attempt_checks = {
            "not available — user-authorized direct attempt",
            "inconclusive — user-authorized direct attempt",
        }
        if status in EXECUTED and duplicate_check not in {"cleared", *direct_attempt_checks}:
            errors.append(f"{name}: executed without a cleared duplicate check")
        if status in EXECUTED and duplicate_evidence in {"", "not applicable", "none"}:
            errors.append(f"{name}: executed without duplicate-check evidence")
        if status in EXECUTED and duplicate_check in direct_attempt_checks:
            if fields.get("Direct-attempt authorization", "").lower() in {"", "not applicable", "none"}:
                errors.append(f"{name}: direct duplicate attempt requires an authorization reference")
        if status == "duplicate — no action":
            if action_channel == OFFICIAL_CONTACT_EMAIL_CHANNEL and mailbox_pre_send_check == "prior outreach found":
                if mailbox_pre_send_evidence in {"", "not applicable", "none"}:
                    errors.append(f"{name}: prior email outreach requires mailbox pre-send evidence")
            else:
                if duplicate_check not in {"duplicate confirmed", "user-confirmed duplicate"}:
                    errors.append(f"{name}: duplicate status requires confirmed duplicate evidence")
                if duplicate_evidence in {"", "not applicable", "none"}:
                    errors.append(f"{name}: duplicate status requires duplicate evidence")

        entered = fields.get("Fields entered", "").lower()
        agreements = fields.get("Agreements/subscriptions", "").lower()
        submitted_at = fields.get("Submit timestamp", "").lower()
        if content_surface in NO_ACTION_CONTENT_SURFACES:
            if status not in {"not attempted", "ineligible"}:
                errors.append(
                    f"{name}: no-action Content surface requires status not attempted or ineligible"
                )
            if entered not in {"", "none"}:
                errors.append(f"{name}: no-action Content surface must not have entered fields")
            if agreements not in {"", "none"}:
                errors.append(
                    f"{name}: no-action Content surface must not select agreements/subscriptions"
                )
            if submitted_at not in {"", "not submitted", "not applicable"}:
                errors.append(
                    f"{name}: no-action Content surface must not have a submit timestamp"
                )
            if handover_page not in {"", "not applicable", "none"}:
                errors.append(
                    f"{name}: no-action Content surface must not have a handover page"
                )
            if verification in UNRESOLVED_VERIFICATION:
                errors.append(
                    f"{name}: no-action Content surface must not have unresolved verification"
                )
            if outcome_check_attempts != "0":
                errors.append(
                    f"{name}: no-action Content surface must have zero outcome checks"
                )
            if fields.get("Exact result", "").lower() not in {
                "not attempted", "no action", "not applicable"
            }:
                errors.append(
                    f"{name}: no-action Content surface must not claim a final result"
                )
        if action_channel == OFFICIAL_CONTACT_EMAIL_CHANNEL:
            if mailbox_pre_send_check == "prior outreach found":
                if status != "duplicate — no action":
                    errors.append(f"{name}: prior email outreach requires duplicate — no action")
                if email_send_attempts != "0":
                    errors.append(f"{name}: prior email outreach must not send again")
            if status in {"not attempted", "form in progress", "draft saved", "duplicate — no action"}:
                if email_send_attempts != "0":
                    errors.append(f"{name}: unfinalized contact email must have zero sends")
            if status in EMAIL_STATUSES:
                if email_send_attempts != "1":
                    errors.append(f"{name}: {status} requires exactly one Gmail Send")
            if status == EMAIL_SENT_STATUS and gmail_send_receipt not in {
                "gmail confirmed sent", "sent copy verified"
            }:
                errors.append(f"{name}: email sent status requires a confirmed Gmail send receipt")
            if status == EMAIL_UNKNOWN_STATUS:
                if gmail_send_receipt != "no clear receipt":
                    errors.append(f"{name}: email send outcome unknown requires no clear receipt")
                if outcome_check_attempts not in {"2", "3"}:
                    errors.append(f"{name}: email send outcome unknown requires 2 or 3 Gmail checks")
                if handover_page in {"", "not applicable", "none"}:
                    errors.append(f"{name}: email send outcome unknown requires a retained Gmail page")
                if fields.get("Mailbox checked", "").lower() in {
                    "", "not applicable", "not checked"
                }:
                    errors.append(f"{name}: email send outcome unknown requires Gmail mailbox checks")
            if gmail_send_receipt in {"gmail confirmed sent", "sent copy verified"} and status != EMAIL_SENT_STATUS:
                errors.append(f"{name}: confirmed Gmail receipt requires email sent status")
            if gmail_send_receipt == "no clear receipt" and status != EMAIL_UNKNOWN_STATUS:
                errors.append(f"{name}: no clear Gmail receipt requires email send outcome unknown")
            if gmail_send_receipt == "send failed" and status not in {
                "blocked — account or email policy", "terminated by user"
            }:
                errors.append(f"{name}: send failed requires a blocked or terminated email state")
            if gmail_send_receipt == "send failed" and email_send_attempts != "1":
                errors.append(f"{name}: send failed requires exactly one Gmail Send")
            if status in {
                "submitted",
                "submission outcome unknown",
                "awaiting approval",
                "awaiting email verification",
                "published",
            }:
                errors.append(f"{name}: official contact email must use an email-specific outcome status")
        if action_channel == WEB_FORM_CHANNEL and status in EMAIL_STATUSES:
            errors.append(f"{name}: web form must not use an email-specific outcome status")
        if status == "not attempted":
            if entered not in {"", "none"}:
                errors.append(f"{name}: not attempted but listing fields were entered")
            if agreements not in {"", "none"}:
                errors.append(f"{name}: not attempted but agreements/subscriptions were selected")
            if submitted_at not in {"", "not submitted", "not applicable"}:
                errors.append(f"{name}: not attempted but has a submit timestamp")

        if status in TERMINAL_OR_PENDING:
            if submitted_at in {"", "not submitted", "not applicable"}:
                errors.append(f"{name}: {status} requires a submit timestamp")
            if fields.get("Exact result", "").lower() in {"", "not attempted", "unknown"}:
                errors.append(f"{name}: {status} requires an exact result")
            if fields.get("Evidence reference", "").lower() in {"", "not applicable", "none"}:
                errors.append(f"{name}: {status} requires an evidence reference")

        if status == "submission outcome unknown" and action_channel != OFFICIAL_CONTACT_EMAIL_CHANNEL:
            if outcome_check_attempts not in {"2", "3"}:
                errors.append(f"{name}: unknown outcome requires 2 or 3 read-only outcome checks")
            if handover_page in {"", "not applicable", "none"}:
                errors.append(f"{name}: unknown outcome requires a retained Handover page")
            for check in ("Backend checked", "Mailbox checked", "Public page checked"):
                if fields.get(check, "").lower() in {"", "not applicable", "not checked"}:
                    errors.append(f"{name}: unknown outcome requires {check}")

        if status == "blocked — manual verification":
            if handover_page in {"", "not applicable", "none"}:
                errors.append(f"{name}: manual verification requires a retained Handover page")
            if entered in {"", "none"}:
                errors.append(f"{name}: manual verification requires a populated form before handover")

        if status == "published" and fields.get("Public listing URL", "").lower() in {"", "not applicable", "none"}:
            errors.append(f"{name}: published requires a public listing URL")

    if not sites:
        errors.append("record contains no website sections")

    return {
        "valid": not errors,
        "errors": errors,
        "warnings": warnings,
        "record_scope": "shareable",
        "total_sites": len(sites),
        "status_counts": dict(sorted(status_counts.items())),
        "verification_counts": dict(sorted(verification_counts.items())),
        "manual_verification_queue": manual_queue,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("record", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = audit(args.record.read_text(encoding="utf-8"))
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Valid: {result['valid']}")
        print(f"Total sites: {result['total_sites']}")
        for key, count in result["status_counts"].items():
            print(f"{key}: {count}")
        if result["manual_verification_queue"]:
            print("Manual verification queue: " + ", ".join(result["manual_verification_queue"]))
        for warning in result["warnings"]:
            print("WARNING: " + warning)
        for error in result["errors"]:
            print("ERROR: " + error)
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
