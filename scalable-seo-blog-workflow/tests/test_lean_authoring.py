"""A real confirmed project, one author draft, and deterministic preparation."""
from __future__ import annotations
import copy
import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib

try:
    import test_research_integrity as fixtures
except ModuleNotFoundError:
    from tests import test_research_integrity as fixtures

ROOT = Path(__file__).resolve().parents[1]
PREPARE = ROOT / "skills/blog-human-handoff/scripts/prepare_article.py"
VALIDATE = ROOT / "skills/blog-human-handoff/scripts/validate_payload.py"
SPEC = importlib.util.spec_from_file_location("lean_content_checks", PREPARE.with_name("content_integrity.py"))
assert SPEC and SPEC.loader
CHECKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKS)


def png(path, color):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    data = b"".join(b"\0" + bytes(color) * 16 for _ in range(9))
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 16, 9, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(data)) + chunk(b"IEND", b""))


@unittest.skipUnless(importlib.util.find_spec("markdown_it"), "new Markdown route requires scripts/requirements.txt")
class LeanAuthoringTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name) / "campaign"
        helper = fixtures.ResearchIntegrityTests()
        helper.prepare(self.workspace)
        self.article = self.workspace / "articles/A1"
        context = self.article / "context/article-contract.json"
        result = helper.run_harness("build-article-context", "--workspace", str(self.workspace), "--article-id", "A1", "--output", str(context))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        (self.article / "images").mkdir()
        self.images = []
        for i, zone in enumerate(["lead", "middle", "closing"], 1):
            file = self.article / f"images/{i:02d}-{zone}-example.png"
            png(file, (i * 50, 10, 20))
            self.images.append({"file": str(file.relative_to(self.article)), "alt": "Example " + zone, "caption": "An editorial example."})
        cover = self.article / "images/00-cover-example.png"
        png(cover, (10, 100, 120))
        self.front = {
            "seo_title": "Example reader workflow: prepare and inspect",
            "tags": ["example", "workflow"], "description": "Complete the example reader task.",
            "images": self.images, "cover": {"file": "images/00-cover-example.png", "alt": "Example cover"},
            "research": {"keyword_basis": "CURRENT_BRAND_SITE", "keyword_refs": ["PRODUCT"],
                "sources": [{"id": "PRODUCT", "url": "https://example.com/product", "notes": "Test-only source, not a verified real product."}],
                "claims": [{"id": "example-product", "text": "Test fixture method.", "source_refs": ["PRODUCT"]}]},
        }
        self.body = (
            "# Example reader workflow: prepare and inspect\n\n"
            "Begin with one example and inspect it.\n\n<!-- BLOG_3P_IMAGE:01 -->\n\n"
            "## Prepare the input\n\nKeep the input clear.\n\n<!-- BLOG_3P_IMAGE:02 -->\n\n"
            "## Inspect the output\n\nCheck the result.\n\n<!-- BLOG_3P_IMAGE:03 -->\n\n"
            "Try [Try Example Product](https://example.com/product).\n"
        )
        self.source = self.article / "canonical/article.md"
        self.source.parent.mkdir()
        self.write_source()

    def write_source(self):
        self.source.write_text("---json\n" + json.dumps(self.front, ensure_ascii=False) + "\n---\n" + self.body, encoding="utf-8")

    def run_prepare(self):
        return subprocess.run([sys.executable, str(PREPARE), "--workspace", str(self.workspace), "--article-id", "A1"], capture_output=True, text=True)

    def run_validate(self):
        return subprocess.run([sys.executable, str(VALIDATE), "--payload", str(self.article / "handoff/visual-payload.html"),
            "--markdown-payload", str(self.article / "handoff/visual-payload.md"),
            "--article-package", str(self.article / "article-package.json")], capture_output=True, text=True)

    def test_one_draft_generates_pair_and_internal_records_without_approval(self):
        result = self.run_prepare()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("PREPARED_NOT_QUALITY_APPROVED", result.stdout)
        package = json.loads((self.article / "article-package.json").read_text())
        self.assertEqual(package["author_source"]["path"], "canonical/article.md")
        index = json.loads((self.article / "reviews/review-index.json").read_text())
        self.assertEqual(index["latest_author_qa"]["status"], "PENDING")
        self.assertIn('<html lang="en">', (self.article / "handoff/visual-payload.html").read_text())
        valid = self.run_validate()
        self.assertEqual(valid.returncode, 0, valid.stdout + valid.stderr)
        outputs = {p.relative_to(self.article): p.read_bytes() for p in self.article.rglob("*") if p.is_file()}
        result = self.run_prepare()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(outputs, {p.relative_to(self.article): p.read_bytes() for p in self.article.rglob("*") if p.is_file()})

    def test_source_change_requires_preparation_and_derived_edit_is_rejected(self):
        self.assertEqual(self.run_prepare().returncode, 0)
        self.body = self.body.replace("Keep the input clear", "Keep one clear input")
        self.write_source()
        self.assertNotEqual(self.run_validate().returncode, 0)
        self.assertEqual(self.run_prepare().returncode, 0)
        metadata_path = self.article / "canonical/metadata.json"
        metadata = json.loads(metadata_path.read_text())
        metadata["description"] = "Independently modified projection."
        metadata_path.write_text(json.dumps(metadata))
        package_path = self.article / "article-package.json"
        package = json.loads(package_path.read_text())
        package["artifact_sources"]["metadata"]["sha256"] = CHECKS.digest(metadata_path)
        package_path.write_text(json.dumps(package))
        result = self.run_validate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("edited independently", result.stdout)

    def test_cover_does_not_replace_body_images_and_cannot_copy_lead(self):
        self.front["images"] = self.front["images"][:2]
        self.body = self.body.replace("<!-- BLOG_3P_IMAGE:03 -->", "")
        self.write_source()
        result = self.run_prepare()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.article / "article-package.json").exists())
        self.front["images"] = self.images
        self.front["cover"] = {"file": self.images[0]["file"], "alt": "Copied lead"}
        self.body += "\n<!-- BLOG_3P_IMAGE:03 -->\n"
        self.write_source()
        result = self.run_prepare()
        self.assertNotEqual(result.returncode, 0)

    def test_author_cannot_override_frozen_policy_or_insert_raw_html(self):
        self.front["link_policy"] = {"max_target_links": 100}
        self.write_source()
        self.assertNotEqual(self.run_prepare().returncode, 0)
        self.front.pop("link_policy")
        self.body += "<script>alert('not allowed')</script>\n"
        self.write_source()
        self.assertNotEqual(self.run_prepare().returncode, 0)

    def test_repair_invalidates_author_receipt_without_erasing_findings(self):
        self.assertEqual(self.run_prepare().returncode, 0)
        index_path = self.article / "reviews/review-index.json"
        index = json.loads(index_path.read_text())
        index["latest_author_qa"]["status"] = "AUTHOR_QA_READY"  # test receipt, not real approval
        index["open_findings"] = ["TEST-FINDING-001"]
        index_path.write_text(json.dumps(index))
        self.body += "\nKeep the editable source.\n"
        self.write_source()
        self.assertEqual(self.run_prepare().returncode, 0)
        index = json.loads(index_path.read_text())
        self.assertEqual(index["latest_author_qa"]["status"], "PENDING")
        self.assertEqual(index["open_findings"], ["TEST-FINDING-001"])
        self.assertTrue(index["superseded_quality_receipts"])

    def test_binding_needs_actual_author_turn_and_does_not_create_independent_review(self):
        self.assertEqual(self.run_prepare().returncode, 0)
        args = [sys.executable, str(PREPARE), "--workspace", str(self.workspace), "--article-id", "A1",
            "--bind-author-qa", "--agent-id", "TEST-W", "--note", "Test-only author conclusion after reading."]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        state_path = self.workspace / "state.json"
        state = json.loads(state_path.read_text())
        state["orchestration"]["tasks"].append({
            "article_id": "A1", "agent_id": "TEST-W", "role": "ARTICLE_WRITER",
            "workflow_stage": "AUTHOR_QA", "status": "COMPLETED",
        })
        state_path.write_text(json.dumps(state))
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        index = json.loads((self.article / "reviews/review-index.json").read_text())
        self.assertEqual(index["latest_author_qa"]["status"], "AUTHOR_QA_READY")
        self.assertEqual(index["latest_full_review"]["status"], "NOT_REQUIRED")
        self.assertEqual(fixtures.HARNESS.review_index_errors(self.workspace, self.article / "reviews/review-index.json", require_full_approved=True), [])

    def test_commonmark_lists_quotes_code_and_tables_survive_the_companion(self):
        self.body += "\n> Keep a quoted instruction.\n\n1. First item\n2. Second item\n\n"
        self.body += "Column | Detail\n--- | ---\nInput | One image pair\n\n"
        self.body += "~~~text\nLiteral code, not a product result.\n~~~\n"
        self.write_source()
        result = self.run_prepare()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        companion = (self.article / "handoff/visual-payload.md").read_text()
        self.assertIn("> Keep a quoted instruction.", companion)
        self.assertIn("Column | Detail", companion)
        self.assertIn("~~~text", companion)
        self.assertEqual(self.run_validate().returncode, 0)


