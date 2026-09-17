#!/usr/bin/env python3
"""Initialize and structurally validate a portable, non-publishing Blog 3P campaign."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlparse

PHASES = {"draft", "prewrite_planning", "awaiting_owner_prewrite_confirmation", "research", "write", "review", "repair", "gate", "human_release_ready", "human_publishing", "human_accepted", "public_readonly_validating", "completed", "deferred", "blocked", "capacity_blocked"}
PRIORITY = ["CURRENT_BRAND_SITE", "REGIONAL_SERP", "MODEL_TRANSLATION_FALLBACK"]
VISUAL_ZONES = ["LEAD", "MIDDLE", "CLOSING"]
OWNER_SOURCE_TYPES = {"OWNER_XLSX", "OWNER_TABLE", "OWNER_MESSAGE"}
MATCHING_ROLE = "CAMPAIGN_PLATFORM_MATCHING_RESEARCHER"
LEGACY_PREWRITE_PLAN_SECTIONS = ["task_and_audience", "research_evidence_and_uncertainty", "keyword_and_localization_strategy", "factual_claims_and_sources", "title_and_outline", "visual_narrative", "platform_transport_assumptions", "risks_and_owner_decisions"]
PREWRITE_PLAN_SECTIONS = ["task_and_audience", "reader_value_and_secondary_cta", "research_evidence_and_uncertainty", "keyword_and_localization_strategy", "factual_claims_and_sources", "title_and_outline", "visual_narrative", "platform_transport_assumptions", "risks_and_owner_decisions"]
LEGACY_PREWRITE_SUMMARY_SECTIONS = ["owner_task_and_scope", "sources_checked_and_uncertainty", "shared_constraints", "platform_matching_status"]
PREWRITE_SUMMARY_SECTIONS = ["owner_task_and_scope", "content_value_and_cta_policy", "sources_checked_and_uncertainty", "shared_constraints", "platform_matching_status"]
PREWRITE_STATUSES = {"PENDING_OWNER_PREWRITE_PLAN_CONFIRMATION", "OWNER_PREWRITE_PLAN_CONFIRMED", "OWNER_PREWRITE_PLAN_CHANGES_REQUESTED"}
ARTICLE_EXECUTION_ROLES = {"ARTICLE_LANE_GATEKEEPER", "ARTICLE_WRITER", "ARTICLE_LANGUAGE_REVIEWER"}
CTA_RECOMMENDATION_FIELDS = ("product_name", "product_destination_url", "product_evidence_path", "reader_task_relevance", "relationship_disclosure")
REQUIRED_CTA_RECOMMENDATION_FIELDS = ("anchor_text", *CTA_RECOMMENDATION_FIELDS)
HUMAN_RETURN_STATES = {"HUMAN_ACCEPTED", "HUMAN_NEEDS_FIX"}
ARTICLE_CONTEXT_SCHEMA = "1.0"
REVIEW_INDEX_SCHEMA = "1.0"
REVIEW_DELTA_SCHEMA = "1.0"
RESEARCH_REVIEW_STATUSES = {"PENDING", "RESEARCH_APPROVED", "RESEARCH_CHANGES_REQUIRED"}
FULL_REVIEW_STATUSES = {"PENDING", "APPROVED", "CHANGES_REQUIRED"}
FINAL_VISUAL_DELTA_RESULT = "APPROVED"
FINAL_VISUAL_DELTA_FIELDS = (
    "report_sha256", "reviewer_agent_id", "review_index_sha256",
    "reviewed_visual_manifest_sha256", "reviewed_visual_payload_sha256",
)
DELTA_CHANGE_KINDS = {
    "CANONICAL_TEXT",
    "METADATA_OR_CTA",
    "RESEARCH_EVIDENCE",
    "VISUAL_ASSET",
    "VISUAL_MANIFEST",
    "VISUAL_PAYLOAD",
    "REQUIREMENTS_OR_SCOPE",
}
DELTA_REVIEW_SCOPES = {"R_DELTA", "R_VISUAL_DELTA"}
PUBLIC_QA_OUTCOMES = {
    "PUBLIC_QA_PASSED",
    "PUBLIC_QA_PASSED_WITH_LIMITATION",
    "HUMAN_TRANSPORT_FIX_REQUIRED",
    "PUBLIC_QA_UNVERIFIED",
    "CANONICAL_CHANGE_REQUESTED",
}
PUBLIC_QA_RECORD_STATUSES = {"NOT_STARTED", *HUMAN_RETURN_STATES, "PUBLIC_READONLY_VALIDATING", *PUBLIC_QA_OUTCOMES}
LIMITATION_SCOPE_FIELDS = ("platform", "account_or_site", "editor_or_theme", "locale_or_market", "observed_at")
PUBLIC_QA_POLICY_2_3 = {
    "mode": "REUSE_ARTICLE_LANE_GATEKEEPER_READONLY",
    "requires_human_acceptance": True,
    "human_return_receipt": "STRUCTURED_REQUIRED",
    "public_snapshot": "NORMALIZED_READONLY_REQUIRED",
    "fresh_public_reviewer": "PROHIBITED",
    "automatic_wr_reopen": False,
    "human_transport_fix_recheck": "SAME_LANE_G_ONLY",
    "canonical_change_reopen": "OWNER_EXPLICIT_REQUEST_ID_REQUIRED",
    "accepted_platform_limitation": "EVIDENCE_SCOPED_NOT_GENERALIZABLE",
    "unverified_retry_budget": 1,
    "on_mismatch": "CLASSIFY_BEFORE_OWNER_DECISION",
    "outcomes": [
        "PUBLIC_QA_PASSED",
        "PUBLIC_QA_PASSED_WITH_LIMITATION",
        "HUMAN_TRANSPORT_FIX_REQUIRED",
        "PUBLIC_QA_UNVERIFIED",
        "CANONICAL_CHANGE_REQUESTED",
    ],
}
ARTIFACT_OPTIMIZATION_POLICY_2_4 = {
    "mode": "CANONICAL_MANIFESTS_AND_DELTA_CONTEXT",
    "prewrite_manifest_schema": "1.3",
    "prewrite_manifest_canonical_source": True,
    "prewrite_owner_view": "HARNESS_DETERMINISTIC_RENDER_ONLY",
    "manual_duplicate_entry": "PROHIBITED",
    "article_context": {"path": "context/article-contract.json", "schema_version": ARTICLE_CONTEXT_SCHEMA},
    "review_index": {"path": "reviews/review-index.json", "schema_version": REVIEW_INDEX_SCHEMA},
    "review_delta": {"schema_version": REVIEW_DELTA_SCHEMA, "max_delta_attempts_before_full_review": 2},
    "research_evidence_pack": {"path": "research/evidence-pack.json", "canonical": True},
    "shared_evidence_pack": {"path": "evidence/shared/campaign-evidence-pack.json", "canonical": True},
    "visual_manifest": {"path": "canonical/visual-manifest.json", "canonical": True},
    "handoff_manifest": {"path": "handoff/handoff-manifest.json", "canonical": True},
    "payload_semantic_auditor": "ARTICLE_LANGUAGE_REVIEWER",
    "gate_payload_acceptance": "MANIFEST_HASH_AND_REQUIREMENTS_ONLY",
}


def parse_schema_version(value: object) -> tuple[int, int] | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"(\d+)\.(\d+)", value)
    return (int(match.group(1)), int(match.group(2))) if match else None


def schema_at_least(value: object, major: int, minor: int) -> bool:
    parsed = parse_schema_version(value)
    return parsed is not None and parsed >= (major, minor)


def non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def content_value_policy_errors(policy: object, *, required_cta: bool = False) -> list[str]:
    if not isinstance(policy, dict):
        return ["content value policy must be an object"]
    expected = {
        "mode": "READER_VALUE_FIRST",
        "primary_purpose": "STANDALONE_ANSWER_TO_READER_TASK",
        "cta_role": "REQUIRED_SECONDARY_TRANSPARENT_RECOMMENDATION" if required_cta else "OPTIONAL_SECONDARY_TRANSPARENT_RECOMMENDATION",
        "cta_requires_identifiable_product_and_claim_basis": True,
        "cta_requires_relationship_disclosure_when_applicable": True,
        "cta_must_not_replace_or_dominate_reader_value": True,
    }
    if required_cta:
        expected["cta_must_be_present"] = True
    return [f"content value policy requires {key}={value!r}" for key, value in expected.items() if policy.get(key) != value]


def content_value_article_errors(article: object, *, required_cta: bool = False) -> list[str]:
    if not isinstance(article, dict):
        return ["content value declaration requires an article object"]
    article_id = str(article.get("article_id", "")).strip() or "<unknown>"
    errors: list[str] = []
    if not non_empty_string(article.get("reader_value_promise")):
        errors.append(f"article {article_id}: reader_value_promise is required")
    cta = article.get("cta")
    if not isinstance(cta, dict):
        return errors + [f"article {article_id}: cta must be an object"]
    mode = cta.get("mode")
    if required_cta:
        if mode != "SECONDARY_RECOMMENDATION":
            errors.append(f"article {article_id}: cta.mode must be SECONDARY_RECOMMENDATION in schema 2.2+")
        for field in REQUIRED_CTA_RECOMMENDATION_FIELDS:
            if not non_empty_string(cta.get(field)):
                errors.append(f"article {article_id}: required secondary CTA requires {field}")
    elif mode == "NONE":
        if any(cta.get(field) is not None and cta.get(field) != "" for field in CTA_RECOMMENDATION_FIELDS):
            errors.append(f"article {article_id}: CTA NONE may not carry recommendation fields")
    elif mode == "SECONDARY_RECOMMENDATION":
        for field in CTA_RECOMMENDATION_FIELDS:
            if not non_empty_string(cta.get(field)):
                errors.append(f"article {article_id}: secondary CTA requires {field}")
    else:
        errors.append(f"article {article_id}: cta.mode must be NONE or SECONDARY_RECOMMENDATION")
    return errors


def normalized_cta_declaration(value: object) -> object:
    if not isinstance(value, dict) or value.get("mode") != "NONE":
        return value
    return {key: item for key, item in value.items() if key not in CTA_RECOMMENDATION_FIELDS}


def article_package_declaration_errors(campaign_article: object, package: object, *, required_cta: bool = False, package_schema: str | None = None) -> list[str]:
    if not isinstance(campaign_article, dict):
        return ["campaign article declaration must be an object"]
    if not isinstance(package, dict):
        return ["article package must be an object"]
    article_id = str(campaign_article.get("article_id", "")).strip() or "<unknown>"
    errors = content_value_article_errors(package, required_cta=required_cta)
    expected_package_schema = package_schema or ("1.2" if required_cta else "1.1")
    if package.get("schema_version") != expected_package_schema:
        errors.append(f"article {article_id}: article package schema_version must be {expected_package_schema}")
    if str(package.get("article_id", "")).strip() != article_id:
        errors.append(f"article {article_id}: article package article_id does not match")
    if package.get("reader_value_promise") != campaign_article.get("reader_value_promise"):
        errors.append(f"article {article_id}: article package reader_value_promise does not match frozen campaign declaration")
    package_cta = package.get("cta") if required_cta else normalized_cta_declaration(package.get("cta"))
    campaign_cta = campaign_article.get("cta") if required_cta else normalized_cta_declaration(campaign_article.get("cta"))
    if package_cta != campaign_cta:
        errors.append(f"article {article_id}: article package cta does not match frozen campaign declaration")
    return errors


def package_artifact_source_errors(package: object) -> list[str]:
    """Validate the compact source chain without scoring editorial content."""
    if not isinstance(package, dict):
        return ["article package must be an object"]
    sources = package.get("artifact_sources")
    expected = {
        "evidence_pack": ("research/evidence-pack.json", "ARTICLE_CLAIM_AND_SEO_DECISION_INDEX"),
        "visual_manifest": ("canonical/visual-manifest.json", "SINGLE_SOURCE_FOR_IMAGE_ASSETS_ALT_CAPTIONS_AND_PLACEMENT"),
        "handoff_manifest": ("handoff/handoff-manifest.json", "DERIVED_HANDOFF_ARTIFACT_AND_HASH_INDEX"),
    }
    errors: list[str] = []
    if not isinstance(sources, dict):
        return ["article package schema 1.3 requires artifact_sources"]
    if sources.get("manual_retelling") != "PROHIBITED":
        errors.append("article package artifact_sources must prohibit manual retelling")
    for key, (path, role) in expected.items():
        source = sources.get(key)
        if not isinstance(source, dict):
            errors.append(f"article package artifact_sources requires {key}")
            continue
        if source.get("path") != path:
            errors.append(f"article package {key} path is invalid")
        if source.get("role") != role:
            errors.append(f"article package {key} role is invalid")
        if not non_empty_string(source.get("sha256")):
            errors.append(f"article package {key} requires sha256 or a lifecycle placeholder")
    errors.extend(final_visual_payload_delta_errors(package.get("final_visual_payload_delta")))
    return errors


def final_visual_payload_delta_errors(
    delta: object, *, require_approved: bool = False, workspace: Path | None = None,
    expected_visual_manifest_sha256: str | None = None,
    expected_visual_payload_sha256: str | None = None,
    expected_review_index_sha256: str | None = None,
) -> list[str]:
    """Check the compact R visual-delta receipt without re-scoring payload semantics."""
    if not isinstance(delta, dict):
        return ["article package schema 1.3 requires final_visual_payload_delta"]
    errors: list[str] = []
    if delta.get("precondition") != "TEXT_AND_SEO_FIELDS_STABLE" or delta.get("scope") != "VISUAL_MANIFEST_ASSETS_AND_COMPILED_PAYLOAD_ONLY":
        errors.append("article package final visual payload delta boundary is invalid")
    result = delta.get("reviewer_result")
    if result not in {"PENDING", FINAL_VISUAL_DELTA_RESULT}:
        errors.append("article package final visual payload delta must be PENDING or APPROVED")
    if not non_empty_string(delta.get("report_path")):
        errors.append("article package final visual payload delta requires report_path")
    if result == "PENDING" and any(delta.get(field) not in {None, ""} for field in FINAL_VISUAL_DELTA_FIELDS):
        errors.append("pending final visual payload delta may not carry approval bindings")
    if not require_approved:
        return errors
    if result != FINAL_VISUAL_DELTA_RESULT:
        errors.append("handoff requires an APPROVED final visual payload delta")
    for field in FINAL_VISUAL_DELTA_FIELDS:
        if not non_empty_string(delta.get(field)):
            errors.append(f"approved final visual payload delta requires {field}")
    if workspace is not None and non_empty_string(delta.get("report_path")):
        report, report_error = workspace_file(workspace, delta.get("report_path"), label="final visual payload delta report")
        if report_error:
            errors.append(report_error)
        elif report is not None and delta.get("report_sha256") != sha256_file(report):
            errors.append("final visual payload delta report_sha256 does not match")
    if expected_visual_manifest_sha256 is not None and delta.get("reviewed_visual_manifest_sha256") != expected_visual_manifest_sha256:
        errors.append("final visual payload delta visual manifest hash does not match")
    if expected_visual_payload_sha256 is not None and delta.get("reviewed_visual_payload_sha256") != expected_visual_payload_sha256:
        errors.append("final visual payload delta visual payload hash does not match")
    if expected_review_index_sha256 is not None and delta.get("review_index_sha256") != expected_review_index_sha256:
        errors.append("final visual payload delta review index hash does not match")
    return errors


def is_http_url(value: object) -> bool:
    if not non_empty_string(value):
        return False
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and parsed.username is None and parsed.password is None


def parse_timestamp(value: object) -> datetime | None:
    """Accept only timezone-aware ISO-8601 timestamps for auditable public-QA turns."""
    if not non_empty_string(value):
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def workspace_file(workspace: Path, value: object, *, label: str) -> tuple[Path | None, str | None]:
    """Resolve a campaign-local evidence file without permitting traversal outside the workspace."""
    if not non_empty_string(value):
        return None, f"{label} requires a non-empty relative path"
    candidate = Path(value.strip())
    if candidate.is_absolute():
        return None, f"{label} must stay relative to the campaign workspace"
    root = workspace.resolve()
    resolved = (workspace / candidate).resolve()
    if resolved == root or root not in resolved.parents:
        return None, f"{label} is outside the campaign workspace"
    if not resolved.is_file():
        return None, f"{label} does not exist"
    return resolved, None


def json_object_file(path: Path, *, label: str) -> tuple[dict | None, str | None]:
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{label} must be valid JSON: {exc}"
    if not isinstance(parsed, dict):
        return None, f"{label} must contain a JSON object"
    return parsed, None


def normalized_snapshot_sha256(snapshot: dict) -> str:
    payload = dict(snapshot)
    payload.pop("snapshot_sha256", None)
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def public_qa_policy_errors(policy: object) -> list[str]:
    if not isinstance(policy, dict):
        return ["public QA policy must be an object"]
    return [
        f"public QA policy requires {key}={value!r}"
        for key, value in PUBLIC_QA_POLICY_2_3.items()
        if policy.get(key) != value
    ]


def platform_limitation_errors(limitation: object, *, prefix: str) -> list[str]:
    if not isinstance(limitation, dict):
        return [f"{prefix}: platform limitation must be an object"]
    errors: list[str] = []
    for field in ("id", "observed_behavior"):
        if not non_empty_string(limitation.get(field)):
            errors.append(f"{prefix}: platform limitation requires {field}")
    scope = limitation.get("scope")
    if not isinstance(scope, dict):
        errors.append(f"{prefix}: platform limitation requires a scoped observation")
    else:
        for field in LIMITATION_SCOPE_FIELDS:
            if not non_empty_string(scope.get(field)):
                errors.append(f"{prefix}: platform limitation scope requires {field}")
    evidence_paths = limitation.get("evidence_paths")
    if not isinstance(evidence_paths, list) or not evidence_paths or any(not non_empty_string(path) for path in evidence_paths):
        errors.append(f"{prefix}: platform limitation requires non-empty evidence_paths")
    affected = limitation.get("affected_contract_items")
    if not isinstance(affected, list) or not affected or any(not non_empty_string(item) for item in affected):
        errors.append(f"{prefix}: platform limitation requires affected_contract_items")
    if not non_empty_string(limitation.get("owner_acceptance")):
        errors.append(f"{prefix}: platform limitation requires owner_acceptance")
    if limitation.get("not_generalizable") is not True:
        errors.append(f"{prefix}: platform limitation must set not_generalizable=true")
    return errors


def public_return_receipt_errors(receipt: object, *, expected_article_id: object = None) -> list[str]:
    if not isinstance(receipt, dict):
        return ["public return receipt must be an object"]
    errors: list[str] = []
    if receipt.get("schema_version") != "1.0":
        errors.append("public return receipt schema_version must be 1.0")
    article_id = str(receipt.get("article_id", "")).strip()
    if not article_id:
        errors.append("public return receipt requires article_id")
    elif expected_article_id is not None and article_id != expected_article_id:
        errors.append("public return receipt article_id does not match article package")
    if not is_http_url(receipt.get("public_url")):
        errors.append("public return receipt requires an http(s) public_url")
    if receipt.get("human_state") not in HUMAN_RETURN_STATES:
        errors.append("public return receipt human_state must be HUMAN_ACCEPTED or HUMAN_NEEDS_FIX")
    if parse_timestamp(receipt.get("returned_at")) is None:
        errors.append("public return receipt requires a timezone-aware ISO-8601 returned_at")
    if not non_empty_string(receipt.get("published_at_or_revision")):
        errors.append("public return receipt requires published_at_or_revision or UNVERIFIED")
    visual_paths = receipt.get("public_visual_evidence_paths")
    if not isinstance(visual_paths, list) or any(not non_empty_string(path) for path in visual_paths):
        errors.append("public return receipt public_visual_evidence_paths must be a list of paths")
    limitations = receipt.get("known_platform_limitations")
    if not isinstance(limitations, list):
        errors.append("public return receipt known_platform_limitations must be a list")
    else:
        for index, limitation in enumerate(limitations, 1):
            errors.extend(platform_limitation_errors(limitation, prefix=f"public return receipt limitation #{index}"))
    return errors


def publication_ledger_errors(
    publication: object, *, article_ids: set[str], article_workspaces: object, workspace: Path | None = None,
) -> list[str]:
    if not isinstance(publication, dict):
        return ["state publication must be an object"]
    if not non_empty_string(publication.get("status")):
        return ["state publication requires a status"]
    records = publication.get("articles")
    if not isinstance(records, dict):
        return ["state publication articles must be an object"]
    errors: list[str] = []
    workspace_records = article_workspaces if isinstance(article_workspaces, dict) else {}
    for article_id, record in records.items():
        prefix = f"state publication article {article_id}"
        if article_id not in article_ids:
            errors.append(f"{prefix}: unknown article_id")
        if not isinstance(record, dict):
            errors.append(f"{prefix}: record must be an object")
            continue
        required_fields = {
            "public_url", "human_state", "returned_at", "return_receipt_path", "public_snapshot_path",
            "lane_gatekeeper_agent_id", "attempt", "unverified_retry_count", "public_qa_status", "last_report_path",
            "owner_request_id", "accepted_platform_limitations",
        }
        missing = sorted(required_fields - set(record))
        if missing:
            errors.append(f"{prefix}: missing fields " + ", ".join(missing))
            continue
        human_state = record.get("human_state")
        if human_state is not None and human_state not in HUMAN_RETURN_STATES:
            errors.append(f"{prefix}: human_state is invalid")
        if human_state is not None and parse_timestamp(record.get("returned_at")) is None:
            errors.append(f"{prefix}: active public state requires a timezone-aware ISO-8601 returned_at")
        qa_status = record.get("public_qa_status")
        if qa_status not in PUBLIC_QA_RECORD_STATUSES:
            errors.append(f"{prefix}: public_qa_status is invalid")
        if isinstance(record.get("attempt"), bool) or not isinstance(record.get("attempt"), int) or record["attempt"] < 0:
            errors.append(f"{prefix}: attempt must be a non-negative integer")
        retry_count = record.get("unverified_retry_count")
        retry_budget = PUBLIC_QA_POLICY_2_3["unverified_retry_budget"]
        if isinstance(retry_count, bool) or not isinstance(retry_count, int) or retry_count < 0:
            errors.append(f"{prefix}: unverified_retry_count must be a non-negative integer")
        elif retry_count > retry_budget:
            errors.append(f"{prefix}: unverified_retry_count exceeds the configured retry budget")
        limitations = record.get("accepted_platform_limitations")
        if not isinstance(limitations, list):
            errors.append(f"{prefix}: accepted_platform_limitations must be a list")
        else:
            for index, limitation in enumerate(limitations, 1):
                errors.extend(platform_limitation_errors(limitation, prefix=f"{prefix} limitation #{index}"))
        public_stage = qa_status in {"PUBLIC_READONLY_VALIDATING", *PUBLIC_QA_OUTCOMES}
        if human_state is not None or qa_status != "NOT_STARTED":
            if not is_http_url(record.get("public_url")):
                errors.append(f"{prefix}: an active public state requires an http(s) public_url")
            if not non_empty_string(record.get("return_receipt_path")):
                errors.append(f"{prefix}: an active public state requires return_receipt_path")
        if public_stage:
            if human_state != "HUMAN_ACCEPTED":
                errors.append(f"{prefix}: public QA requires HUMAN_ACCEPTED")
            if not non_empty_string(record.get("lane_gatekeeper_agent_id")):
                errors.append(f"{prefix}: public QA requires the existing lane_gatekeeper_agent_id")
            if record.get("attempt", 0) < 1:
                errors.append(f"{prefix}: public QA requires attempt >= 1")
            article_workspace = workspace_records.get(article_id)
            if not isinstance(article_workspace, dict):
                errors.append(f"{prefix}: public QA requires the registered article workspace")
                bundle = None
            else:
                bundle = article_workspace.get("role_bundle")
            if not isinstance(bundle, dict):
                errors.append(f"{prefix}: public QA requires the registered lane role bundle")
            registered_lane_id = bundle.get("lane_gatekeeper_agent") if isinstance(bundle, dict) else None
            if not non_empty_string(registered_lane_id):
                errors.append(f"{prefix}: public QA requires a registered lane gatekeeper agent ID")
            elif record.get("lane_gatekeeper_agent_id") != registered_lane_id:
                errors.append(f"{prefix}: public QA must reuse the registered lane gatekeeper")
        if qa_status in PUBLIC_QA_OUTCOMES:
            if not non_empty_string(record.get("public_snapshot_path")):
                errors.append(f"{prefix}: completed public QA classification requires public_snapshot_path")
            if not non_empty_string(record.get("last_report_path")):
                errors.append(f"{prefix}: completed public QA classification requires last_report_path")
        if qa_status == "PUBLIC_QA_PASSED_WITH_LIMITATION" and not limitations:
            errors.append(f"{prefix}: PASS_WITH_LIMITATION requires an evidence-scoped limitation")
        if qa_status == "CANONICAL_CHANGE_REQUESTED" and not non_empty_string(record.get("owner_request_id")):
            errors.append(f"{prefix}: CANONICAL_CHANGE_REQUESTED requires owner_request_id")
        if workspace is not None and (human_state is not None or qa_status != "NOT_STARTED"):
            errors.extend(publication_artifact_errors(record, article_id=article_id, workspace=workspace, prefix=prefix))
    return errors


def publication_artifact_errors(record: dict, *, article_id: str, workspace: Path, prefix: str) -> list[str]:
    """Bind an active public-QA ledger row to real, campaign-local evidence files."""
    errors: list[str] = []
    receipt_path, receipt_path_error = workspace_file(
        workspace, record.get("return_receipt_path"), label=f"{prefix} return_receipt_path",
    )
    if receipt_path_error:
        errors.append(receipt_path_error)
    elif receipt_path is not None:
        receipt, receipt_error = json_object_file(receipt_path, label=f"{prefix} return receipt")
        if receipt_error:
            errors.append(receipt_error)
        elif receipt is not None:
            errors.extend(f"{prefix}: {error}" for error in public_return_receipt_errors(receipt, expected_article_id=article_id))
            if receipt.get("public_url") != record.get("public_url"):
                errors.append(f"{prefix}: receipt public_url does not match the ledger")
            if receipt.get("human_state") != record.get("human_state"):
                errors.append(f"{prefix}: receipt human_state does not match the ledger")
            receipt_returned_at = parse_timestamp(receipt.get("returned_at"))
            ledger_returned_at = parse_timestamp(record.get("returned_at"))
            if receipt_returned_at is None or ledger_returned_at is None or receipt_returned_at != ledger_returned_at:
                errors.append(f"{prefix}: receipt returned_at does not match the ledger")

    qa_status = record.get("public_qa_status")
    snapshot_required = qa_status in {"PUBLIC_READONLY_VALIDATING", *PUBLIC_QA_OUTCOMES}
    report_required = qa_status in PUBLIC_QA_OUTCOMES
    if not snapshot_required:
        return errors

    snapshot_path, snapshot_path_error = workspace_file(
        workspace, record.get("public_snapshot_path"), label=f"{prefix} public_snapshot_path",
    )
    if snapshot_path_error:
        errors.append(snapshot_path_error)
    elif snapshot_path is not None:
        snapshot, snapshot_error = json_object_file(snapshot_path, label=f"{prefix} public snapshot")
        if snapshot_error:
            errors.append(snapshot_error)
        elif snapshot is not None:
            if snapshot.get("snapshot_sha256") != normalized_snapshot_sha256(snapshot):
                errors.append(f"{prefix}: public snapshot hash does not match")
            expected_contract = snapshot.get("expected_contract")
            if not isinstance(expected_contract, dict) or expected_contract.get("article_id") != article_id:
                errors.append(f"{prefix}: public snapshot article_id does not match the ledger")
            source = snapshot.get("source")
            if not isinstance(source, dict) or source.get("requested_url") != record.get("public_url"):
                errors.append(f"{prefix}: public snapshot URL does not match the ledger")
            if snapshot.get("capture_status") not in {"CAPTURED", "UNVERIFIED"}:
                errors.append(f"{prefix}: public snapshot has an invalid capture_status")

    if report_required:
        report_path, report_path_error = workspace_file(
            workspace, record.get("last_report_path"), label=f"{prefix} last_report_path",
        )
        if report_path_error:
            errors.append(report_path_error)
        elif report_path is not None:
            try:
                report_text = report_path.read_text(encoding="utf-8")
            except OSError as exc:
                errors.append(f"{prefix}: cannot read public QA report: {exc}")
            else:
                required_report_literals = (
                    f"Public QA report — {article_id}",
                    f"Existing lane G agent ID: `{record.get('lane_gatekeeper_agent_id')}`",
                    f"Public URL: `{record.get('public_url')}`",
                    f"Human return receipt: `{record.get('return_receipt_path')}`",
                    f"Normalized public snapshot: `{record.get('public_snapshot_path')}`",
                    f"Selected result: `{qa_status}`",
                )
                for literal in required_report_literals:
                    if literal not in report_text:
                        errors.append(f"{prefix}: public QA report does not bind {literal!r}")
                if (
                    qa_status == "CANONICAL_CHANGE_REQUESTED"
                    and f"Owner request ID: `{record.get('owner_request_id')}`" not in report_text
                ):
                    errors.append(f"{prefix}: canonical-change report does not bind owner_request_id")
    return errors


def public_qa_task_errors(publication: object, *, tasks: object, article_workspaces: object) -> list[str]:
    """Prove post-return work stayed in the pre-existing lane and never silently restarted W/R."""
    if not isinstance(publication, dict) or not isinstance(publication.get("articles"), dict):
        return []
    if not isinstance(tasks, list):
        return ["public QA requires a visible task ledger"]
    workspace_records = article_workspaces if isinstance(article_workspaces, dict) else {}
    errors: list[str] = []
    for article_id, record in publication["articles"].items():
        if not isinstance(record, dict):
            continue
        human_state = record.get("human_state")
        qa_status = record.get("public_qa_status")
        if human_state is None and qa_status == "NOT_STARTED":
            continue
        prefix = f"state publication article {article_id}"
        returned_at = parse_timestamp(record.get("returned_at"))
        if returned_at is None:
            continue
        workspace = workspace_records.get(article_id)
        bundle = workspace.get("role_bundle") if isinstance(workspace, dict) else None
        if not isinstance(bundle, dict):
            continue
        expected_agent_by_role = {
            "ARTICLE_LANE_GATEKEEPER": bundle.get("lane_gatekeeper_agent"),
            "ARTICLE_WRITER": bundle.get("writer_agent"),
            "ARTICLE_LANGUAGE_REVIEWER": bundle.get("reviewer_agent"),
        }
        article_tasks = [
            task for task in tasks
            if isinstance(task, dict) and task.get("article_id") == article_id and task.get("role") in ARTICLE_EXECUTION_ROLES
        ]
        for task in article_tasks:
            role = task.get("role")
            expected_agent_id = expected_agent_by_role.get(role)
            if not non_empty_string(task.get("agent_id")) or task.get("agent_id") != expected_agent_id:
                errors.append(f"{prefix}: article task {role} must reuse its registered agent ID")
            task_started_at = parse_timestamp(task.get("started_at"))
            if task_started_at is None:
                errors.append(f"{prefix}: article task {role} requires a timezone-aware ISO-8601 started_at")
                continue
            if task_started_at >= returned_at and role in {"ARTICLE_WRITER", "ARTICLE_LANGUAGE_REVIEWER"}:
                if (
                    qa_status != "CANONICAL_CHANGE_REQUESTED"
                    or task.get("workflow_stage") != "CANONICAL_REOPEN"
                    or task.get("owner_request_id") != record.get("owner_request_id")
                ):
                    errors.append(f"{prefix}: post-return W/R is forbidden without the matching canonical-change owner request")

        completed_classification = qa_status in PUBLIC_QA_OUTCOMES
        if not completed_classification:
            continue
        lane_agent_id = record.get("lane_gatekeeper_agent_id")
        public_g_turns = [
            task for task in article_tasks
            if task.get("role") == "ARTICLE_LANE_GATEKEEPER"
            and task.get("agent_id") == lane_agent_id
            and task.get("workflow_stage") == "PUBLIC_QA_READONLY"
            and task.get("result_path") == record.get("last_report_path")
            and (parse_timestamp(task.get("started_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= returned_at
        ]
        if not public_g_turns:
            errors.append(f"{prefix}: public QA requires a timestamped read-only turn by the registered lane gatekeeper")
    return errors


def dump(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_json(value: object) -> str:
    """Hash structured provenance without depending on incidental JSON whitespace."""
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def relative_path(workspace: Path, path: Path) -> str:
    """Return a workspace-relative path and reject accidental external references."""
    root = workspace.resolve()
    resolved = path.resolve()
    if resolved == root or root not in resolved.parents:
        raise ValueError(f"path must stay inside workspace: {path}")
    return str(resolved.relative_to(root))


def manifest_text(value: object, *, pending: str = "PENDING") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else pending


PREWRITE_SUMMARY_LABELS = {
    "owner_task_and_scope": "Owner task and scope",
    "content_value_and_cta_policy": "Content value and CTA policy",
    "sources_checked_and_uncertainty": "Sources checked and uncertainty",
    "shared_constraints": "Shared constraints",
    "platform_matching_status": "Platform-matching status",
}
PREWRITE_PLAN_LABELS = {
    "task_and_audience": "Task and audience",
    "reader_value_and_secondary_cta": "Reader value and secondary CTA",
    "research_evidence_and_uncertainty": "Research evidence and uncertainty",
    "keyword_and_localization_strategy": "Keyword and localization strategy",
    "factual_claims_and_sources": "Factual claims and sources",
    "title_and_outline": "Title and outline",
    "visual_narrative": "Visual narrative",
    "platform_transport_assumptions": "Platform transport assumptions",
    "risks_and_owner_decisions": "Risks and owner decisions",
}


def render_prewrite_plan_markdown(manifest: dict, manifest_sha256: str) -> str:
    """Render the owner view from the canonical JSON plan; never hand-maintain it."""
    article_plans = manifest.get("article_plans")
    article_plans = article_plans if isinstance(article_plans, list) else []
    article_ids = [str(plan.get("article_id", "")).strip() for plan in article_plans if isinstance(plan, dict)]
    summary = manifest.get("campaign_summary")
    summary = summary if isinstance(summary, dict) else {}
    convention = manifest.get("artifact_convention")
    convention = convention if isinstance(convention, dict) else {}
    shared_pack = manifest.get("shared_evidence_pack")
    shared_pack = shared_pack if isinstance(shared_pack, dict) else {}
    lines = [
        "# Pre-write research and writing plan",
        "",
        "<!-- BLOG_3P_PREWRITE_RENDERED_FROM: prewrite-plan.json -->",
        f"Status: {manifest_text(manifest.get('status'))}",
        f"Owner confirmation ID: {manifest_text(manifest.get('owner_confirmation_id'))}",
        f"Pre-write manifest SHA-256: {manifest_sha256}",
        f"Article IDs: {', '.join(article_ids) if article_ids else 'PENDING'}",
        "",
        "This is a generated, read-only owner view of `prewrite-plan.json`. It is a planning record, not article prose and not a replacement for W's integrated research after confirmation.",
        "",
        "## Artifact convention",
        "",
        f"- Canonical source: `{manifest_text(convention.get('canonical_source'))}`",
        f"- Owner view: `{manifest_text(convention.get('owner_view_path'))}` / `{manifest_text(convention.get('owner_view_mode'))}`",
        f"- Shared evidence pack: `{manifest_text(shared_pack.get('path'))}` (SHA-256: `{manifest_text(shared_pack.get('sha256'))}`)",
        "",
        "## Campaign research summary",
        "",
    ]
    for section in PREWRITE_SUMMARY_SECTIONS:
        lines.append(f"- **{PREWRITE_SUMMARY_LABELS[section]}:** {manifest_text(summary.get(section))}")
    lines.extend(["", "## Per-article plans", ""])
    if not article_plans:
        lines.append("No article plans configured yet.")
    for plan in article_plans:
        if not isinstance(plan, dict):
            continue
        article_id = manifest_text(plan.get("article_id"), pending="UNSPECIFIED_ARTICLE")
        lines.extend([f"### {article_id}", ""])
        for index, section in enumerate(PREWRITE_PLAN_SECTIONS, 1):
            lines.append(f"{index}. **{PREWRITE_PLAN_LABELS[section]}** — {manifest_text(plan.get(section))}")
        evidence_refs = plan.get("evidence_refs")
        if isinstance(evidence_refs, list) and evidence_refs:
            lines.append("- **Evidence references:** " + ", ".join(str(item).strip() for item in evidence_refs if str(item).strip()))
        lines.append("")
    lines.extend([
        "## Owner decision",
        "",
        "- [ ] `OWNER_PREWRITE_PLAN_CONFIRMED` — permits G to lock requirements and dispatch article worktrees.",
        "- [ ] `OWNER_PREWRITE_PLAN_CHANGES_REQUESTED` — revise the canonical JSON plan; do not dispatch article worktrees, W or R.",
        "",
    ])
    return "\n".join(lines)


def render_confirmation_markdown(*, status: str, confirmation_id: object, report_sha256: object, manifest_sha256: object, article_ids: list[str]) -> str:
    return "\n".join([
        "# Campaign confirmation",
        "",
        "<!-- BLOG_3P_PREWRITE_CONFIRMATION_RENDERED -->",
        "## Pre-write plan confirmation",
        "",
        f"Pre-write plan status: {manifest_text(status)}",
        f"Pre-write plan confirmation ID: {manifest_text(confirmation_id)}",
        f"Pre-write report SHA-256: {manifest_text(report_sha256)}",
        f"Pre-write manifest SHA-256: {manifest_text(manifest_sha256)}",
        f"Pre-write article IDs: {', '.join(article_ids) if article_ids else 'PENDING'}",
        "",
    ])


def replace_generated_receipt_block(text: str, block: str) -> str:
    start = "<!-- BLOG_3P_PREWRITE_RECEIPT_START -->"
    end = "<!-- BLOG_3P_PREWRITE_RECEIPT_END -->"
    replacement = f"{start}\n{block.rstrip()}\n{end}"
    pattern = re.compile(re.escape(start) + r"[\s\S]*?" + re.escape(end))
    if pattern.search(text):
        return pattern.sub(replacement, text, count=1)
    suffix = "\n" if text.endswith("\n") else "\n\n"
    return text + suffix + replacement + "\n"


def render_requirements_receipt(*, status: str, confirmation_id: object, report_sha256: object, manifest_sha256: object, article_ids: list[str]) -> str:
    return "\n".join([
        "## Bound pre-write plan",
        "",
        f"Pre-write plan status: {manifest_text(status)}",
        f"Pre-write plan confirmation ID: {manifest_text(confirmation_id)}",
        f"Pre-write report SHA-256: {manifest_text(report_sha256)}",
        f"Pre-write manifest SHA-256: {manifest_text(manifest_sha256)}",
        f"Pre-write article IDs: {', '.join(article_ids) if article_ids else 'PENDING'}",
    ])


def read_workspace_json(workspace: Path, name: str) -> tuple[dict | None, str | None]:
    path = workspace / name
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, f"{name} must be valid JSON: {exc}"
    if not isinstance(value, dict):
        return None, f"{name} must contain a JSON object"
    return value, None


def sync_prewrite_plan(workspace: Path) -> int:
    """Synchronize generated plan/receipt views from the canonical JSON manifest."""
    cfg, cfg_error = read_workspace_json(workspace, "campaign.json")
    st, state_error = read_workspace_json(workspace, "state.json")
    manifest, manifest_error = read_workspace_json(workspace, "prewrite-plan.json")
    errors = [error for error in (cfg_error, state_error, manifest_error) if error]
    if errors or cfg is None or st is None or manifest is None:
        print("PREWRITE_SYNC_FAILED\n" + "\n".join(errors))
        return 1
    if manifest.get("campaign_id") != cfg.get("campaign_id"):
        print("PREWRITE_SYNC_FAILED\nprewrite-plan.json campaign_id does not match campaign.json")
        return 1
    status = manifest.get("status")
    if status not in PREWRITE_STATUSES:
        print("PREWRITE_SYNC_FAILED\nprewrite-plan.json status is invalid")
        return 1
    article_plans = manifest.get("article_plans")
    if not isinstance(article_plans, list) or not all(isinstance(plan, dict) for plan in article_plans):
        print("PREWRITE_SYNC_FAILED\nprewrite-plan.json article_plans must be a list of objects")
        return 1
    plan_ids = [str(plan.get("article_id", "")).strip() for plan in article_plans]
    articles = cfg.get("articles")
    articles = articles if isinstance(articles, list) else []
    configured_ids = [str(article.get("article_id", "")).strip() for article in articles if isinstance(article, dict)]
    if status == "OWNER_PREWRITE_PLAN_CONFIRMED":
        confirmation_id = manifest.get("owner_confirmation_id")
        if not non_empty_string(confirmation_id):
            print("PREWRITE_SYNC_FAILED\nconfirmed pre-write plan requires owner_confirmation_id")
            return 1
        if not exact_article_coverage(plan_ids, configured_ids):
            print("PREWRITE_SYNC_FAILED\nconfirmed pre-write plan must cover every configured article exactly once")
            return 1
    manifest_path = workspace / "prewrite-plan.json"
    report_path = workspace / "prewrite-plan.md"
    manifest_sha = sha256_file(manifest_path)
    report_path.write_text(render_prewrite_plan_markdown(manifest, manifest_sha), encoding="utf-8")
    report_sha = sha256_file(report_path)
    confirmed = status == "OWNER_PREWRITE_PLAN_CONFIRMED"
    receipt_confirmation_id = manifest.get("owner_confirmation_id") if confirmed else None
    receipt_article_ids = plan_ids if confirmed else []
    receipt_report_sha = report_sha if confirmed else None
    receipt_manifest_sha = manifest_sha if confirmed else None
    prewrite = st.setdefault("prewrite_plan", {})
    prewrite.update({
        "status": status,
        "report_path": "prewrite-plan.md",
        "report_sha256": receipt_report_sha,
        "manifest_path": "prewrite-plan.json",
        "manifest_sha256": receipt_manifest_sha,
        "article_ids": receipt_article_ids,
        "owner_confirmation_id": receipt_confirmation_id,
    })
    if confirmed and st.get("phase") in {"prewrite_planning", "awaiting_owner_prewrite_confirmation"}:
        st["phase"] = "research"
    scope_lock = cfg.setdefault("scope_lock", {})
    scope_lock["prewrite_plan_receipt"] = {
        "owner_confirmation_id": receipt_confirmation_id,
        "report_sha256": receipt_report_sha,
        "manifest_sha256": receipt_manifest_sha,
        "article_ids": receipt_article_ids,
    }
    confirmation_path = workspace / "confirmation.md"
    confirmation_path.write_text(
        render_confirmation_markdown(
            status=status,
            confirmation_id=receipt_confirmation_id,
            report_sha256=receipt_report_sha,
            manifest_sha256=receipt_manifest_sha,
            article_ids=receipt_article_ids,
        ),
        encoding="utf-8",
    )
    requirements_path = workspace / "requirements-contract.md"
    existing_requirements = requirements_path.read_text(encoding="utf-8") if requirements_path.exists() else "# Requirements contract\n\n## Stable requirements\n\n"
    requirements_path.write_text(
        replace_generated_receipt_block(
            existing_requirements,
            render_requirements_receipt(
                status=status,
                confirmation_id=receipt_confirmation_id,
                report_sha256=receipt_report_sha,
                manifest_sha256=receipt_manifest_sha,
                article_ids=receipt_article_ids,
            ),
        ),
        encoding="utf-8",
    )
    dump(workspace / "campaign.json", cfg)
    dump(workspace / "state.json", st)
    print(
        "PREWRITE_SYNCED"
        + f"\nstatus={status}"
        + f"\nmanifest_sha256={manifest_sha}"
        + f"\nreport_sha256={report_sha}"
    )
    return 0


def render_prewrite_plan(manifest_path: Path, output: Path) -> int:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"PREWRITE_RENDER_FAILED\nmanifest must be valid JSON: {exc}")
        return 1
    if not isinstance(manifest, dict):
        print("PREWRITE_RENDER_FAILED\nmanifest must contain a JSON object")
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_prewrite_plan_markdown(manifest, sha256_file(manifest_path)), encoding="utf-8")
    print(f"PREWRITE_RENDERED: {output}")
    return 0


def article_record(cfg: dict, article_id: str) -> dict | None:
    articles = cfg.get("articles")
    if not isinstance(articles, list):
        return None
    for article in articles:
        if isinstance(article, dict) and str(article.get("article_id", "")).strip() == article_id:
            return article
    return None


def article_plan_record(manifest: dict, article_id: str) -> dict | None:
    plans = manifest.get("article_plans")
    if not isinstance(plans, list):
        return None
    for plan in plans:
        if isinstance(plan, dict) and str(plan.get("article_id", "")).strip() == article_id:
            return plan
    return None


def active_findings_for_article(finding_status: object, article_id: str) -> list[dict]:
    """Keep review context compact while retaining IDs and lineage pointers."""
    if not isinstance(finding_status, dict):
        return []
    active: list[dict] = []
    closed = {"RESOLVED", "CLOSED", "ACCEPTED", "SUPERSEDED"}
    for finding_id, value in finding_status.items():
        if not isinstance(value, dict):
            continue
        owner_article = str(value.get("article_id", "")).strip()
        status = str(value.get("status", "OPEN")).strip().upper()
        if owner_article == article_id and status not in closed:
            active.append({
                "id": str(finding_id),
                "status": status,
                "supersedes": value.get("supersedes"),
                "split_from": value.get("split_from"),
                "report_path": value.get("report_path"),
            })
    return sorted(active, key=lambda item: item["id"])


def build_article_context(workspace: Path, article_id: str, output: Path) -> int:
    """Create the compact, hash-bound context capsule for one existing article lane."""
    cfg, cfg_error = read_workspace_json(workspace, "campaign.json")
    st, state_error = read_workspace_json(workspace, "state.json")
    manifest, manifest_error = read_workspace_json(workspace, "prewrite-plan.json")
    errors = [error for error in (cfg_error, state_error, manifest_error) if error]
    if errors or cfg is None or st is None or manifest is None:
        print("ARTICLE_CONTEXT_BUILD_FAILED\n" + "\n".join(errors))
        return 1
    if st.get("prewrite_plan", {}).get("status") != "OWNER_PREWRITE_PLAN_CONFIRMED":
        print("ARTICLE_CONTEXT_BUILD_FAILED\nowner-confirmed pre-write plan is required before an article context can exist")
        return 1
    article = article_record(cfg, article_id)
    plan = article_plan_record(manifest, article_id)
    if article is None or plan is None:
        print("ARTICLE_CONTEXT_BUILD_FAILED\narticle must exist exactly once in campaign.json and prewrite-plan.json")
        return 1
    assignments = cfg.get("article_platform_assignment", {}).get("assignments", [])
    assignment = next((item for item in assignments if isinstance(item, dict) and str(item.get("article_id", "")).strip() == article_id), None) if isinstance(assignments, list) else None
    locale_rows = cfg.get("locale_platform_validation", {}).get("rows", [])
    locale_row = next((item for item in locale_rows if isinstance(item, dict) and str(item.get("article_id", "")).strip() == article_id), None) if isinstance(locale_rows, list) else None
    source_paths = ("campaign.json", "prewrite-plan.json", "requirements-contract.md")
    context = {
        "schema_version": ARTICLE_CONTEXT_SCHEMA,
        "campaign_id": cfg.get("campaign_id"),
        "article_id": article_id,
        "frozen_article": article,
        "prewrite_plan": plan,
        "platform_assignment": assignment,
        "locale_platform_validation": locale_row,
        "source_hashes": {name: sha256_file(workspace / name) for name in source_paths},
        "open_findings": active_findings_for_article(st.get("finding_status"), article_id),
        "artifact_paths": {
            "evidence_pack": "research/evidence-pack.json",
            "canonical_article": "canonical/article.md",
            "visual_manifest": "canonical/visual-manifest.json",
            "article_package": "article-package.json",
            "review_index": "reviews/review-index.json",
            "handoff_manifest": "handoff/handoff-manifest.json",
            "visual_payload": "handoff/visual-payload.html",
        },
        "rehydration_protocol": {
            "always_read_first": ["CURRENT_WORKFLOW_CORE", "context/article-contract.json", "reviews/review-index.json"],
            "expand_historical_material_when": ["CONTEXT_COMPACTION", "INPUT_HASH_DRIFT", "OPEN_FINDING_LINEAGE", "R_DELTA_ESCALATION", "OWNER_SCOPE_CHANGE"],
            "do_not_reload_unaffected_history": True,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    dump(output, context)
    print(f"ARTICLE_CONTEXT_BUILT: {output}")
    return 0


def article_context_errors(workspace: Path, context_path: Path) -> list[str]:
    """Return source-of-truth drift errors for a compact lane context."""
    context, context_error = json_object_file(context_path, label="article context")
    errors: list[str] = [context_error] if context_error else []
    if context is None:
        return errors
    if context.get("schema_version") != ARTICLE_CONTEXT_SCHEMA:
        errors.append("article context schema_version must be 1.0")
    article_id = str(context.get("article_id", "")).strip()
    if not article_id:
        errors.append("article context requires article_id")
    cfg, cfg_error = read_workspace_json(workspace, "campaign.json")
    state, state_error = read_workspace_json(workspace, "state.json")
    manifest, manifest_error = read_workspace_json(workspace, "prewrite-plan.json")
    if cfg_error:
        errors.append(cfg_error)
    if state_error:
        errors.append(state_error)
    if manifest_error:
        errors.append(manifest_error)
    if cfg is not None and article_id and context.get("frozen_article") != article_record(cfg, article_id):
        errors.append("article context frozen_article no longer matches campaign.json")
    if manifest is not None and article_id and context.get("prewrite_plan") != article_plan_record(manifest, article_id):
        errors.append("article context prewrite_plan no longer matches prewrite-plan.json")
    if state is not None and article_id and context.get("open_findings") != active_findings_for_article(state.get("finding_status"), article_id):
        errors.append("article context open findings no longer match state.json")
    source_hashes = context.get("source_hashes")
    if not isinstance(source_hashes, dict):
        errors.append("article context requires source_hashes")
    else:
        for relative, expected_hash in source_hashes.items():
            path, path_error = workspace_file(workspace, relative, label="article context source")
            if path_error:
                errors.append(path_error)
            elif path is not None and expected_hash != sha256_file(path):
                errors.append(f"article context source hash changed: {relative}")
    expected_paths = {
        "evidence_pack": "research/evidence-pack.json",
        "canonical_article": "canonical/article.md",
        "visual_manifest": "canonical/visual-manifest.json",
        "article_package": "article-package.json",
        "review_index": "reviews/review-index.json",
        "handoff_manifest": "handoff/handoff-manifest.json",
        "visual_payload": "handoff/visual-payload.html",
    }
    if context.get("artifact_paths") != expected_paths:
        errors.append("article context artifact paths are invalid")
    protocol = context.get("rehydration_protocol")
    if not isinstance(protocol, dict) or protocol.get("do_not_reload_unaffected_history") is not True:
        errors.append("article context rehydration protocol is invalid")
    return errors


def check_article_context(workspace: Path, context_path: Path) -> int:
    """Verify that a compact lane capsule still represents the frozen source inputs."""
    errors = article_context_errors(workspace, context_path)
    if errors:
        print("ARTICLE_CONTEXT_INVALID\n" + "\n".join(errors))
        return 1
    print("ARTICLE_CONTEXT_VALID")
    return 0


def build_review_index(workspace: Path, context_path: Path, output: Path, canonical_path: Path | None) -> int:
    """Create a compact review baseline; it records pointers rather than duplicating research prose."""
    context_errors = article_context_errors(workspace, context_path)
    if context_errors:
        print("REVIEW_INDEX_BUILD_FAILED\narticle contract is stale or invalid\n" + "\n".join(context_errors))
        return 1
    context, error = json_object_file(context_path, label="article contract")
    if error or context is None:
        print("REVIEW_INDEX_BUILD_FAILED\n" + (error or "invalid article contract"))
        return 1
    if context.get("schema_version") != ARTICLE_CONTEXT_SCHEMA or not non_empty_string(context.get("article_id")):
        print("REVIEW_INDEX_BUILD_FAILED\narticle contract schema or article_id is invalid")
        return 1
    canonical = canonical_path or workspace / str(context.get("artifact_paths", {}).get("canonical_article", "canonical/article.md"))
    canonical_record = {"path": relative_path(workspace, canonical), "sha256": sha256_file(canonical)} if canonical.is_file() else {"path": relative_path(workspace, canonical), "sha256": None}
    index = {
        "schema_version": REVIEW_INDEX_SCHEMA,
        "article_id": context["article_id"],
        "article_contract": {"path": relative_path(workspace, context_path), "sha256": sha256_file(context_path)},
        "canonical": canonical_record,
        "open_findings": context.get("open_findings", []),
        "latest_research_review": {
            "status": "PENDING", "report_path": None, "report_sha256": None,
            "reviewer_agent_id": None, "reviewed_evidence_pack_sha256": None,
        },
        "latest_full_review": {
            "status": "PENDING", "report_path": None, "report_sha256": None,
            "reviewer_agent_id": None, "canonical_sha256": canonical_record["sha256"],
        },
        "last_delta": None,
        "read_protocol": context.get("rehydration_protocol"),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    dump(output, index)
    print(f"REVIEW_INDEX_BUILT: {output}")
    return 0


def review_record_errors(
    workspace: Path, record: object, *, label: str, allowed_statuses: set[str],
    approved_status: str, require_approved: bool, expected_artifact_sha256: str | None = None,
    artifact_field: str | None = None, pending_allows_artifact: bool = False,
) -> list[str]:
    """Validate one small R decision receipt without trying to score the report text."""
    if not isinstance(record, dict):
        return [f"review index requires {label}"]
    errors: list[str] = []
    status = record.get("status")
    if status not in allowed_statuses:
        errors.append(f"{label} has an invalid status")
    if status == "PENDING":
        for field in ("report_path", "report_sha256", "reviewer_agent_id"):
            if record.get(field) not in {None, ""}:
                errors.append(f"pending {label} may not carry {field}")
        if artifact_field is not None and not pending_allows_artifact and record.get(artifact_field) not in {None, ""}:
            errors.append(f"pending {label} may not carry {artifact_field}")
    else:
        for field in ("report_path", "report_sha256", "reviewer_agent_id"):
            if not non_empty_string(record.get(field)):
                errors.append(f"{label} requires {field}")
        report_path, report_error = workspace_file(workspace, record.get("report_path"), label=f"{label} report")
        if report_error:
            errors.append(report_error)
        elif report_path is not None and record.get("report_sha256") != sha256_file(report_path):
            errors.append(f"{label} report_sha256 does not match")
        if artifact_field is not None:
            if not non_empty_string(record.get(artifact_field)):
                errors.append(f"{label} requires {artifact_field}")
            elif expected_artifact_sha256 is not None and record.get(artifact_field) != expected_artifact_sha256:
                errors.append(f"{label} {artifact_field} does not match")
    if require_approved and status != approved_status:
        errors.append(f"handoff requires {label} status {approved_status}")
    return errors


def review_index_errors(
    workspace: Path, index_path: Path, *, require_research_approved: bool = False,
    require_full_approved: bool = False,
) -> list[str]:
    """Verify review-baseline provenance before an R or hand-off turn."""
    index, index_error = json_object_file(index_path, label="review index")
    errors: list[str] = [index_error] if index_error else []
    if index is None:
        return errors
    if index.get("schema_version") != REVIEW_INDEX_SCHEMA:
        errors.append("review index schema_version must be 1.0")
    article_id = str(index.get("article_id", "")).strip()
    if not article_id:
        errors.append("review index requires article_id")
    context: dict | None = None
    contract = index.get("article_contract")
    if not isinstance(contract, dict):
        errors.append("review index requires article_contract")
    else:
        context_path, context_error = workspace_file(workspace, contract.get("path"), label="review index article_contract")
        if context_error:
            errors.append(context_error)
        elif context_path is not None:
            if contract.get("sha256") != sha256_file(context_path):
                errors.append("review index article contract hash does not match")
            errors.extend(article_context_errors(workspace, context_path))
            context, parsed_context_error = json_object_file(context_path, label="article context")
            if parsed_context_error or context is None:
                errors.append(parsed_context_error or "article context is invalid")
            elif context.get("article_id") != article_id:
                errors.append("review index article_id does not match article context")
    canonical = index.get("canonical")
    if not isinstance(canonical, dict):
        errors.append("review index requires canonical record")
    else:
        canonical_path, canonical_error = workspace_file(workspace, canonical.get("path"), label="review index canonical path")
        if canonical_error:
            errors.append(canonical_error)
        elif canonical_path is not None and canonical.get("sha256") is not None and canonical.get("sha256") != sha256_file(canonical_path):
            errors.append("review index canonical hash does not match")
    if not isinstance(index.get("open_findings"), list):
        errors.append("review index open_findings must be a list")
    evidence_pack_sha256 = None
    if isinstance(context, dict):
        evidence_pack_path = context.get("artifact_paths", {}).get("evidence_pack") if isinstance(context.get("artifact_paths"), dict) else None
        evidence_pack, evidence_pack_error = workspace_file(workspace, evidence_pack_path, label="review index evidence pack")
        if evidence_pack_error and require_research_approved:
            errors.append(evidence_pack_error)
        elif evidence_pack is not None:
            evidence_pack_sha256 = sha256_file(evidence_pack)
    errors.extend(review_record_errors(
        workspace, index.get("latest_research_review"), label="latest_research_review",
        allowed_statuses=RESEARCH_REVIEW_STATUSES, approved_status="RESEARCH_APPROVED",
        require_approved=require_research_approved, expected_artifact_sha256=evidence_pack_sha256,
        artifact_field="reviewed_evidence_pack_sha256",
    ))
    canonical_sha256 = None
    if isinstance(canonical, dict) and canonical.get("sha256") is not None:
        canonical_sha256 = canonical.get("sha256")
    errors.extend(review_record_errors(
        workspace, index.get("latest_full_review"), label="latest_full_review",
        allowed_statuses=FULL_REVIEW_STATUSES, approved_status="APPROVED",
        require_approved=require_full_approved, expected_artifact_sha256=canonical_sha256,
        artifact_field="canonical_sha256", pending_allows_artifact=True,
    ))
    return errors


def check_review_index(workspace: Path, index_path: Path) -> int:
    """Verify review-baseline provenance before an R full or delta turn."""
    errors = review_index_errors(workspace, index_path)
    if errors:
        print("REVIEW_INDEX_INVALID\n" + "\n".join(errors))
        return 1
    print("REVIEW_INDEX_VALID")
    return 0


def registered_reviewer_id(workspace: Path, article_id: str) -> tuple[str | None, list[str]]:
    """Resolve the one visible R registered for an article lane."""
    state, state_error = read_workspace_json(workspace, "state.json")
    if state_error or state is None:
        return None, [state_error or "state.json is invalid"]
    orchestration = state.get("orchestration")
    workspaces = orchestration.get("article_workspaces") if isinstance(orchestration, dict) else None
    lane = workspaces.get(article_id) if isinstance(workspaces, dict) else None
    bundle = lane.get("role_bundle") if isinstance(lane, dict) else None
    reviewer_id = bundle.get("reviewer_agent") if isinstance(bundle, dict) else None
    if not non_empty_string(reviewer_id):
        return None, ["handoff requires the registered article lane reviewer"]
    return reviewer_id, []


def reviewer_task_receipt_errors(
    workspace: Path, *, article_id: str, reviewer_agent_id: str, workflow_stage: str,
    result: str, report_path: str,
) -> list[str]:
    """Require one visible R task receipt for a final approval without rereading its report."""
    state, state_error = read_workspace_json(workspace, "state.json")
    if state_error or state is None:
        return [state_error or "state.json is invalid"]
    orchestration = state.get("orchestration")
    tasks = orchestration.get("tasks") if isinstance(orchestration, dict) else None
    if not isinstance(tasks, list):
        return ["handoff requires the visible task ledger"]
    for task in tasks:
        if not isinstance(task, dict):
            continue
        if (
            task.get("article_id") == article_id
            and task.get("role") == "ARTICLE_LANGUAGE_REVIEWER"
            and task.get("agent_id") == reviewer_agent_id
            and task.get("workflow_stage") == workflow_stage
            and task.get("result") == result
            and task.get("result_path") == report_path
            and task.get("status") == "COMPLETED"
        ):
            return []
    return [
        "handoff requires a completed visible reviewer task for "
        f"{workflow_stage} at {report_path}"
    ]


def handoff_review_approval_errors(workspace: Path, article_id: str) -> tuple[list[str], dict | None, str | None]:
    """Bind hand-off to the registered R's research and full-review approvals."""
    index_path = workspace / "reviews/review-index.json"
    errors = review_index_errors(
        workspace, index_path, require_research_approved=True, require_full_approved=True,
    )
    index, index_error = json_object_file(index_path, label="handoff review index")
    if index_error or index is None:
        errors.append(index_error or "handoff requires a review index")
        return errors, None, None
    if index.get("article_id") != article_id:
        errors.append("handoff review index article_id does not match article package")
    reviewer_id, reviewer_errors = registered_reviewer_id(workspace, article_id)
    errors.extend(reviewer_errors)
    if reviewer_id is None:
        return errors, index, None
    research = index.get("latest_research_review")
    full = index.get("latest_full_review")
    for label, record, stage, result in (
        ("latest_research_review", research, "RESEARCH_REVIEW", "RESEARCH_APPROVED"),
        ("latest_full_review", full, "FULL_REVIEW", "APPROVED"),
    ):
        if not isinstance(record, dict):
            continue
        if record.get("reviewer_agent_id") != reviewer_id:
            errors.append(f"{label} reviewer_agent_id must match the registered article reviewer")
            continue
        report_path = record.get("report_path")
        if non_empty_string(report_path):
            errors.extend(reviewer_task_receipt_errors(
                workspace, article_id=article_id, reviewer_agent_id=reviewer_id,
                workflow_stage=stage, result=result, report_path=report_path,
            ))
    return errors, index, reviewer_id


