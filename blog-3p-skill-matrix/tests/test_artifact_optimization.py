#!/usr/bin/env python3
"""Regression checks for canonical manifests and compact review context."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
HARNESS_PATH = ROOT / "skills/blog-3p-harness/scripts/harnessctl.py"
BUILD_PAYLOAD = ROOT / "skills/blog-3p-human-handoff/scripts/build_visual_payload.py"
SPEC = importlib.util.spec_from_file_location("blog_3p_harnessctl", HARNESS_PATH)
assert SPEC is not None and SPEC.loader is not None
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


def article() -> dict:
    return {
        "article_id": "A1",
        "language": "en",
        "market": "US",
        "focus_keyword": "example workflow",
        "reader_value_promise": "Teach the reader the workflow before the secondary recommendation.",
        "cta": {
            "mode": "SECONDARY_RECOMMENDATION",
            "anchor_text": "Try Example Product",
            "product_name": "Example Product",
            "product_destination_url": "https://example.com/product",
            "product_evidence_path": "research/evidence-pack.json#/claims/example-product",
            "reader_task_relevance": "It is a relevant option after the standalone answer.",
            "relationship_disclosure": "NOT_APPLICABLE",
        },
    }


def package_for(item: dict, visual_sha: str) -> dict:
    return {
        "schema_version": "1.3",
        "article_id": item["article_id"],
        "canonical_path": "canonical/article.md",
        "canonical_sha256": "a" * 64,
        "title": "Example workflow",
        "seo_title": "Example workflow guide",
        "tags": ["example"],
        "description": "A useful example workflow.",
        "meta_description": "A useful example workflow.",
        "focus_keyword": item["focus_keyword"],
        "reader_value_promise": item["reader_value_promise"],
        "cta": copy.deepcopy(item["cta"]),
        "artifact_sources": {
            "evidence_pack": {"path": "research/evidence-pack.json", "sha256": "PENDING", "role": "ARTICLE_CLAIM_AND_SEO_DECISION_INDEX"},
            "visual_manifest": {"path": "canonical/visual-manifest.json", "sha256": visual_sha, "role": "SINGLE_SOURCE_FOR_IMAGE_ASSETS_ALT_CAPTIONS_AND_PLACEMENT"},
            "handoff_manifest": {"path": "handoff/handoff-manifest.json", "sha256": "PENDING_AFTER_PAYLOAD", "role": "DERIVED_HANDOFF_ARTIFACT_AND_HASH_INDEX"},
            "manual_retelling": "PROHIBITED",
        },
        "final_visual_payload_delta": {
            "precondition": "TEXT_AND_SEO_FIELDS_STABLE",
            "scope": "VISUAL_MANIFEST_ASSETS_AND_COMPILED_PAYLOAD_ONLY",
            "reviewer_result": "PENDING",
            "report_path": "reviews/visual-payload-delta-1.md",
            "report_sha256": None,
            "reviewer_agent_id": None,
            "review_index_sha256": None,
            "reviewed_visual_manifest_sha256": None,
            "reviewed_visual_payload_sha256": None,
        },
    }


def record_research_and_full_approvals(workspace: Path, index_path: Path, canonical: Path, evidence_pack: Path) -> dict:
    """Create compact R receipts used only by hand-off regression fixtures."""
    research_report = workspace / "reviews/research-review-1.md"
    full_report = workspace / "reviews/review-1.md"
    research_report.write_text("R: research approved.\n", encoding="utf-8")
    full_report.write_text("R: full review approved.\n", encoding="utf-8")
    state_path = workspace / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["orchestration"]["article_workspaces"] = {
        "A1": {
            "root_role": "ARTICLE_LANE_GATEKEEPER",
            "role_bundle": {
                "lane_gatekeeper_agent": "G-A1",
                "writer_agent": "W-A1",
                "reviewer_agent": "R-A1",
            },
        },
    }
    state["orchestration"]["tasks"] = [
        {
            "article_id": "A1", "role": "ARTICLE_LANGUAGE_REVIEWER", "agent_id": "R-A1",
            "workflow_stage": "RESEARCH_REVIEW", "result": "RESEARCH_APPROVED",
            "result_path": "reviews/research-review-1.md", "status": "COMPLETED",
        },
        {
            "article_id": "A1", "role": "ARTICLE_LANGUAGE_REVIEWER", "agent_id": "R-A1",
            "workflow_stage": "FULL_REVIEW", "result": "APPROVED",
            "result_path": "reviews/review-1.md", "status": "COMPLETED",
        },
    ]
    state_path.write_text(json.dumps(state), encoding="utf-8")
    index = json.loads(index_path.read_text(encoding="utf-8"))
    index["latest_research_review"] = {
        "status": "RESEARCH_APPROVED",
        "report_path": "reviews/research-review-1.md",
        "report_sha256": HARNESS.sha256_file(research_report),
        "reviewer_agent_id": "R-A1",
        "reviewed_evidence_pack_sha256": HARNESS.sha256_file(evidence_pack),
    }
    index["latest_full_review"] = {
        "status": "APPROVED",
        "report_path": "reviews/review-1.md",
        "report_sha256": HARNESS.sha256_file(full_report),
        "reviewer_agent_id": "R-A1",
        "canonical_sha256": HARNESS.sha256_file(canonical),
    }
    index_path.write_text(json.dumps(index), encoding="utf-8")
    return index


class ArtifactOptimizationTests(unittest.TestCase):
    def run_harness(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(HARNESS_PATH), *args], cwd=ROOT, text=True,
            capture_output=True, check=False,
        )

    def initialize_confirmed_workspace(self) -> tuple[tempfile.TemporaryDirectory[str], Path, dict]:
        temp_dir = tempfile.TemporaryDirectory()
        workspace = Path(temp_dir.name) / "campaign"
        initialized = self.run_harness("init", "--workspace", str(workspace), "--campaign-id", "optimized")
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        item = article()
        campaign_path = workspace / "campaign.json"
        campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
        campaign["articles"] = [item]
        campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
        manifest_path = workspace / "prewrite-plan.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["status"] = "OWNER_PREWRITE_PLAN_CONFIRMED"
        manifest["owner_confirmation_id"] = "OWNER-PLAN-001"
        manifest["campaign_summary"] = {section: f"confirmed {section}" for section in HARNESS.PREWRITE_SUMMARY_SECTIONS}
        manifest["article_plans"] = [{
            "article_id": "A1",
            "evidence_refs": ["evidence/shared/campaign-evidence-pack.json"],
            **{section: f"confirmed {section}" for section in HARNESS.PREWRITE_PLAN_SECTIONS},
        }]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        synced = self.run_harness("sync-prewrite-plan", "--workspace", str(workspace))
        self.assertEqual(synced.returncode, 0, synced.stdout + synced.stderr)
        return temp_dir, workspace, item

    def test_prewrite_json_is_canonical_and_manual_markdown_drift_fails(self) -> None:
        template = json.loads((ROOT / "templates/campaign.json").read_text(encoding="utf-8"))
        self.assertEqual(template, HARNESS.campaign("REPLACE_ME"))
        temp_dir, workspace, _ = self.initialize_confirmed_workspace()
        with temp_dir:
            checked = self.run_harness("check", "--workspace", str(workspace))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            plan = workspace / "prewrite-plan.md"
            plan.write_text(plan.read_text(encoding="utf-8") + "\nmanual drift\n", encoding="utf-8")
            drift = self.run_harness("check", "--workspace", str(workspace))
            self.assertNotEqual(drift.returncode, 0)
            self.assertIn("deterministic rendering", drift.stdout)

    def test_context_review_index_and_delta_validate_only_changed_artifacts(self) -> None:
        temp_dir, workspace, _ = self.initialize_confirmed_workspace()
        with temp_dir:
            canonical = workspace / "canonical/article.md"
            canonical.write_text("# Example\n\nBody.\n", encoding="utf-8")
            evidence_pack = workspace / "research/evidence-pack.json"
            evidence_pack.write_text(json.dumps({"schema_version": "1.0", "claims": []}), encoding="utf-8")
            context = workspace / "context/article-contract.json"
            built = self.run_harness("build-article-context", "--workspace", str(workspace), "--article-id", "A1", "--output", "context/article-contract.json")
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            self.assertEqual(self.run_harness("check-article-context", "--workspace", str(workspace), "--context", str(context)).returncode, 0)
            index = workspace / "reviews/review-index.json"
            index_built = self.run_harness("build-review-index", "--workspace", str(workspace), "--article-contract", str(context), "--output", str(index))
            self.assertEqual(index_built.returncode, 0, index_built.stdout + index_built.stderr)
            record_research_and_full_approvals(workspace, index, canonical, evidence_pack)
            self.assertEqual(self.run_harness("check-review-index", "--workspace", str(workspace), "--index", str(index)).returncode, 0)
            delta = workspace / "reviews/review-delta-1.json"
            delta.write_text(json.dumps({
                "schema_version": "1.0",
                "article_id": "A1",
                "review_index_path": "reviews/review-index.json",
                "review_index_sha256": HARNESS.sha256_file(index),
                "review_scope": "R_DELTA",
                "r_delta_attempt": 1,
                "full_review_required": False,
                "changed_artifacts": [{
                    "path": "canonical/article.md",
                    "sha256": HARNESS.sha256_file(canonical),
                    "change_kind": "CANONICAL_TEXT",
                    "affected_requirement_ids": ["REQ-SEO-001"],
                    "affected_finding_ids": ["SEO-EXAMPLE-001"],
                }],
            }), encoding="utf-8")
            validated = self.run_harness("check-review-delta", "--workspace", str(workspace), "--delta", str(delta))
            self.assertEqual(validated.returncode, 0, validated.stdout + validated.stderr)
            canonical.write_text("# Example\n\nChanged body.\n", encoding="utf-8")
            stale = self.run_harness("check-review-delta", "--workspace", str(workspace), "--delta", str(delta))
            self.assertNotEqual(stale.returncode, 0)
            self.assertIn("sha256 does not match", stale.stdout)
            campaign_path = workspace / "campaign.json"
            campaign = json.loads(campaign_path.read_text(encoding="utf-8"))
            campaign["articles"][0]["focus_keyword"] = "drifted workflow intent"
            campaign_path.write_text(json.dumps(campaign), encoding="utf-8")
            stale_build = self.run_harness(
                "build-review-index", "--workspace", str(workspace),
                "--article-contract", str(context), "--output", str(workspace / "reviews/stale-index.json"),
            )
            self.assertNotEqual(stale_build.returncode, 0)
            self.assertIn("article contract is stale or invalid", stale_build.stdout)
            stale_index = self.run_harness("check-review-index", "--workspace", str(workspace), "--index", str(index))
            self.assertNotEqual(stale_index.returncode, 0)
            self.assertIn("frozen_article no longer matches", stale_index.stdout)

    def test_compiler_builds_and_harness_checks_compact_handoff_manifest(self) -> None:
        temp_dir, workspace, item = self.initialize_confirmed_workspace()
        with temp_dir:
            canonical = workspace / "canonical/article.md"
            canonical.write_text("# Example\n", encoding="utf-8")
            (workspace / "canonical/body.html").write_text(
                '<p>Useful answer.</p><p><a href="https://example.com/product">Try Example Product</a></p>{{IMAGE_CARDS}}',
                encoding="utf-8",
            )
            (workspace / "canonical/metadata.json").write_text(
                json.dumps({"seo_title": "Example workflow guide", "tags": ["example"], "description": "A useful example workflow."}),
                encoding="utf-8",
            )
            visual_manifest = workspace / "canonical/visual-manifest.json"
            visual_manifest.write_text(json.dumps({"schema_version": "1.0", "assets": []}), encoding="utf-8")
            evidence_pack = workspace / "research/evidence-pack.json"
            evidence_pack.write_text(json.dumps({"schema_version": "1.0", "claims": []}), encoding="utf-8")
            (workspace / "requirements-traceability.md").write_text("REQ-SEO-001 -> canonical/article.md\n", encoding="utf-8")
            context = workspace / "context/article-contract.json"
            self.assertEqual(self.run_harness(
                "build-article-context", "--workspace", str(workspace), "--article-id", "A1", "--output", str(context),
            ).returncode, 0)
            index = workspace / "reviews/review-index.json"
            self.assertEqual(self.run_harness(
                "build-review-index", "--workspace", str(workspace), "--article-contract", str(context), "--output", str(index),
            ).returncode, 0)
            record_research_and_full_approvals(workspace, index, canonical, evidence_pack)
            visual_sha = HARNESS.sha256_file(visual_manifest)
            package = workspace / "article-package.json"
            package_data = package_for(item, visual_sha)
            package_data["canonical_sha256"] = HARNESS.sha256_file(canonical)
            package_data["artifact_sources"]["evidence_pack"]["sha256"] = HARNESS.sha256_file(evidence_pack)
            package.write_text(json.dumps(package_data), encoding="utf-8")
            output = workspace / "handoff/visual-payload.html"
            handoff = workspace / "handoff/handoff-manifest.json"
            initial_payload = subprocess.run(
                [
                    sys.executable, str(BUILD_PAYLOAD), "--title", "Example workflow",
                    "--body-html", str(workspace / "canonical/body.html"), "--article-package", str(package),
                    "--metadata-json", str(workspace / "canonical/metadata.json"), "--output", str(output),
                ], cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(initial_payload.returncode, 0, initial_payload.stdout + initial_payload.stderr)
            visual_report = workspace / "reviews/visual-payload-delta-1.md"
            visual_report.write_text("R: visual payload approved.\n", encoding="utf-8")
            index_data = json.loads(index.read_text(encoding="utf-8"))
            index_data["last_delta"] = {
                "review_scope": "R_VISUAL_DELTA",
                "status": "APPROVED",
                "report_path": "reviews/visual-payload-delta-1.md",
                "report_sha256": HARNESS.sha256_file(visual_report),
                "reviewer_agent_id": "R-A1",
                "reviewed_visual_manifest_sha256": visual_sha,
                "reviewed_visual_payload_sha256": HARNESS.sha256_file(output),
            }
            index.write_text(json.dumps(index_data), encoding="utf-8")
            state_path = workspace / "state.json"
            state = json.loads(state_path.read_text(encoding="utf-8"))
            state["orchestration"]["tasks"].append({
                "article_id": "A1", "role": "ARTICLE_LANGUAGE_REVIEWER", "agent_id": "R-A1",
                "workflow_stage": "VISUAL_PAYLOAD_DELTA", "result": "APPROVED",
                "result_path": "reviews/visual-payload-delta-1.md", "status": "COMPLETED",
            })
            state_path.write_text(json.dumps(state), encoding="utf-8")
            package_data = json.loads(package.read_text(encoding="utf-8"))
            package_data["final_visual_payload_delta"] = {
                "precondition": "TEXT_AND_SEO_FIELDS_STABLE",
                "scope": "VISUAL_MANIFEST_ASSETS_AND_COMPILED_PAYLOAD_ONLY",
                "reviewer_result": "APPROVED",
                "report_path": "reviews/visual-payload-delta-1.md",
                "report_sha256": HARNESS.sha256_file(visual_report),
                "reviewer_agent_id": "R-A1",
                "review_index_sha256": HARNESS.sha256_file(index),
                "reviewed_visual_manifest_sha256": visual_sha,
                "reviewed_visual_payload_sha256": HARNESS.sha256_file(output),
            }
            package.write_text(json.dumps(package_data), encoding="utf-8")
            built = subprocess.run(
                [
                    sys.executable, str(BUILD_PAYLOAD), "--title", "Example workflow",
                    "--body-html", str(workspace / "canonical/body.html"), "--article-package", str(package),
                    "--metadata-json", str(workspace / "canonical/metadata.json"), "--output", str(output),
                    "--handoff-manifest-output", str(handoff), "--workspace", str(workspace),
                    "--requirements-traceability", str(workspace / "requirements-traceability.md"),
                ], cwd=ROOT, text=True, capture_output=True, check=False,
            )
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            checked = self.run_harness("check-handoff-manifest", "--workspace", str(workspace), "--manifest", str(handoff), "--article-package", str(package))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            state_path = workspace / "state.json"
            frozen_state = state_path.read_text(encoding="utf-8")
            missing_research_task = json.loads(frozen_state)
            missing_research_task["orchestration"]["tasks"] = [
                task for task in missing_research_task["orchestration"]["tasks"]
                if task.get("workflow_stage") != "RESEARCH_REVIEW"
            ]
            state_path.write_text(json.dumps(missing_research_task), encoding="utf-8")
            no_research_gate = self.run_harness("check-handoff-manifest", "--workspace", str(workspace), "--manifest", str(handoff), "--article-package", str(package))
            self.assertNotEqual(no_research_gate.returncode, 0)
            self.assertIn("RESEARCH_REVIEW", no_research_gate.stdout)
            state_path.write_text(frozen_state, encoding="utf-8")
            frozen_package = package.read_text(encoding="utf-8")
            rejected_package = json.loads(frozen_package)
            rejected_package["final_visual_payload_delta"]["reviewer_result"] = "CHANGES_REQUIRED"
            package.write_text(json.dumps(rejected_package), encoding="utf-8")
            rejected = self.run_harness("check-article-package", "--workspace", str(workspace), "--package", str(package))
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("must be PENDING or APPROVED", rejected.stdout)
            package.write_text(frozen_package, encoding="utf-8")
            visual_report.write_text("placeholder, not the reviewed report\n", encoding="utf-8")
            tampered = self.run_harness("check-handoff-manifest", "--workspace", str(workspace), "--manifest", str(handoff), "--article-package", str(package))
            self.assertNotEqual(tampered.returncode, 0)
            self.assertIn("report_sha256 does not match", tampered.stdout)


if __name__ == "__main__":
    unittest.main()