class LinkAndImageChecksTests(unittest.TestCase):
    CTA = {"anchor_text": "Try Product", "product_destination_url": "https://brand.example/tool"}

    def test_all_target_occurrences_count_regardless_of_role_and_path(self):
        body = '<p><a href="https://brand.example/tool">Try Product</a><a href="https://www.brand.example/">Source</a><a href="https://brand.example/pricing?x=1">Details</a><a href="https://reference.example/doc">Reference</a></p>'
        stats, errors = CHECKS.check_links(body, {"max_target_links": 1}, self.CTA)
        self.assertEqual(stats["target_link_occurrences"], 3)
        self.assertEqual(stats["third_party_link_occurrences"], 1)
        self.assertTrue(errors)
        self.assertEqual(CHECKS.check_links(body, {}, self.CTA)[1], [])

    def test_required_multiple_anchors_are_preserved_not_blanket_rejected(self):
        body = '<a href="https://brand.example/tool">Try Product</a><a href="https://brand.example/tool">Example prompts</a>'
        policy = {"target_link_count": 2, "required_links": [{"href": "https://brand.example/tool", "anchor_text": "Example prompts", "count": 1}]}
        self.assertEqual(CHECKS.check_links(body, policy, self.CTA)[1], [])
        self.assertTrue(CHECKS.check_links(body + body, policy, self.CTA)[1])

    def test_unique_url_does_not_hide_repeated_occurrences(self):
        body = '<a href="https://brand.example/tool">Try Product</a>' * 3
        stats, errors = CHECKS.check_links(body, {"max_target_links": 1}, self.CTA)
        self.assertEqual(stats["unique_target_urls"], 1)
        self.assertEqual(stats["target_link_occurrences"], 3)
        self.assertTrue(errors)

    def test_bare_target_url_is_flagged_when_budget_cannot_be_proven(self):
        body = '<a href="https://brand.example/tool">Try Product</a><p>https://brand.example/tool</p>'
        stats, errors = CHECKS.check_links(body, {"max_target_links": 1}, self.CTA)
        self.assertEqual(stats["potential_target_autolinks"], 1)
        self.assertTrue(errors)

    def test_delivery_policy_changes_are_protected(self):
        cfg = {"schema_version": "2.14", "articles": [{"article_id": "A1", "language": "en"}]}
        plan = {"link_policy": {"max_target_links": 1}, "delivery_requirements": {"body_image_count": 3, "cover_required": True}}
        plan["confirmed_scope_snapshot"] = copy.deepcopy(fixtures.HARNESS.protected_prewrite_scope_snapshot(cfg, plan))
        self.assertEqual(fixtures.HARNESS.confirmed_scope_snapshot_errors(cfg, plan), [])
        plan["link_policy"]["max_target_links"] = 3
        self.assertTrue(fixtures.HARNESS.confirmed_scope_snapshot_errors(cfg, plan))


if __name__ == "__main__":
    unittest.main()