def check_review_delta(workspace: Path, delta_path: Path) -> int:
    """Validate a narrow R-delta hand-off without asking R to reload unrelated history."""
    delta, error = json_object_file(delta_path, label="review delta")
    errors: list[str] = [error] if error else []
    if delta is None:
        print("REVIEW_DELTA_INVALID\n" + "\n".join(errors))
        return 1
    if delta.get("schema_version") != REVIEW_DELTA_SCHEMA:
        errors.append("review delta schema_version must be 1.0")
    article_id = str(delta.get("article_id", "")).strip()
    if not article_id:
        errors.append("review delta requires article_id")
    review_index_path, index_path_error = workspace_file(workspace, delta.get("review_index_path"), label="review delta review_index_path")
    if index_path_error:
        errors.append(index_path_error)
    else:
        assert review_index_path is not None
        errors.extend(review_index_errors(
            workspace, review_index_path, require_research_approved=True, require_full_approved=True,
        ))
        index, index_error = json_object_file(review_index_path, label="review index")
        if index_error or index is None:
            errors.append(index_error or "review index is invalid")
        else:
            if index.get("schema_version") != REVIEW_INDEX_SCHEMA:
                errors.append("review delta references an unsupported review index")
            if index.get("article_id") != article_id:
                errors.append("review delta article_id does not match review index")
            if delta.get("review_index_sha256") != sha256_file(review_index_path):
                errors.append("review delta review_index_sha256 does not match")
    review_scope = delta.get("review_scope")
    if review_scope not in DELTA_REVIEW_SCOPES:
        errors.append("review delta review_scope must be R_DELTA or R_VISUAL_DELTA")
    attempt = delta.get("r_delta_attempt")
    if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
        errors.append("review delta r_delta_attempt must be a positive integer")
    if isinstance(attempt, int) and attempt > 2 and delta.get("full_review_required") is not True:
        errors.append("review delta after two attempts must escalate to a full review")
    changed = delta.get("changed_artifacts")
    if not isinstance(changed, list) or not changed:
        errors.append("review delta requires non-empty changed_artifacts")
    elif all(isinstance(item, dict) for item in changed):
        kinds: set[str] = set()
        for item in changed:
            kind = item.get("change_kind")
            kinds.add(str(kind))
            if kind not in DELTA_CHANGE_KINDS:
                errors.append("review delta changed artifact has unknown change_kind")
            artifact_path, artifact_error = workspace_file(workspace, item.get("path"), label="review delta changed artifact")
            if artifact_error:
                errors.append(artifact_error)
            elif artifact_path is not None and item.get("sha256") != sha256_file(artifact_path):
                errors.append("review delta changed artifact sha256 does not match")
            if not isinstance(item.get("affected_requirement_ids"), list) or not isinstance(item.get("affected_finding_ids"), list):
                errors.append("review delta changed artifact requires affected requirement and finding ID lists")
        if review_scope == "R_VISUAL_DELTA" and not kinds <= {"VISUAL_ASSET", "VISUAL_MANIFEST", "VISUAL_PAYLOAD"}:
            errors.append("R_VISUAL_DELTA may only contain visual artifacts")
        if "REQUIREMENTS_OR_SCOPE" in kinds and delta.get("full_review_required") is not True:
            errors.append("requirements or scope changes require a full review")
    else:
        errors.append("review delta changed_artifacts must contain objects")
    if errors:
        print("REVIEW_DELTA_INVALID\n" + "\n".join(errors))
        return 1
    print("REVIEW_DELTA_VALID")
    return 0


def markdown_field(text: str, label: str) -> str | None:
    match = re.search(rf"(?mi)^\s*{re.escape(label)}\s*:\s*\`?([^\`\n]+?)\`?\s*$", text)
    return match.group(1).strip() if match else None


def csv_values(value: str | None) -> list[str]:
    if value is None:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def exact_article_coverage(candidate_ids: object, article_ids: list[str]) -> bool:
    if not isinstance(candidate_ids, list) or not article_ids:
        return False
    normalized = [str(item).strip() for item in candidate_ids]
    return (
        all(normalized)
        and len(normalized) == len(article_ids)
        and len(set(normalized)) == len(normalized)
        and set(normalized) == set(article_ids)
    )


def campaign(campaign_id: str) -> dict:
    return {
        "schema_version": "2.4", "campaign_id": campaign_id,
        "scope_lock": {"status": "DRAFT", "owner_confirmation": "PENDING", "prewrite_plan_receipt": {"owner_confirmation_id": None, "report_sha256": None, "manifest_sha256": None, "article_ids": []}},
        "prewrite_plan_policy": {"mode": "CAMPAIGN_G_PREWRITE_EVIDENCE_AND_PLAN", "required_before_article_dispatch": True, "owner_confirmation_required": True, "report_path": "prewrite-plan.md", "manifest_path": "prewrite-plan.json", "confirmation_path": "confirmation.md", "requirements_contract_path": "requirements-contract.md", "requires_per_article_plan": True, "article_plan_sections": PREWRITE_PLAN_SECTIONS, "campaign_summary_sections": PREWRITE_SUMMARY_SECTIONS, "allow_article_roles_before_confirmation": False, "standalone_article_research_role": "PROHIBITED", "writer_research_remains_required": True, "canonical_source": "prewrite-plan.json", "owner_view_mode": "DETERMINISTIC_RENDERED_READ_ONLY", "manual_duplicate_entry": "PROHIBITED", "sync_command": "sync-prewrite-plan"},
        "platform_scope": {"source": "OWNER_SELECTION_LOCK_ONLY", "allowed_pairs": [], "automatic_discovery_or_expansion": False, "on_exhaustion": "CAPACITY_BLOCKED", "selection_lock": {"path": "owner-platform-selection.json", "sha256": "PENDING_OWNER_CONFIRMATION", "mode": "OWNER_SOURCE_RECEIPTS_ONLY", "internal_candidates_may_be_selected": False, "eligibility_evidence_may_select_platform": False, "on_missing_receipt": "OWNER_DECISION_REQUIRED"}},
        "platform_matching_policy": {"mode": "VISIBLE_SUBAGENT_RESEARCH_THEN_OWNER_LOCK", "researcher_role": MATCHING_ROLE, "reusable": True, "candidate_universe": "OWNER_SOURCE_ARTIFACT_ONLY", "main_controller_may_select_or_rank": False, "proposal_may_write_allowed_pairs": False, "owner_confirmation_required_before_lock": True, "proposal_path": "evidence/platform-matching/platform-matching-proposal.json"},
        "articles": [],
        "article_platform_assignment": {"mode": "ONE_ARTICLE_ONE_DISTINCT_PLATFORM", "required_before_editorial_dispatch": True, "platform_reuse_across_articles": "PROHIBITED", "pair_reuse_across_articles": "PROHIBITED", "assignments": [], "on_missing_or_duplicate": "ARTICLE_PLATFORM_ASSIGNMENT_BLOCKED_RECONFIRM_OWNER"},
        "locale_platform_validation": {"mode": "ARTICLE_LANGUAGE_MARKET_PLATFORM_EVIDENCE", "required_before_editorial_dispatch": True, "rows": [], "on_mismatch": "LOCALE_PLATFORM_MISMATCH_RECONFIRM_OWNER", "article_language_source": "USER_CONFIRMED_ARTICLE_LANGUAGE_ONLY", "platform_language_role": "ELIGIBILITY_ONLY_NEVER_REWRITE_LANGUAGE"},
        "title_quality_policy": {"mode": "MODEL_LED_SEMANTIC_REVIEW", "required_before_review": True, "review_dimensions": ["topic_clarity", "reader_intent", "distinct_value", "natural_language", "market_suitability"], "heuristics": {"minimum_word_count": 6, "minimum_visible_char_count": 24, "non_blocking": True}},
        "content_value_policy": {"mode": "READER_VALUE_FIRST", "primary_purpose": "STANDALONE_ANSWER_TO_READER_TASK", "cta_role": "REQUIRED_SECONDARY_TRANSPARENT_RECOMMENDATION", "cta_must_be_present": True, "cta_requires_identifiable_product_and_claim_basis": True, "cta_requires_relationship_disclosure_when_applicable": True, "cta_must_not_replace_or_dominate_reader_value": True},
        "keyword_research_policy": {"mode": "PRE_DRAFT_LONG_TAIL_AND_REGIONAL_SERP", "required_after_owner_prewrite_confirmation_before_drafting": True, "creative_angle_is_not_keyword_evidence": True, "variant_priority_order": PRIORITY, "english_multi_article_intents_must_be_distinct": True, "regional_serp_variants_required_for_every_target_language": True, "model_translation_fallback_requires_independent_regional_serp_checks": 2},
        "platform_style_research_policy": {"mode": "IN_SCOPE_READONLY_DUAL_PROFILE", "attempt_before_drafting": True, "in_scope_platforms_only": True, "sample_shortage": "UNVERIFIED_USE_CONSERVATIVE_GENERIC", "editorial_profile_is_non_binding": True, "durable_harvest_requires_public_qa_passed": True},
        "visual_narrative_policy": {"mode": "LEAD_MIDDLE_CLOSING_REQUIRED", "default_applies_to": ["guide", "tutorial", "comparison", "review", "long_explainer"], "default_minimum_images": 3, "required_coverage_zones": VISUAL_ZONES, "all_articles_required": False, "exception_requires_owner_confirmation": True},
        "cross_language_seo": {"status": "NOT_REQUESTED", "target_locales": [], "google_trends_seed_language": "ENGLISH_ONLY", "variant_priority_order": PRIORITY, "minimum_independent_regional_serp_checks_for_fallback": 2},
        "quality_policy": {"aitdk_local_reference": "required", "plugin_scan": "best_effort_non_blocking", "final_prepublication_target": "visual-payload.html"},
        "artifact_optimization_policy": ARTIFACT_OPTIMIZATION_POLICY_2_4,
        "orchestration_policy": {"delegation_default": "VISIBLE_SUBAGENTS", "visible_task_record_required": True, "invisible_cli_agent_sessions": "PROHIBITED", "writer_reviewer_pair_mode": "ONE_REUSABLE_PAIR_PER_ARTICLE", "cross_article_agent_reuse": "PROHIBITED", "operations_steward_mode": "ONE_REUSABLE_CAMPAIGN_OPERATIONS_STEWARD", "persistent_requirements_gatekeeper": True, "fresh_agent_roles": [], "pair_activation": "G_QUEUE_SUBJECT_TO_RUNTIME_CAPACITY", "execution_isolation": "WORKTREE_FIRST_PER_ARTICLE", "worktree_autospawn": "CREATE_VISIBLE_PROJECT_WORKTREE_PER_READY_ARTICLE_WHEN_SUPPORTED", "worktree_fallback": "VISIBLE_SHARED_WORKSPACE_WITH_PATH_ISOLATION", "silent_worktree_fallback": False, "article_worktree_role_bundle": "ONE_REUSABLE_W_R_G_LANE_PER_ARTICLE", "project_worktree_root_role": "ARTICLE_LANE_GATEKEEPER", "campaign_gatekeeper_scope": "GLOBAL_REQUIREMENTS_QUEUE_AND_LEDGER_ONLY", "article_public_gate_mode": "REUSE_ARTICLE_LANE_GATEKEEPER_ONLY", "public_qa_policy": PUBLIC_QA_POLICY_2_3, "queue_resume_policy": "AUTO_START_NEXT_READY_TASK_ON_SLOT_AVAILABLE", "article_agent_replacement_requires_full_rehydration": True, "allowed_main_cli_use": ["local_file_operations", "deterministic_validation", "hashing", "read_only_inspection", "version_control"]},
        "release_policy": {
            "mode": "HUMAN_NATIVE_ONLY",
            "machine_external_writes_allowed": False,
            "default_title_transfer_mode": "SEPARATE_TITLE_FIELD",
            "heading_hierarchy_policy": {
                "authority": "PUBLIC_READER_PAGE_VISUAL_ONLY",
                "editor_html_or_dom": "NOT_A_VALID_QA_SURFACE",
                "local_payload_markup": "AUTHORING_AND_COPY_SELECTION_AID_ONLY",
                "public_visual_check_requires_human_accepted_url": True,
            },
            "visual_payload_template": {"id": "BLOG_3P_VISUAL_PAYLOAD", "version": "2", "rendering": "COMPILER_ONLY", "model_authored_shell_css_js": "PROHIBITED"},
        },
    }


def state(campaign_id: str) -> dict:
    return {"schema_version": "2.2", "campaign_id": campaign_id, "phase": "prewrite_planning", "round": 0, "history": [], "finding_status": {}, "locale_platform_validation": {}, "prewrite_plan": {"status": "PENDING_OWNER_PREWRITE_PLAN_CONFIRMATION", "report_path": "prewrite-plan.md", "report_sha256": None, "manifest_path": "prewrite-plan.json", "manifest_sha256": None, "article_ids": [], "owner_confirmation_id": None}, "artifact_index": {"article_contexts": {}, "review_indexes": {}, "review_deltas": {}}, "orchestration": {"controller_role": "CAMPAIGN_GATEKEEPER", "tasks": [], "article_queue": [], "article_agents": {}, "article_workspaces": {}, "service_agents": {"campaign_operations": {"role": "CAMPAIGN_OPERATIONS_STEWARD", "agent_id": None, "status": "NOT_STARTED", "reusable": True, "last_rehydrated_at": None}, "platform_matching": {"role": MATCHING_ROLE, "agent_id": None, "status": "NOT_STARTED", "reusable": True, "last_rehydrated_at": None}}, "capacity": {"available_slots": "RUNTIME_DISCOVERED", "active_article_pairs": [], "active_article_worktrees": [], "spawn_policy": "AUTHORIZED_MAXIMIZE_AVAILABLE_CAPACITY", "last_dispatch_at": None}}, "publication": {"status": "NOT_STARTED", "articles": {}}}


def init(workspace: Path, campaign_id: str) -> int:
    if workspace.exists() and any(workspace.iterdir()):
        print(f"ERROR: workspace is not empty: {workspace}")
        return 2
    workspace.mkdir(parents=True, exist_ok=True)
    for name in ("research", "canonical", "reviews", "gate", "handoff", "evidence", "resolutions", "context"):
        (workspace / name).mkdir(exist_ok=True)
    (workspace / "evidence" / "owner-selection").mkdir(exist_ok=True)
    (workspace / "evidence" / "platform-matching").mkdir(exist_ok=True)
    (workspace / "evidence" / "public-qa").mkdir(exist_ok=True)
    (workspace / "evidence" / "shared").mkdir(exist_ok=True)
    dump(workspace / "campaign.json", campaign(campaign_id))
    dump(workspace / "state.json", state(campaign_id))
    dump(workspace / "owner-platform-selection.json", {"schema_version": "1.0", "campaign_id": campaign_id, "status": "PENDING_OWNER_CONFIRMATION", "source_artifacts": [], "pair_receipts": []})
    (workspace / "requirements-contract.md").write_text(
        "# Requirements contract\n\n"
        "G creates stable REQ-<AREA>-NNN entries here only from requirements explicitly confirmed by the owner. "
        "The pre-write receipt block is compiler-managed; do not hand-edit it.\n\n"
        "<!-- BLOG_3P_PREWRITE_RECEIPT_START -->\n"
        "## Bound pre-write plan\n\n"
        "Pre-write plan status: PENDING_OWNER_PREWRITE_PLAN_CONFIRMATION\n"
        "Pre-write plan confirmation ID: PENDING\n"
        "Pre-write report SHA-256: PENDING\n"
        "Pre-write manifest SHA-256: PENDING\n"
        "Pre-write article IDs: PENDING\n"
        "<!-- BLOG_3P_PREWRITE_RECEIPT_END -->\n\n"
        "## Stable requirements\n\n",
        encoding="utf-8",
    )
    dump(workspace / "prewrite-plan.json", {
        "schema_version": "1.3",
        "campaign_id": campaign_id,
        "status": "PENDING_OWNER_PREWRITE_PLAN_CONFIRMATION",
        "owner_confirmation_id": None,
        "artifact_convention": {
            "canonical_source": "prewrite-plan.json",
            "owner_view_path": "prewrite-plan.md",
            "owner_view_mode": "DETERMINISTIC_RENDERED_READ_ONLY",
            "manual_duplicate_entry": "PROHIBITED",
            "writer_research_remains_required": True,
        },
        "shared_evidence_pack": {
            "path": "evidence/shared/campaign-evidence-pack.json",
            "sha256": "PENDING",
            "scope": "CAMPAIGN_READONLY_BASELINE",
            "does_not_replace_article_research": True,
        },
        "campaign_summary": {section: "" for section in PREWRITE_SUMMARY_SECTIONS},
        "article_plans": [],
    })
    (workspace / "pre-clearance-checklist.md").write_text(
        "# One-shot pre-clearance\n\n"
        "- [ ] G writes the canonical `prewrite-plan.json`, runs `sync-prewrite-plan`, and presents the generated `prewrite-plan.md`: every article/subtask has task/audience, independent reader value and a required secondary CTA with exact visible anchor text, product/current destination, evidence basis, reader-task relevance, disclosure and non-claims, plus research evidence and uncertainty, keyword/localization strategy, factual-source plan, title/outline, visual narrative, platform transport assumptions and risks/owner decisions. The Markdown view is read-only and does not replace W's integrated research.\n"
        "- [ ] No article worktree, ARTICLE_LANE_GATEKEEPER, W or R exists before the owner records OWNER_PREWRITE_PLAN_CONFIRMED. The only permitted pre-confirmation child role is the reusable read-only CAMPAIGN_PLATFORM_MATCHING_RESEARCHER when human release is requested.\n"
        "- [ ] Scope, audience, sources, image rights and locales are confirmed. Every new article has a frozen CTA: its exact visible anchor text, product identity, current destination, claim evidence, reader relevance and material-relationship disclosure. It remains secondary and may not be presented as independently tested or ranked.\n"
        "- [ ] Start or resume the visible reusable CAMPAIGN_PLATFORM_MATCHING_RESEARCHER. It reads only the owner candidate source artifacts and public eligibility evidence, then writes evidence/platform-matching/platform-matching-report.md and platform-matching-proposal.json. G must not rank or select candidates.\n"
        "- [ ] For every human-release platform/account pair, have the owner confirm the subagent proposal, then populate owner-platform-selection.json from a user-originated XLSX/table/message artifact: record its hash, exact row/cell or message locator, platform literal, account confirmation literal and owner confirmation ID. Only then hash and lock it in campaign.json. Official login notices, preflight, activation records and campaign configuration are eligibility evidence only and may never select a pair.\n"
        "- [ ] Freeze a visual-narrative policy: coverage zones, minimum image count, each image's adjacent claim and reader job. For a ten-article all-required batch, set all_articles_required: true; do not record a silent exception.\n"
        "- [ ] After owner pre-write confirmation and before prose, the article's W conducts its integrated evidence research and the reusable R returns RESEARCH_APPROVED.\n"
        "- [ ] Before editorial dispatch, every article has exactly one user-confirmed platform/account assignment when a human-release package is requested; platform names and platform/account pairs are unique across articles.\n"
        "- [ ] The runtime's Git-project worktree capability is recorded. When it is available, each ready independent article must receive a visible project worktree before its W/R pair starts; any shared-workspace fallback is explicit and uses disjoint article paths.\n"
        "- [ ] Before review, freeze each article's focus keyword/approved variant, reader task, canonical article title, platform title and SEO title. W/R assess semantic quality; G checks only frozen-field fidelity. Word and character thresholds are non-blocking advisories. Platform title equals canonical title by default.\n"
        "- [ ] Treat local outline markup and title/body transfer as authoring aids only. Do not inspect or edit platform editor HTML/DOM to force H1/H2/H3. After HUMAN_ACCEPTED, heading hierarchy is accepted only from public reader-page visual evidence.\n",
        encoding="utf-8",
    )
    synced = sync_prewrite_plan(workspace)
    if synced != 0:
        return synced
    print(f"INITIALIZED: {workspace}")
    return 0


def check(workspace: Path) -> int:
    missing = [name for name in ("campaign.json", "state.json", "confirmation.md", "requirements-contract.md", "pre-clearance-checklist.md", "research", "canonical", "reviews", "gate", "handoff") if not (workspace / name).exists()]
    if missing:
        print("CHECK_FAILED\n" + "\n".join(f"missing {name}" for name in missing)); return 1
    try:
        cfg = json.loads((workspace / "campaign.json").read_text(encoding="utf-8"))
        st = json.loads((workspace / "state.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"CHECK_FAILED\ninvalid JSON: {exc}"); return 1
    errors: list[str] = []
    parsed_schema_version = parse_schema_version(cfg.get("schema_version"))
    if parsed_schema_version is None:
        errors.append("campaign schema_version must use exact major.minor form")
        # Apply current strict policy after a malformed version so it cannot
        # quietly select a weaker legacy validation path.
        parsed_schema_version = (2, 4)
    requires_prewrite_policy = parsed_schema_version >= (2, 0)
    requires_content_value_policy = parsed_schema_version >= (2, 1)
    requires_required_cta_policy = parsed_schema_version >= (2, 2)
    requires_streamlined_public_qa_policy = parsed_schema_version >= (2, 3)
    requires_artifact_optimization_policy = parsed_schema_version >= (2, 4)
    required_plan_sections = PREWRITE_PLAN_SECTIONS if requires_content_value_policy else LEGACY_PREWRITE_PLAN_SECTIONS
    required_summary_sections = PREWRITE_SUMMARY_SECTIONS if requires_content_value_policy else LEGACY_PREWRITE_SUMMARY_SECTIONS
    prewrite_files_available = all((workspace / name).is_file() for name in ("prewrite-plan.md", "prewrite-plan.json"))
    prewrite_manifest: object = {}
    if requires_prewrite_policy:
        if not prewrite_files_available:
            errors.append("schema 2+ campaign requires prewrite-plan.md and prewrite-plan.json")
        else:
            try:
                prewrite_manifest = json.loads((workspace / "prewrite-plan.json").read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"invalid pre-write manifest JSON: {exc}")
    prewrite_policy = cfg.get("prewrite_plan_policy", {})
    if requires_prewrite_policy:
        if not isinstance(prewrite_policy, dict) or prewrite_policy.get("mode") != "CAMPAIGN_G_PREWRITE_EVIDENCE_AND_PLAN": errors.append("pre-write plan must be controlled by campaign G without replacing writer research")
        elif prewrite_policy.get("required_before_article_dispatch") is not True: errors.append("pre-write plan must precede article dispatch")
        elif prewrite_policy.get("owner_confirmation_required") is not True: errors.append("pre-write plan requires owner confirmation")
        elif prewrite_policy.get("report_path") != "prewrite-plan.md": errors.append("pre-write report path must be prewrite-plan.md")
        elif prewrite_policy.get("manifest_path") != "prewrite-plan.json": errors.append("pre-write manifest path must be prewrite-plan.json")
        elif prewrite_policy.get("confirmation_path") != "confirmation.md": errors.append("pre-write confirmation path must be confirmation.md")
        elif prewrite_policy.get("requirements_contract_path") != "requirements-contract.md": errors.append("pre-write requirements contract path must be requirements-contract.md")
        elif prewrite_policy.get("requires_per_article_plan") is not True: errors.append("pre-write plan requires one plan per article")
        elif prewrite_policy.get("article_plan_sections") != required_plan_sections: errors.append("pre-write plan sections are incomplete or reordered")
        elif prewrite_policy.get("campaign_summary_sections") != required_summary_sections: errors.append("pre-write campaign-summary sections are incomplete or reordered")
        elif prewrite_policy.get("allow_article_roles_before_confirmation") is not False: errors.append("article roles may not start before owner confirms the pre-write plan")
        elif prewrite_policy.get("standalone_article_research_role") != "PROHIBITED": errors.append("pre-write planning must not create a second article-research role")
        elif prewrite_policy.get("writer_research_remains_required") is not True: errors.append("pre-write plan cannot replace writer integrated research")
        elif requires_artifact_optimization_policy and prewrite_policy.get("canonical_source") != "prewrite-plan.json": errors.append("schema 2.4 pre-write source must be canonical JSON")
        elif requires_artifact_optimization_policy and prewrite_policy.get("owner_view_mode") != "DETERMINISTIC_RENDERED_READ_ONLY": errors.append("schema 2.4 pre-write owner view must be deterministically rendered")
        elif requires_artifact_optimization_policy and prewrite_policy.get("manual_duplicate_entry") != "PROHIBITED": errors.append("schema 2.4 pre-write duplicate manual entry must be prohibited")
        elif requires_artifact_optimization_policy and prewrite_policy.get("sync_command") != "sync-prewrite-plan": errors.append("schema 2.4 pre-write synchronization command is invalid")
    if requires_artifact_optimization_policy and cfg.get("artifact_optimization_policy") != ARTIFACT_OPTIMIZATION_POLICY_2_4:
        errors.append("schema 2.4 artifact optimization policy is missing or changed")
    if requires_prewrite_policy and not prewrite_files_available:
        print("CHECK_FAILED\n" + "\n".join(errors)); return 1
    scope = cfg.get("platform_scope", {})
    if scope.get("source") != "OWNER_SELECTION_LOCK_ONLY": errors.append("platform scope source must be OWNER_SELECTION_LOCK_ONLY")
    if not isinstance(scope.get("allowed_pairs"), list): errors.append("allowed_pairs must be a list")
    if scope.get("automatic_discovery_or_expansion") is not False: errors.append("automatic platform expansion must be false")
    matching_policy = cfg.get("platform_matching_policy", {})
    if not isinstance(matching_policy, dict) or matching_policy.get("mode") != "VISIBLE_SUBAGENT_RESEARCH_THEN_OWNER_LOCK": errors.append("platform matching must use a visible subagent before owner lock")
    elif matching_policy.get("researcher_role") != MATCHING_ROLE or matching_policy.get("reusable") is not True: errors.append("platform matching requires one reusable visible matching researcher")
    elif matching_policy.get("candidate_universe") != "OWNER_SOURCE_ARTIFACT_ONLY": errors.append("platform matching candidates must come only from owner source artifacts")
    elif matching_policy.get("main_controller_may_select_or_rank") is not False or matching_policy.get("proposal_may_write_allowed_pairs") is not False: errors.append("G and matching proposal may not freeze platform selections")
    elif matching_policy.get("owner_confirmation_required_before_lock") is not True or not str(matching_policy.get("proposal_path", "")).strip(): errors.append("platform matching requires owner confirmation and a proposal path")
    selection_receipts: list[dict] = []; matching_proposals: list[dict] = []
    locked = str(cfg.get("scope_lock", {}).get("status", "")).upper() in {"LOCKED", "CONFIRMED"}
    if locked and scope.get("allowed_pairs"):
        selection = scope.get("selection_lock", {})
        if not isinstance(selection, dict) or selection.get("mode") != "OWNER_SOURCE_RECEIPTS_ONLY": errors.append("locked platform scope requires OWNER_SOURCE_RECEIPTS_ONLY selection lock")
        elif selection.get("internal_candidates_may_be_selected") is not False or selection.get("eligibility_evidence_may_select_platform") is not False: errors.append("internal candidates and eligibility evidence may not select platforms")
        elif selection.get("on_missing_receipt") != "OWNER_DECISION_REQUIRED": errors.append("missing platform receipt must require owner decision")
        else:
            lock_name = str(selection.get("path", "")).strip()
            root = workspace.resolve(); lock_path = (workspace / lock_name).resolve()
            if not lock_name or lock_path == root or root not in lock_path.parents or not lock_path.is_file(): errors.append("owner platform selection lock file is missing or outside workspace")
            elif lock_path.name == "campaign.json": errors.append("campaign.json cannot be an owner platform selection source")
            elif selection.get("sha256") != sha256_file(lock_path): errors.append("owner platform selection lock hash does not match")
            else:
                try:
                    lock = json.loads(lock_path.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError) as exc:
                    errors.append(f"invalid owner platform selection lock: {exc}"); lock = {}
                if not isinstance(lock, dict):
                    errors.append("owner platform selection lock must be an object"); lock = {}
                artifacts = lock.get("source_artifacts", []) if isinstance(lock, dict) else []
                selection_receipts = lock.get("pair_receipts", []) if isinstance(lock, dict) else []
                matching_reference = lock.get("matching_proposal", {}) if isinstance(lock, dict) else {}
                if lock.get("campaign_id") != cfg.get("campaign_id") or lock.get("status") != "OWNER_CONFIRMED": errors.append("owner platform selection lock must be OWNER_CONFIRMED for this campaign")
                if not isinstance(artifacts, list) or not artifacts: errors.append("owner platform selection lock needs source artifacts")
                if not isinstance(selection_receipts, list) or not selection_receipts: errors.append("owner platform selection lock needs pair receipts")
                artifact_by_id = {str(item.get("source_id", "")).strip(): item for item in artifacts if isinstance(item, dict)}
                if len(artifact_by_id) != len(artifacts) or not all(artifact_by_id): errors.append("owner selection source artifacts need unique source_id values")
                for source_id, artifact in artifact_by_id.items():
                    source_path = (workspace / str(artifact.get("path", "")).strip()).resolve()
                    if artifact.get("source_type") not in OWNER_SOURCE_TYPES: errors.append(f"owner selection source {source_id}: source_type must be owner-originated")
                    elif source_path == root or root not in source_path.parents or not source_path.is_file(): errors.append(f"owner selection source {source_id}: source file is missing or outside workspace")
                    elif source_path.name in {"campaign.json", "state.json", "owner-platform-selection.json"}: errors.append(f"owner selection source {source_id}: workflow configuration cannot select a platform")
                    elif artifact.get("sha256") != sha256_file(source_path): errors.append(f"owner selection source {source_id}: source hash does not match")
                proposal_name = str(matching_reference.get("path", "")).strip() if isinstance(matching_reference, dict) else ""
                proposal_path = (workspace / proposal_name).resolve()
                if not isinstance(matching_reference, dict) or matching_reference.get("researcher_role") != MATCHING_ROLE or not str(matching_reference.get("task_id", "")).strip(): errors.append("owner selection lock needs a visible matching-researcher proposal reference")
                elif proposal_name != matching_policy.get("proposal_path") or proposal_path == root or root not in proposal_path.parents or not proposal_path.is_file(): errors.append("matching proposal file is missing, outside workspace, or differs from policy")
                elif matching_reference.get("sha256") != sha256_file(proposal_path): errors.append("matching proposal hash does not match")
                else:
                    try:
                        proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError) as exc:
                        errors.append(f"invalid platform matching proposal: {exc}"); proposal = {}
                    if not isinstance(proposal, dict): errors.append("platform matching proposal must be an object"); proposal = {}
                    matching_proposals = proposal.get("proposals", []) if isinstance(proposal, dict) else []
                    if proposal.get("campaign_id") != cfg.get("campaign_id") or proposal.get("researcher_role") != MATCHING_ROLE or proposal.get("status") != "RECOMMENDED_PENDING_OWNER_CONFIRMATION": errors.append("platform matching proposal has invalid campaign, role, or status")
                    if not isinstance(matching_proposals, list) or not matching_proposals: errors.append("platform matching proposal needs recommendations")
                    for item in matching_proposals if isinstance(matching_proposals, list) else []:
                        if not isinstance(item, dict): errors.append("platform matching recommendation must be an object"); continue
                        required = ("article_id", "language", "market", "platform", "candidate_source_id", "candidate_locator", "rationale", "eligibility_evidence_path")
                        if any(not str(item.get(field, "")).strip() for field in required): errors.append("platform matching recommendation has missing required fields")
                        if item.get("candidate_source_id") not in artifact_by_id: errors.append("platform matching recommendation references an unknown owner source")
                for receipt in selection_receipts if isinstance(selection_receipts, list) else []:
                    if not isinstance(receipt, dict): errors.append("owner platform selection receipt must be an object"); continue
                    required = ("article_id", "platform", "account", "source_id", "source_locator", "platform_source_literal", "account_confirmation_literal", "owner_confirmation_id")
                    if any(not str(receipt.get(field, "")).strip() for field in required): errors.append("owner platform selection receipt has missing required fields")
                    if receipt.get("source_id") not in artifact_by_id: errors.append("owner platform selection receipt references an unknown source")
                    if receipt.get("status") != "EXPLICITLY_CONFIRMED": errors.append("owner platform selection receipt must be EXPLICITLY_CONFIRMED")
    assignment = cfg.get("article_platform_assignment", {})
    if assignment.get("mode") != "ONE_ARTICLE_ONE_DISTINCT_PLATFORM": errors.append("article-platform assignment mode must be ONE_ARTICLE_ONE_DISTINCT_PLATFORM")
    if assignment.get("required_before_editorial_dispatch") is not True: errors.append("article-platform assignment must be required before editorial dispatch")
    if assignment.get("platform_reuse_across_articles") != "PROHIBITED": errors.append("a platform may not be reused across articles")
    if assignment.get("pair_reuse_across_articles") != "PROHIBITED": errors.append("a platform/account pair may not be reused across articles")
    assignments = assignment.get("assignments")
    if not isinstance(assignments, list): errors.append("article-platform assignments must be a list")
    articles = cfg.get("articles", [])
    if not isinstance(articles, list): errors.append("articles must be a list")
    if locked and (articles or assignments or scope.get("allowed_pairs")):
        article_ids = [str(item.get("article_id", "")).strip() for item in articles if isinstance(item, dict)]
        if not article_ids or len(article_ids) != len(articles) or len(set(article_ids)) != len(article_ids): errors.append("locked campaign articles require unique non-empty article_id values")
        if not isinstance(assignments, list) or len(assignments) != len(article_ids): errors.append("locked campaign requires exactly one article-platform assignment per article")
        elif all(isinstance(item, dict) for item in assignments):
            assigned_ids = [str(item.get("article_id", "")).strip() for item in assignments]
            platforms = [str(item.get("platform", "")).strip().casefold() for item in assignments]
            pairs = [(str(item.get("platform", "")).strip().casefold(), str(item.get("account", "")).strip().casefold()) for item in assignments]
            if set(assigned_ids) != set(article_ids) or len(set(assigned_ids)) != len(assigned_ids): errors.append("article-platform assignments must cover each article exactly once")
            if not all(platforms) or len(set(platforms)) != len(platforms): errors.append("each article must use a distinct non-empty platform")
            if not all(platform and account for platform, account in pairs) or len(set(pairs)) != len(pairs): errors.append("each article must use a distinct non-empty platform/account pair")
            allowed = {(str(item.get("platform", "")).strip().casefold(), str(item.get("account", "")).strip().casefold()) for item in scope.get("allowed_pairs", []) if isinstance(item, dict)}
            receipt_pairs = {(str(item.get("platform", "")).strip().casefold(), str(item.get("account", "")).strip().casefold()) for item in selection_receipts if isinstance(item, dict)}
            receipt_rows = {(str(item.get("article_id", "")).strip(), str(item.get("platform", "")).strip().casefold(), str(item.get("account", "")).strip().casefold()) for item in selection_receipts if isinstance(item, dict)}
            proposal_rows = {(str(item.get("article_id", "")).strip(), str(item.get("platform", "")).strip().casefold()) for item in matching_proposals if isinstance(item, dict)}
            if len(allowed) != len(scope.get("allowed_pairs", [])): errors.append("locked article-platform campaigns require allowed_pairs objects with platform and account")
            elif set(allowed) != receipt_pairs: errors.append("allowed_pairs must exactly equal owner-confirmed selection receipts")
            elif not {(str(item.get("article_id", "")).strip(), str(item.get("platform", "")).strip().casefold(), str(item.get("account", "")).strip().casefold()) for item in assignments} <= receipt_rows: errors.append("every article assignment needs its matching owner-confirmed selection receipt")
            elif not {(str(item.get("article_id", "")).strip(), str(item.get("platform", "")).strip().casefold()) for item in assignments} <= proposal_rows: errors.append("every article assignment must preserve the visible matching-researcher platform recommendation")
            elif not set(pairs) <= allowed: errors.append("each article assignment must exactly match a user-supplied allowed platform/account pair")
        else: errors.append("article-platform assignments must contain objects")
    locale = cfg.get("locale_platform_validation", {})
    if not isinstance(locale, dict) or locale.get("mode") != "ARTICLE_LANGUAGE_MARKET_PLATFORM_EVIDENCE": errors.append("locale-platform validation mode must be ARTICLE_LANGUAGE_MARKET_PLATFORM_EVIDENCE")
    elif locale.get("required_before_editorial_dispatch") is not True: errors.append("locale-platform validation must be required before editorial dispatch")
    elif locale.get("article_language_source") != "USER_CONFIRMED_ARTICLE_LANGUAGE_ONLY": errors.append("article language must come only from user-confirmed article language")
    elif locale.get("platform_language_role") != "ELIGIBILITY_ONLY_NEVER_REWRITE_LANGUAGE": errors.append("platform language may only determine eligibility, never rewrite article language")
    locale_rows = locale.get("rows") if isinstance(locale, dict) else None
    if not isinstance(locale_rows, list): errors.append("locale-platform validation rows must be a list")
    if locked and (articles or assignments or scope.get("allowed_pairs")):
        if not isinstance(locale_rows, list) or len(locale_rows) != len(article_ids): errors.append("locked campaign requires one locale-platform validation row per article")
        elif not all(isinstance(item, dict) for item in locale_rows): errors.append("locale-platform validation rows must contain objects")
        else:
            article_by_id = {str(item.get("article_id", "")).strip(): item for item in articles if isinstance(item, dict)}
            assignment_by_id = {str(item.get("article_id", "")).strip(): item for item in assignments if isinstance(item, dict)}
            row_ids = [str(item.get("article_id", "")).strip() for item in locale_rows]
            if set(row_ids) != set(article_ids) or len(set(row_ids)) != len(row_ids): errors.append("locale-platform validation must cover each article exactly once")
            for row in locale_rows:
                article_id = str(row.get("article_id", "")).strip()
                article = article_by_id.get(article_id, {})
                mapped = assignment_by_id.get(article_id, {})
                language = str(article.get("language", "")).strip().casefold()
                market = str(article.get("market", "")).strip().casefold()
                supported = [str(value).strip().casefold() for value in row.get("supported_content_languages", [])] if isinstance(row.get("supported_content_languages"), list) else []
                if not language or not market: errors.append(f"article {article_id}: language and market are required for locale-platform validation")
                if str(row.get("article_language", "")).strip().casefold() != language or str(row.get("market", "")).strip().casefold() != market: errors.append(f"article {article_id}: locale validation must match the frozen article language and market")
                if str(row.get("platform", "")).strip().casefold() != str(mapped.get("platform", "")).strip().casefold() or str(row.get("account", "")).strip().casefold() != str(mapped.get("account", "")).strip().casefold(): errors.append(f"article {article_id}: locale validation must match its unique platform/account assignment")
                if not supported or language not in supported: errors.append(f"article {article_id}: LOCALE_PLATFORM_MISMATCH (platform does not support the frozen article language)")
                if not str(row.get("platform_language_evidence", "")).strip() or str(row.get("decision", "")).strip().upper() != "COMPATIBLE": errors.append(f"article {article_id}: locale-platform evidence and COMPATIBLE decision are required")
    title_policy = cfg.get("title_quality_policy", {})
    if not isinstance(title_policy, dict) or title_policy.get("mode") != "MODEL_LED_SEMANTIC_REVIEW": errors.append("title review mode must be MODEL_LED_SEMANTIC_REVIEW")
    elif title_policy.get("required_before_review") is not True: errors.append("title review must be required before review")
    elif not isinstance(title_policy.get("review_dimensions"), list) or not title_policy["review_dimensions"]: errors.append("title review requires non-empty review_dimensions")
    elif not isinstance(title_policy.get("heuristics"), dict) or title_policy["heuristics"].get("non_blocking") is not True: errors.append("title heuristics must be explicitly non-blocking")
    if requires_content_value_policy:
        errors.extend(content_value_policy_errors(cfg.get("content_value_policy"), required_cta=requires_required_cta_policy))
        quality_policy = cfg.get("quality_policy")
        expected_quality_policy = {
            "aitdk_local_reference": "required",
            "plugin_scan": "best_effort_non_blocking",
            "final_prepublication_target": "visual-payload.html",
        }
        if not isinstance(quality_policy, dict) or any(quality_policy.get(key) != value for key, value in expected_quality_policy.items()):
            errors.append("schema 2.1+ campaign requires the standard local quality policy")
    keyword_policy = cfg.get("keyword_research_policy", {})
    if not isinstance(keyword_policy, dict) or keyword_policy.get("mode") != "PRE_DRAFT_LONG_TAIL_AND_REGIONAL_SERP": errors.append("keyword research mode must be PRE_DRAFT_LONG_TAIL_AND_REGIONAL_SERP")
    elif requires_prewrite_policy and keyword_policy.get("required_after_owner_prewrite_confirmation_before_drafting") is not True: errors.append("writer keyword research must follow plan confirmation and precede drafting")
    elif not requires_prewrite_policy and keyword_policy.get("required_before_confirmation_and_drafting") is not True: errors.append("legacy keyword research must precede confirmation and drafting")
    elif keyword_policy.get("creative_angle_is_not_keyword_evidence") is not True: errors.append("creative angle cannot be keyword evidence")
    elif keyword_policy.get("variant_priority_order") != PRIORITY: errors.append("keyword research variant priority order is invalid")
    elif keyword_policy.get("english_multi_article_intents_must_be_distinct") is not True: errors.append("English multi-article intents must be distinct")
    elif keyword_policy.get("regional_serp_variants_required_for_every_target_language") is not True: errors.append("regional SERP variants are required for every target language")
    elif keyword_policy.get("model_translation_fallback_requires_independent_regional_serp_checks") != 2: errors.append("model translation fallback requires two regional SERP checks")
    style_policy = cfg.get("platform_style_research_policy", {})
    if not isinstance(style_policy, dict) or style_policy.get("mode") != "IN_SCOPE_READONLY_DUAL_PROFILE": errors.append("platform style research mode must be IN_SCOPE_READONLY_DUAL_PROFILE")
    elif style_policy.get("attempt_before_drafting") is not True: errors.append("platform style research must be attempted before drafting")
    elif style_policy.get("in_scope_platforms_only") is not True: errors.append("platform style research must stay in scope")
    elif style_policy.get("sample_shortage") != "UNVERIFIED_USE_CONSERVATIVE_GENERIC": errors.append("platform style sample shortage must remain non-blocking")
    elif style_policy.get("editorial_profile_is_non_binding") is not True: errors.append("platform editorial profile must remain non-binding")
    elif style_policy.get("durable_harvest_requires_public_qa_passed") is not True: errors.append("platform style harvest requires public QA")
    visual_policy = cfg.get("visual_narrative_policy", {})
    if not isinstance(visual_policy, dict) or visual_policy.get("mode") != "LEAD_MIDDLE_CLOSING_REQUIRED": errors.append("visual narrative mode must be LEAD_MIDDLE_CLOSING_REQUIRED")
    elif visual_policy.get("required_coverage_zones") != VISUAL_ZONES: errors.append("visual narrative must require LEAD, MIDDLE and CLOSING coverage")
    elif not isinstance(visual_policy.get("default_minimum_images"), int) or visual_policy["default_minimum_images"] < 3: errors.append("visual narrative default minimum must be at least three images")
    elif not isinstance(visual_policy.get("default_applies_to"), list) or not visual_policy["default_applies_to"]: errors.append("visual narrative requires article-type coverage")
    elif not isinstance(visual_policy.get("all_articles_required"), bool): errors.append("visual narrative all_articles_required must be boolean")
    elif visual_policy.get("exception_requires_owner_confirmation") is not True: errors.append("visual narrative exceptions require owner confirmation")
    if isinstance(articles, list) and requires_content_value_policy:
        for article in articles:
            if not isinstance(article, dict):
                continue
            article_id = str(article.get("article_id", "")).strip()
            if locked and not str(article.get("focus_keyword", "")).strip(): errors.append(f"article {article_id}: focus_keyword is required")
            errors.extend(content_value_article_errors(article, required_cta=requires_required_cta_policy))
    release_policy = cfg.get("release_policy", {})
    if release_policy.get("machine_external_writes_allowed") is not False: errors.append("machine external writes must be false")
    if release_policy.get("default_title_transfer_mode") not in {"SEPARATE_TITLE_FIELD", "TITLE_IN_BODY"}: errors.append("release policy needs a valid default title transfer mode")
    heading_policy = release_policy.get("heading_hierarchy_policy")
    if not isinstance(heading_policy, dict): errors.append("release policy requires a heading hierarchy policy")
    elif heading_policy.get("authority") != "PUBLIC_READER_PAGE_VISUAL_ONLY": errors.append("heading hierarchy authority must be the public reader-page visual")
    elif heading_policy.get("editor_html_or_dom") != "NOT_A_VALID_QA_SURFACE": errors.append("editor HTML or DOM cannot be a heading QA surface")
    elif heading_policy.get("local_payload_markup") != "AUTHORING_AND_COPY_SELECTION_AID_ONLY": errors.append("local payload markup must remain an authoring and copy-selection aid")
    elif heading_policy.get("public_visual_check_requires_human_accepted_url") is not True: errors.append("public visual heading check requires human acceptance and a URL")
    template = release_policy.get("visual_payload_template", {})
    if not isinstance(template, dict) or template.get("id") != "BLOG_3P_VISUAL_PAYLOAD" or template.get("version") != "2": errors.append("release payload must use BLOG_3P_VISUAL_PAYLOAD@2")
    elif template.get("rendering") != "COMPILER_ONLY" or template.get("model_authored_shell_css_js") != "PROHIBITED": errors.append("release payload must be compiler-only with no model-authored shell, CSS or JavaScript")
    orchestration = cfg.get("orchestration_policy", {})
    requires_worktree_policy = parsed_schema_version != (1, 0)
    requires_lane_bundle = parsed_schema_version not in {(1, 0), (1, 1)}
    if orchestration.get("delegation_default") != "VISIBLE_SUBAGENTS": errors.append("visible subagents must be the default delegation mode")
    if orchestration.get("visible_task_record_required") is not True: errors.append("visible task records must be required")
    if orchestration.get("invisible_cli_agent_sessions") != "PROHIBITED": errors.append("invisible CLI agent sessions must be prohibited")
    if orchestration.get("writer_reviewer_pair_mode") != "ONE_REUSABLE_PAIR_PER_ARTICLE": errors.append("each article must have one reusable writer-reviewer pair")
    if orchestration.get("cross_article_agent_reuse") != "PROHIBITED": errors.append("writer-reviewer agents may not be reused across articles")
    if orchestration.get("operations_steward_mode") != "ONE_REUSABLE_CAMPAIGN_OPERATIONS_STEWARD": errors.append("campaign operations must use one reusable visible steward")
    if orchestration.get("persistent_requirements_gatekeeper") is not True: errors.append("G must be the persistent requirements gatekeeper")
    if orchestration.get("fresh_agent_roles") != []: errors.append("public QA must not create a fresh agent")
    if orchestration.get("pair_activation") != "G_QUEUE_SUBJECT_TO_RUNTIME_CAPACITY": errors.append("article pairs must be scheduled by the G queue and runtime capacity")
    if requires_worktree_policy:
        if orchestration.get("execution_isolation") != "WORKTREE_FIRST_PER_ARTICLE": errors.append("execution isolation must be WORKTREE_FIRST_PER_ARTICLE")
        if orchestration.get("worktree_autospawn") != "CREATE_VISIBLE_PROJECT_WORKTREE_PER_READY_ARTICLE_WHEN_SUPPORTED": errors.append("ready articles must auto-spawn visible project worktrees when supported")
        if orchestration.get("worktree_fallback") != "VISIBLE_SHARED_WORKSPACE_WITH_PATH_ISOLATION": errors.append("worktree fallback must preserve visible shared-workspace path isolation")
        if orchestration.get("silent_worktree_fallback") is not False: errors.append("worktree fallback must never be silent")
    elif orchestration.get("visible_worktree_autospawn") != "AUTHORIZED_MAXIMIZE_AVAILABLE_CAPACITY": errors.append("legacy campaigns must retain visible worktree auto-spawn policy")
    if requires_lane_bundle:
        if orchestration.get("article_worktree_role_bundle") != "ONE_REUSABLE_W_R_G_LANE_PER_ARTICLE": errors.append("each article worktree must carry one reusable W-R-G lane")
        if orchestration.get("project_worktree_root_role") != "ARTICLE_LANE_GATEKEEPER": errors.append("the project worktree root must be ARTICLE_LANE_GATEKEEPER")
        if orchestration.get("campaign_gatekeeper_scope") != "GLOBAL_REQUIREMENTS_QUEUE_AND_LEDGER_ONLY": errors.append("campaign G must remain the global requirements, queue and ledger controller")
        if orchestration.get("article_public_gate_mode") != "REUSE_ARTICLE_LANE_GATEKEEPER_ONLY": errors.append("public QA must reuse the article lane gatekeeper only")
        public_qa = orchestration.get("public_qa_policy")
        if requires_streamlined_public_qa_policy:
            errors.extend(public_qa_policy_errors(public_qa))
        elif isinstance(public_qa, dict) and all(key in public_qa for key in PUBLIC_QA_POLICY_2_3):
            errors.extend(public_qa_policy_errors(public_qa))
        elif not isinstance(public_qa, dict) or public_qa.get("mode") != "REUSE_ARTICLE_LANE_GATEKEEPER_READONLY": errors.append("public QA must use the existing article lane gatekeeper in read-only mode")
        elif public_qa.get("requires_human_acceptance") is not True: errors.append("public QA requires explicit human acceptance")
        elif public_qa.get("automatic_wr_reopen") is not False: errors.append("public QA must not automatically reopen the W-R loop")
        elif public_qa.get("on_mismatch") != "OWNER_DECISION_REQUIRED": errors.append("public QA mismatch must require an owner decision")
    if orchestration.get("queue_resume_policy") != "AUTO_START_NEXT_READY_TASK_ON_SLOT_AVAILABLE": errors.append("next ready task must auto-start when a runtime slot becomes available")
    if orchestration.get("article_agent_replacement_requires_full_rehydration") is not True: errors.append("article-agent replacement must require full rehydration")
    state_orchestration = st.get("orchestration", {})
    if requires_artifact_optimization_policy:
        artifact_index = st.get("artifact_index")
        if not isinstance(artifact_index, dict):
            errors.append("state artifact_index must be an object")
        elif any(not isinstance(artifact_index.get(field), dict) for field in ("article_contexts", "review_indexes", "review_deltas")):
            errors.append("state artifact_index must track article contexts, review indexes and review deltas")
    tasks = state_orchestration.get("tasks") if isinstance(state_orchestration, dict) else None
    article_queue = state_orchestration.get("article_queue") if isinstance(state_orchestration, dict) else None
    article_agents = state_orchestration.get("article_agents") if isinstance(state_orchestration, dict) else None
    if not isinstance(tasks, list): errors.append("state orchestration tasks must be a list")
    if not isinstance(article_queue, list): errors.append("state article queue must be a list")
    if not isinstance(article_agents, dict): errors.append("state article agents must be an object")
    article_workspaces = state_orchestration.get("article_workspaces") if isinstance(state_orchestration, dict) else None
    if requires_worktree_policy and not isinstance(article_workspaces, dict): errors.append("state article workspaces must be an object")
    elif article_workspaces is not None and not isinstance(article_workspaces, dict): errors.append("state article workspaces must be an object when present")
    elif requires_lane_bundle and isinstance(article_workspaces, dict):
        configured_workspace_article_ids = {
            str(article.get("article_id", "")).strip()
            for article in articles if isinstance(article, dict) and str(article.get("article_id", "")).strip()
        }
        for article_id, workspace in article_workspaces.items():
            if article_id not in configured_workspace_article_ids:
                errors.append(f"article workspace {article_id}: article_id is not configured")
            if not isinstance(workspace, dict):
                errors.append(f"article workspace {article_id}: record must be an object"); continue
            if workspace.get("root_role") != "ARTICLE_LANE_GATEKEEPER": errors.append(f"article workspace {article_id}: root role must be ARTICLE_LANE_GATEKEEPER")
            bundle = workspace.get("role_bundle")
            if not isinstance(bundle, dict): errors.append(f"article workspace {article_id}: role_bundle must be an object")
            elif set(("lane_gatekeeper_agent", "writer_agent", "reviewer_agent")) - set(bundle): errors.append(f"article workspace {article_id}: role_bundle must declare lane G, W and R")
            elif any(not non_empty_string(bundle.get(field)) for field in ("lane_gatekeeper_agent", "writer_agent", "reviewer_agent")):
                errors.append(f"article workspace {article_id}: role_bundle agent IDs must be non-empty")
    service_agents = state_orchestration.get("service_agents") if isinstance(state_orchestration, dict) else None
    service = service_agents.get("campaign_operations") if isinstance(service_agents, dict) else None
    if not isinstance(service, dict) or service.get("role") != "CAMPAIGN_OPERATIONS_STEWARD" or service.get("reusable") is not True: errors.append("state requires one reusable campaign operations steward")
    matcher = service_agents.get("platform_matching") if isinstance(service_agents, dict) else None
    if not isinstance(matcher, dict) or matcher.get("role") != MATCHING_ROLE or matcher.get("reusable") is not True: errors.append("state requires one reusable visible platform matching researcher")
    capacity = state_orchestration.get("capacity", {}) if isinstance(state_orchestration, dict) else {}
    if not isinstance(capacity, dict): errors.append("state orchestration capacity must be an object")
    elif capacity.get("spawn_policy") != "AUTHORIZED_MAXIMIZE_AVAILABLE_CAPACITY": errors.append("state capacity must maximize visible runtime capacity")
    elif requires_worktree_policy and not isinstance(capacity.get("active_article_worktrees"), list): errors.append("state capacity must track active article worktrees")
    elif not isinstance(capacity.get("active_article_pairs"), list): errors.append("state capacity must track active article pairs")
    prewrite_state = st.get("prewrite_plan")
    if requires_prewrite_policy and not isinstance(prewrite_state, dict):
        errors.append("state pre-write plan must be an object")
    elif requires_prewrite_policy and isinstance(prewrite_state, dict):
        prewrite_status = prewrite_state.get("status")
        if prewrite_status not in PREWRITE_STATUSES:
            errors.append("state pre-write plan has an unknown status")
        if prewrite_state.get("report_path") != "prewrite-plan.md":
            errors.append("state pre-write report path must be prewrite-plan.md")
        if prewrite_state.get("manifest_path") != "prewrite-plan.json":
            errors.append("state pre-write manifest path must be prewrite-plan.json")
        article_ids = [str(article.get("article_id", "")).strip() for article in articles if isinstance(article, dict)]
        article_ids_are_valid = bool(article_ids) and len(article_ids) == len(articles) and all(article_ids) and len(set(article_ids)) == len(article_ids)
        if not isinstance(prewrite_manifest, dict):
            errors.append("pre-write manifest must be an object")
        else:
            if prewrite_manifest.get("campaign_id") != cfg.get("campaign_id"):
                errors.append("pre-write manifest campaign_id does not match")
            if prewrite_manifest.get("status") != prewrite_status:
                errors.append("pre-write manifest status does not match state")
            expected_manifest_schema = "1.3" if requires_artifact_optimization_policy else "1.2" if requires_required_cta_policy else "1.1" if requires_content_value_policy else "1.0"
            if prewrite_manifest.get("schema_version") != expected_manifest_schema:
                errors.append(f"pre-write manifest schema_version must be {expected_manifest_schema}")
            if requires_artifact_optimization_policy:
                convention = prewrite_manifest.get("artifact_convention")
                expected_convention = {
                    "canonical_source": "prewrite-plan.json",
                    "owner_view_path": "prewrite-plan.md",
                    "owner_view_mode": "DETERMINISTIC_RENDERED_READ_ONLY",
                    "manual_duplicate_entry": "PROHIBITED",
                    "writer_research_remains_required": True,
                }
                if not isinstance(convention, dict) or any(convention.get(key) != value for key, value in expected_convention.items()):
                    errors.append("pre-write manifest artifact convention is invalid")
                shared_pack = prewrite_manifest.get("shared_evidence_pack")
                if not isinstance(shared_pack, dict) or shared_pack.get("path") != "evidence/shared/campaign-evidence-pack.json" or shared_pack.get("scope") != "CAMPAIGN_READONLY_BASELINE" or shared_pack.get("does_not_replace_article_research") is not True:
                    errors.append("pre-write manifest shared evidence pack declaration is invalid")
                elif shared_pack.get("sha256") != "PENDING":
                    shared_path, shared_error = workspace_file(workspace, shared_pack.get("path"), label="shared evidence pack")
                    if shared_error:
                        errors.append(shared_error)
                    elif shared_path is not None and shared_pack.get("sha256") != sha256_file(shared_path):
                        errors.append("shared evidence pack hash does not match")
                rendered_plan = render_prewrite_plan_markdown(prewrite_manifest, sha256_file(workspace / "prewrite-plan.json"))
                if (workspace / "prewrite-plan.md").read_text(encoding="utf-8") != rendered_plan:
                    errors.append("pre-write report must be the deterministic rendering of prewrite-plan.json")
        if prewrite_status == "OWNER_PREWRITE_PLAN_CONFIRMED":
            confirmation_id = str(prewrite_state.get("owner_confirmation_id", "")).strip()
            if not confirmation_id:
                errors.append("confirmed pre-write plan requires owner_confirmation_id")
            if not article_ids_are_valid:
                errors.append("confirmed pre-write plan requires unique non-empty configured article IDs")
            if not exact_article_coverage(prewrite_state.get("article_ids"), article_ids):
                errors.append("confirmed pre-write plan must cover every configured article exactly once")
            report_path = workspace / "prewrite-plan.md"
            manifest_path = workspace / "prewrite-plan.json"
            report_hash = sha256_file(report_path)
            manifest_hash = sha256_file(manifest_path)
            if prewrite_state.get("report_sha256") != report_hash:
                errors.append("confirmed pre-write report hash does not match")
            if prewrite_state.get("manifest_sha256") != manifest_hash:
                errors.append("confirmed pre-write manifest hash does not match")
            if isinstance(prewrite_manifest, dict):
                if prewrite_manifest.get("owner_confirmation_id") != confirmation_id:
                    errors.append("pre-write manifest owner_confirmation_id does not match state")
                summary = prewrite_manifest.get("campaign_summary")
                if not isinstance(summary, dict) or any(not isinstance(summary.get(section), str) or not summary[section].strip() for section in required_summary_sections):
                    errors.append("confirmed pre-write manifest requires every campaign-summary section")
                plans = prewrite_manifest.get("article_plans")
                manifest_ids = [str(plan.get("article_id", "")).strip() for plan in plans if isinstance(plan, dict)] if isinstance(plans, list) else []
                if not isinstance(plans, list) or len(manifest_ids) != len(plans) or not exact_article_coverage(manifest_ids, article_ids):
                    errors.append("pre-write manifest must contain exactly one plan per configured article")
                else:
                    for plan in plans:
                        if not isinstance(plan, dict):
                            continue
                        for section in required_plan_sections:
                            if not isinstance(plan.get(section), str) or not plan[section].strip():
                                errors.append(f"pre-write manifest article {plan.get('article_id')}: missing {section}")
            report_text = report_path.read_text(encoding="utf-8")
            report_ids = csv_values(markdown_field(report_text, "Article IDs"))
            if markdown_field(report_text, "Status") != "OWNER_PREWRITE_PLAN_CONFIRMED":
                errors.append("pre-write report must record OWNER_PREWRITE_PLAN_CONFIRMED")
            if markdown_field(report_text, "Owner confirmation ID") != confirmation_id:
                errors.append("pre-write report confirmation ID does not match state")
            if markdown_field(report_text, "Pre-write manifest SHA-256") != manifest_hash:
                errors.append("pre-write report manifest hash does not match")
            if not exact_article_coverage(report_ids, article_ids):
                errors.append("pre-write report must name every configured article exactly once")
            confirmation_text = (workspace / "confirmation.md").read_text(encoding="utf-8")
            if markdown_field(confirmation_text, "Pre-write plan status") != "OWNER_PREWRITE_PLAN_CONFIRMED":
                errors.append("confirmation record must record OWNER_PREWRITE_PLAN_CONFIRMED")
            if markdown_field(confirmation_text, "Pre-write plan confirmation ID") != confirmation_id:
                errors.append("confirmation record ID does not match state")
            if markdown_field(confirmation_text, "Pre-write report SHA-256") != report_hash:
                errors.append("confirmation record report hash does not match")
            if markdown_field(confirmation_text, "Pre-write manifest SHA-256") != manifest_hash:
                errors.append("confirmation record manifest hash does not match")
            if not exact_article_coverage(csv_values(markdown_field(confirmation_text, "Pre-write article IDs")), article_ids):
                errors.append("confirmation record must name every configured article exactly once")
            requirements_text = (workspace / "requirements-contract.md").read_text(encoding="utf-8")
            if markdown_field(requirements_text, "Pre-write plan confirmation ID") != confirmation_id:
                errors.append("requirements contract confirmation ID does not match state")
            if markdown_field(requirements_text, "Pre-write report SHA-256") != report_hash:
                errors.append("requirements contract report hash does not match")
            if markdown_field(requirements_text, "Pre-write manifest SHA-256") != manifest_hash:
                errors.append("requirements contract manifest hash does not match")
            if not exact_article_coverage(csv_values(markdown_field(requirements_text, "Pre-write article IDs")), article_ids):
                errors.append("requirements contract must bind every configured article exactly once")
            scope_receipt = cfg.get("scope_lock", {}).get("prewrite_plan_receipt") if isinstance(cfg.get("scope_lock"), dict) else None
            if not isinstance(scope_receipt, dict):
                errors.append("scope lock must bind the confirmed pre-write plan")
            else:
                if scope_receipt.get("owner_confirmation_id") != confirmation_id:
                    errors.append("scope lock pre-write confirmation ID does not match state")
                if scope_receipt.get("report_sha256") != report_hash:
                    errors.append("scope lock pre-write report hash does not match")
                if scope_receipt.get("manifest_sha256") != manifest_hash:
                    errors.append("scope lock pre-write manifest hash does not match")
                if not exact_article_coverage(scope_receipt.get("article_ids"), article_ids):
                    errors.append("scope lock must bind every configured article exactly once")
            if st.get("phase") in {"prewrite_planning", "awaiting_owner_prewrite_confirmation"}:
                errors.append("confirmed pre-write plan must advance beyond the pre-write phase")
        elif st.get("phase") not in {"prewrite_planning", "awaiting_owner_prewrite_confirmation", "deferred", "blocked", "capacity_blocked"}:
            errors.append("unconfirmed pre-write plan cannot enter editorial phases")
        if prewrite_status != "OWNER_PREWRITE_PLAN_CONFIRMED":
            article_role_tasks = [task for task in tasks if isinstance(task, dict) and task.get("role") in ARTICLE_EXECUTION_ROLES] if isinstance(tasks, list) else []
            active_pairs = capacity.get("active_article_pairs") if isinstance(capacity, dict) else None
            active_worktrees = capacity.get("active_article_worktrees") if isinstance(capacity, dict) else None
            if article_role_tasks:
                errors.append("article roles may not start before OWNER_PREWRITE_PLAN_CONFIRMED")
            if isinstance(article_queue, list) and article_queue:
                errors.append("article queue must remain empty before OWNER_PREWRITE_PLAN_CONFIRMED")
            if isinstance(article_agents, dict) and article_agents:
                errors.append("article agents may not exist before OWNER_PREWRITE_PLAN_CONFIRMED")
            if isinstance(article_workspaces, dict) and article_workspaces:
                errors.append("article worktrees may not exist before OWNER_PREWRITE_PLAN_CONFIRMED")
            if isinstance(active_pairs, list) and active_pairs:
                errors.append("active article pairs are forbidden before OWNER_PREWRITE_PLAN_CONFIRMED")
            if isinstance(active_worktrees, list) and active_worktrees:
                errors.append("active article worktrees are forbidden before OWNER_PREWRITE_PLAN_CONFIRMED")
    if requires_streamlined_public_qa_policy:
        configured_article_ids = {
            str(article.get("article_id", "")).strip()
            for article in articles
            if isinstance(article, dict) and str(article.get("article_id", "")).strip()
        }
        errors.extend(
            publication_ledger_errors(
                st.get("publication"), article_ids=configured_article_ids, article_workspaces=article_workspaces,
                workspace=workspace,
            )
        )
        errors.extend(
            public_qa_task_errors(
                st.get("publication"), tasks=tasks, article_workspaces=article_workspaces,
            )
        )
    cross = cfg.get("cross_language_seo", {})
    if cross.get("google_trends_seed_language") != "ENGLISH_ONLY": errors.append("Google Trends seed language must be ENGLISH_ONLY")
    if cross.get("variant_priority_order") != PRIORITY: errors.append("cross-language priority order is invalid")
    if cross.get("minimum_independent_regional_serp_checks_for_fallback") != 2: errors.append("model fallback requires two independent SERP checks")
    if cross.get("status") not in {"NOT_REQUESTED", "REQUIRED", "READY", "UNVERIFIED", "OWNER_WAIVED"}: errors.append("unknown cross-language status")
    if st.get("campaign_id") != cfg.get("campaign_id"): errors.append("state campaign_id does not match")
    if st.get("phase") not in PHASES: errors.append("unknown phase")
    if errors:
        print("CHECK_FAILED\n" + "\n".join(errors)); return 1
    print("CHECK_PASSED"); return 0


def check_article_package(workspace: Path, package_path: Path) -> int:
    """Check declaration fidelity only; R retains all editorial judgment."""
    errors: list[str] = []
    try:
        cfg = json.loads((workspace / "campaign.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ARTICLE_PACKAGE_CHECK_FAILED\ninvalid campaign JSON: {exc}")
        return 1
    parsed_schema_version = parse_schema_version(cfg.get("schema_version"))
    requires_required_cta_policy = False
    requires_artifact_optimization_policy = False
    if parsed_schema_version is None:
        errors.append("campaign schema_version must use exact major.minor form")
        requires_required_cta_policy = True
    elif parsed_schema_version < (2, 1):
        print("ARTICLE_PACKAGE_CHECK_SKIPPED_LEGACY_SCHEMA")
        return 0
    else:
        requires_required_cta_policy = parsed_schema_version >= (2, 2)
        requires_artifact_optimization_policy = parsed_schema_version >= (2, 4)
        errors.extend(content_value_policy_errors(cfg.get("content_value_policy"), required_cta=requires_required_cta_policy))

    resolved_package = package_path if package_path.is_absolute() else workspace / package_path
    try:
        package = json.loads(resolved_package.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid article package JSON: {exc}")
        package = None
    articles = cfg.get("articles")
    if not isinstance(articles, list):
        errors.append("campaign articles must be a list")
    elif not isinstance(package, dict):
        errors.append("article package must be an object")
    else:
        article_id = str(package.get("article_id", "")).strip()
        matches = [article for article in articles if isinstance(article, dict) and str(article.get("article_id", "")).strip() == article_id]
        if len(matches) != 1:
            errors.append("article package article_id must match exactly one campaign article")
        else:
            errors.extend(article_package_declaration_errors(
                matches[0], package, required_cta=requires_required_cta_policy,
                package_schema="1.3" if requires_artifact_optimization_policy else None,
            ))
            if requires_artifact_optimization_policy:
                errors.extend(package_artifact_source_errors(package))
    if errors:
        print("ARTICLE_PACKAGE_CHECK_FAILED\n" + "\n".join(errors))
        return 1
    print("ARTICLE_PACKAGE_CHECK_PASSED")
    return 0


def check_public_return_receipt(workspace: Path, receipt_path: Path, package_path: Path) -> int:
    """Validate the human return boundary without fetching or changing a public page."""
    errors: list[str] = []
    try:
        cfg = json.loads((workspace / "campaign.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"PUBLIC_RETURN_RECEIPT_CHECK_FAILED\ninvalid campaign JSON: {exc}")
        return 1
    parsed_schema_version = parse_schema_version(cfg.get("schema_version"))
    if parsed_schema_version is None:
        errors.append("campaign schema_version must use exact major.minor form")
        parsed_schema_version = (2, 4)
    if parsed_schema_version < (2, 3):
        print("PUBLIC_RETURN_RECEIPT_CHECK_SKIPPED_LEGACY_SCHEMA")
        return 0
    orchestration = cfg.get("orchestration_policy", {})
    errors.extend(public_qa_policy_errors(orchestration.get("public_qa_policy") if isinstance(orchestration, dict) else None))
    resolved_package = package_path if package_path.is_absolute() else workspace / package_path
    resolved_receipt = receipt_path if receipt_path.is_absolute() else workspace / receipt_path
    try:
        package = json.loads(resolved_package.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid article package JSON: {exc}")
        package = None
    try:
        receipt = json.loads(resolved_receipt.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid public return receipt JSON: {exc}")
        receipt = None
    article_id = str(package.get("article_id", "")).strip() if isinstance(package, dict) else ""
    articles = cfg.get("articles")
    matches = [article for article in articles if isinstance(article, dict) and str(article.get("article_id", "")).strip() == article_id] if isinstance(articles, list) else []
    if len(matches) != 1:
        errors.append("article package article_id must match exactly one campaign article")
    elif isinstance(package, dict):
        errors.extend(article_package_declaration_errors(
            matches[0], package, required_cta=True,
            package_schema="1.3" if parsed_schema_version >= (2, 4) else None,
        ))
        if parsed_schema_version >= (2, 4):
            errors.extend(package_artifact_source_errors(package))
    errors.extend(public_return_receipt_errors(receipt, expected_article_id=article_id or None))
    if errors:
        print("PUBLIC_RETURN_RECEIPT_CHECK_FAILED\n" + "\n".join(errors))
        return 1
    print("PUBLIC_RETURN_RECEIPT_CHECK_PASSED")
    return 0


def check_handoff_manifest(workspace: Path, manifest_path: Path, package_path: Path) -> int:
    """Check the compiler-generated handoff receipt that G consumes after R's final visual delta."""
    resolved_manifest = manifest_path if manifest_path.is_absolute() else workspace / manifest_path
    resolved_package = package_path if package_path.is_absolute() else workspace / package_path
    manifest, manifest_error = json_object_file(resolved_manifest, label="handoff manifest")
    package, package_error = json_object_file(resolved_package, label="article package")
    errors: list[str] = [error for error in (manifest_error, package_error) if error]
    if manifest is None or package is None:
        print("HANDOFF_MANIFEST_CHECK_FAILED\n" + "\n".join(errors))
        return 1
    if manifest.get("schema_version") != "1.0":
        errors.append("handoff manifest schema_version must be 1.0")
    if package.get("schema_version") != "1.3":
        errors.append("handoff manifest requires article package schema_version 1.3")
    errors.extend(package_artifact_source_errors(package))
    article_id = str(package.get("article_id", "")).strip()
    if manifest.get("article_id") != article_id:
        errors.append("handoff manifest article_id does not match article package")
    if manifest.get("purpose") != "DERIVED_HANDOFF_ARTIFACT_AND_HASH_INDEX":
        errors.append("handoff manifest purpose is invalid")

    review_errors, review_index, registered_reviewer_id = handoff_review_approval_errors(workspace, article_id)
    errors.extend(review_errors)
    review_index_path = workspace / "reviews/review-index.json"
    review_index_sha256 = sha256_file(review_index_path) if review_index_path.is_file() else None

    def verify_artifact(key: str, expected_path: str | None = None) -> None:
        record = manifest.get(key)
        if not isinstance(record, dict):
            errors.append(f"handoff manifest requires {key}")
            return
        if expected_path is not None and record.get("path") != expected_path:
            errors.append(f"handoff manifest {key} path does not match the canonical declaration")
        artifact, artifact_error = workspace_file(workspace, record.get("path"), label=f"handoff manifest {key}")
        if artifact_error:
            errors.append(artifact_error)
        elif artifact is not None and record.get("sha256") != sha256_file(artifact):
            errors.append(f"handoff manifest {key} sha256 does not match")

    verify_artifact("visual_payload", "handoff/visual-payload.html")
    verify_artifact("metadata", "canonical/metadata.json")
    try:
        expected_package_path = relative_path(workspace, resolved_package)
    except ValueError:
        expected_package_path = None
        errors.append("handoff article package must stay inside workspace")
    verify_artifact("article_package", expected_package_path)
    artifact_sources = package.get("artifact_sources")
    expected_visual_path = None
    if isinstance(artifact_sources, dict) and isinstance(artifact_sources.get("visual_manifest"), dict):
        expected_visual_path = artifact_sources["visual_manifest"].get("path")
    verify_artifact("visual_manifest", expected_visual_path if isinstance(expected_visual_path, str) else None)
    visual_record = manifest.get("visual_manifest")
    if isinstance(artifact_sources, dict) and isinstance(artifact_sources.get("visual_manifest"), dict) and isinstance(visual_record, dict):
        if visual_record.get("sha256") != artifact_sources["visual_manifest"].get("sha256"):
            errors.append("handoff manifest visual_manifest sha256 does not match article package")
    if isinstance(artifact_sources, dict):
        evidence_source = artifact_sources.get("evidence_pack")
        if isinstance(evidence_source, dict):
            evidence_pack, evidence_error = workspace_file(workspace, evidence_source.get("path"), label="handoff evidence pack")
            if evidence_error:
                errors.append(evidence_error)
            elif evidence_pack is not None and evidence_source.get("sha256") != sha256_file(evidence_pack):
                errors.append("handoff evidence pack sha256 does not match article package")
        canonical_path, canonical_error = workspace_file(workspace, package.get("canonical_path"), label="handoff canonical article")
        if canonical_error:
            errors.append(canonical_error)
        elif canonical_path is not None and package.get("canonical_sha256") != sha256_file(canonical_path):
            errors.append("handoff canonical article sha256 does not match article package")
    visual_payload, visual_payload_error = workspace_file(workspace, "handoff/visual-payload.html", label="handoff visual payload")
    visual_payload_sha256 = sha256_file(visual_payload) if visual_payload is not None and not visual_payload_error else None
    visual_manifest_sha256 = None
    if isinstance(artifact_sources, dict) and isinstance(artifact_sources.get("visual_manifest"), dict):
        visual_manifest_sha256 = artifact_sources["visual_manifest"].get("sha256")
    package_delta = package.get("final_visual_payload_delta")
    errors.extend(final_visual_payload_delta_errors(
        package_delta, require_approved=True, workspace=workspace,
        expected_visual_manifest_sha256=visual_manifest_sha256 if isinstance(visual_manifest_sha256, str) else None,
        expected_visual_payload_sha256=visual_payload_sha256,
        expected_review_index_sha256=review_index_sha256,
    ))
    expected_delta_fields = (
        "reviewer_result", "report_path", "report_sha256", "reviewer_agent_id",
        "review_index_sha256", "reviewed_visual_manifest_sha256", "reviewed_visual_payload_sha256",
    )
    final_delta = manifest.get("final_visual_payload_delta")
    if not isinstance(final_delta, dict):
        errors.append("handoff manifest requires final_visual_payload_delta")
    elif not isinstance(package_delta, dict) or any(final_delta.get(field) != package_delta.get(field) for field in expected_delta_fields):
        errors.append("handoff manifest final visual payload delta does not match article package")
    if isinstance(package_delta, dict) and registered_reviewer_id is not None:
        if package_delta.get("reviewer_agent_id") != registered_reviewer_id:
            errors.append("final visual payload delta reviewer_agent_id must match the registered article reviewer")
        elif non_empty_string(package_delta.get("report_path")):
            errors.extend(reviewer_task_receipt_errors(
                workspace, article_id=article_id, reviewer_agent_id=registered_reviewer_id,
                workflow_stage="VISUAL_PAYLOAD_DELTA", result=FINAL_VISUAL_DELTA_RESULT,
                report_path=package_delta["report_path"],
            ))
    if isinstance(review_index, dict) and isinstance(package_delta, dict):
        visual_index = review_index.get("last_delta")
        if not isinstance(visual_index, dict):
            errors.append("handoff review index requires the approved final visual delta")
        else:
            if visual_index.get("review_scope") != "R_VISUAL_DELTA" or visual_index.get("status") != FINAL_VISUAL_DELTA_RESULT:
                errors.append("handoff review index final delta must be an approved R_VISUAL_DELTA")
            for field in (
                "report_path", "report_sha256", "reviewer_agent_id",
                "reviewed_visual_manifest_sha256", "reviewed_visual_payload_sha256",
            ):
                if visual_index.get(field) != package_delta.get(field):
                    errors.append(f"handoff review index final delta {field} does not match article package")
    gate_input = manifest.get("gate_input")
    if not isinstance(gate_input, dict):
        errors.append("handoff manifest requires gate_input")
    else:
        trace_path, trace_error = workspace_file(workspace, gate_input.get("requirements_traceability_path"), label="handoff manifest requirements traceability")
        if trace_error:
            errors.append(trace_error)
        elif trace_path is not None and gate_input.get("requirements_traceability_sha256") != sha256_file(trace_path):
            errors.append("handoff manifest requirements traceability sha256 does not match")
        if gate_input.get("gate_mode") != "MANIFEST_HASH_AND_REQUIREMENTS_ONLY":
            errors.append("handoff manifest gate mode is invalid")
    if errors:
        print("HANDOFF_MANIFEST_CHECK_FAILED\n" + "\n".join(errors))
        return 1
    print("HANDOFF_MANIFEST_CHECK_PASSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(); sub = parser.add_subparsers(dest="command", required=True)
    p_init = sub.add_parser("init"); p_init.add_argument("--workspace", type=Path, required=True); p_init.add_argument("--campaign-id", required=True)
    p_check = sub.add_parser("check"); p_check.add_argument("--workspace", type=Path, required=True)
    p_sync = sub.add_parser("sync-prewrite-plan"); p_sync.add_argument("--workspace", type=Path, required=True)
    p_render = sub.add_parser("render-prewrite-plan"); p_render.add_argument("--manifest", type=Path, required=True); p_render.add_argument("--output", type=Path, required=True)
    p_context = sub.add_parser("build-article-context"); p_context.add_argument("--workspace", type=Path, required=True); p_context.add_argument("--article-id", required=True); p_context.add_argument("--output", type=Path, required=True)
    p_context_check = sub.add_parser("check-article-context"); p_context_check.add_argument("--workspace", type=Path, required=True); p_context_check.add_argument("--context", type=Path, required=True)
    p_index = sub.add_parser("build-review-index"); p_index.add_argument("--workspace", type=Path, required=True); p_index.add_argument("--article-contract", type=Path, required=True); p_index.add_argument("--output", type=Path, required=True); p_index.add_argument("--canonical", type=Path)
    p_index_check = sub.add_parser("check-review-index"); p_index_check.add_argument("--workspace", type=Path, required=True); p_index_check.add_argument("--index", type=Path, required=True)
    p_delta = sub.add_parser("check-review-delta"); p_delta.add_argument("--workspace", type=Path, required=True); p_delta.add_argument("--delta", type=Path, required=True)
    p_package = sub.add_parser("check-article-package"); p_package.add_argument("--workspace", type=Path, required=True); p_package.add_argument("--package", type=Path, required=True)
    p_return = sub.add_parser("check-public-return-receipt"); p_return.add_argument("--workspace", type=Path, required=True); p_return.add_argument("--receipt", type=Path, required=True); p_return.add_argument("--article-package", type=Path, required=True)
    p_handoff = sub.add_parser("check-handoff-manifest"); p_handoff.add_argument("--workspace", type=Path, required=True); p_handoff.add_argument("--manifest", type=Path, required=True); p_handoff.add_argument("--article-package", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "init":
        return init(args.workspace, args.campaign_id)
    if args.command == "check":
        return check(args.workspace)
    if args.command == "sync-prewrite-plan":
        return sync_prewrite_plan(args.workspace)
    if args.command == "render-prewrite-plan":
        return render_prewrite_plan(args.manifest, args.output)
    if args.command == "build-article-context":
        output = args.output if args.output.is_absolute() else args.workspace / args.output
        return build_article_context(args.workspace, args.article_id, output)
    if args.command == "check-article-context":
        context = args.context if args.context.is_absolute() else args.workspace / args.context
        return check_article_context(args.workspace, context)
    if args.command == "build-review-index":
        context = args.article_contract if args.article_contract.is_absolute() else args.workspace / args.article_contract
        output = args.output if args.output.is_absolute() else args.workspace / args.output
        canonical = args.canonical if args.canonical is None or args.canonical.is_absolute() else args.workspace / args.canonical
        return build_review_index(args.workspace, context, output, canonical)
    if args.command == "check-review-index":
        index = args.index if args.index.is_absolute() else args.workspace / args.index
        return check_review_index(args.workspace, index)
    if args.command == "check-review-delta":
        delta = args.delta if args.delta.is_absolute() else args.workspace / args.delta
        return check_review_delta(args.workspace, delta)
    if args.command == "check-article-package":
        return check_article_package(args.workspace, args.package)
    if args.command == "check-public-return-receipt":
        return check_public_return_receipt(args.workspace, args.receipt, args.article_package)
    return check_handoff_manifest(args.workspace, args.manifest, args.article_package)


if __name__ == "__main__":
    raise SystemExit(main())
