"""Required owner phrases cannot be replaced by an author's supporting angle."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

try:
    import test_research_integrity as fixtures
    import test_single_source_payload as payload_fixtures
except ModuleNotFoundError:
    from tests import test_research_integrity as fixtures
    from tests import test_single_source_payload as payload_fixtures

H = fixtures.HARNESS
PHRASE = "free image to video generator no signup required"
RULE = {
    "requirement_id": "REQ-KEYWORD-001",
    "phrase": PHRASE,
    "language": "en",
    "article_ids": ["*"],
    "localization_allowed": True,
    "required_meanings": ["免费", "图生视频", "无需注册"],
    "source_locator": "owner-message: shared main keyword for this batch",
}


class KeywordRequirementFidelityTests(unittest.TestCase):
    def inputs(self, language="en"):
        context = {"frozen_article": {"language": language}, "keyword_requirements": [copy.deepcopy(RULE)]}
        evidence = {"keyword_and_localization": {"focus_keyword": PHRASE}}
        title = PHRASE.title() + ": Prepare Your Two Images"
        metadata = {"canonical_title": title, "platform_title": title}
        return context, evidence, metadata, '<h1 id="blog-title">' + title + "</h1>"

    def test_complete_phrase_with_distinct_angle_passes(self):
        self.assertEqual(H.keyword_delivery_errors(*self.inputs()), [])

    def test_meaning_preserving_titles_allow_different_sentence_shapes(self):
        titles = [
            "Animate a Photo for Free—No Signup Needed",
            "No Account Needed: Write Prompts for Free Image-to-Video Clips",
            "Which Two Images Work Best for a Free Video Without Registration?",
        ]
        for title in titles:
            with self.subTest(title=title):
                c, e, m, _ = self.inputs()
                c["keyword_requirements"][0]["title_mode"] = "MEANING_PRESERVING"
                m.update({"canonical_title": title, "platform_title": title})
                self.assertEqual(H.keyword_delivery_errors(c, e, m, '<h1 id="blog-title">' + title + "</h1>"), [])
        # This proves format/identity acceptance, not semantic truth or ranking.

    def test_semantic_mode_keeps_the_shared_keyword_and_requires_title_identity(self):
        c, e, m, p = self.inputs()
        c["keyword_requirements"][0]["title_mode"] = "MEANING_PRESERVING"
        e["keyword_and_localization"]["focus_keyword"] = "prompts"
        self.assertTrue(any("replaced" in x for x in H.keyword_delivery_errors(c, e, m, p)))
        e["keyword_and_localization"]["focus_keyword"] = PHRASE
        self.assertTrue(any("does not match" in x for x in H.keyword_delivery_errors(c, e, m, '<h1 id="blog-title">Another sentence</h1>')))

    def test_title_mode_change_needs_confirmation_and_unknown_mode_is_rejected(self):
        cfg = {"schema_version": "2.14", "articles": [{"article_id": "A1", "language": "en"}]}
        plan = {"keyword_requirements": [copy.deepcopy(RULE)]}
        plan["confirmed_scope_snapshot"] = copy.deepcopy(H.protected_prewrite_scope_snapshot(cfg, plan))
        plan["keyword_requirements"][0]["title_mode"] = "MEANING_PRESERVING"
        self.assertTrue(H.confirmed_scope_snapshot_errors(cfg, plan))
        plan["keyword_requirements"][0]["title_mode"] = "SKIP_REQUIREMENTS"
        self.assertTrue(H.keyword_requirements_errors(cfg, plan))

    def test_author_cannot_replace_main_keyword_with_prompts(self):
        c, e, m, _ = self.inputs()
        e["keyword_and_localization"]["focus_keyword"] = "image to video prompts"
        m = {k: "Image to Video Prompts" for k in m}
        errors = H.keyword_delivery_errors(c, e, m, '<h1 id="blog-title">Image to Video Prompts</h1>')
        self.assertTrue(any("replaced the required owner phrase" in x for x in errors))
        self.assertTrue(any("canonical_title lacks" in x for x in errors))

    def test_only_seo_metadata_is_not_enough(self):
        c, e, m, _ = self.inputs()
        m.update({"canonical_title": "Prepare Your Images", "platform_title": "Prepare Your Images", "seo_title": PHRASE})
        self.assertTrue(H.keyword_delivery_errors(c, e, m, '<h1 id="blog-title">Prepare Your Images</h1>'))

    def test_intended_h1_is_checked_separately(self):
        c, e, m, _ = self.inputs()
        errors = H.keyword_delivery_errors(c, e, m, '<h1 id="blog-title">Unrelated Scene</h1>')
        self.assertTrue(any("intended H1" in x for x in errors))

    def test_phrase_match_does_not_accept_word_prefix(self):
        self.assertFalse(H.complete_keyword_in_text(PHRASE, PHRASE + "ness"))
        self.assertTrue(H.complete_keyword_in_text(PHRASE, PHRASE.upper() + ": Prompts"))

    def test_case_sensitive_owner_requirement_is_preserved(self):
        c, e, m, p = self.inputs()
        c["keyword_requirements"][0]["case_sensitive"] = True
        self.assertTrue(H.keyword_delivery_errors(c, e, m, p))

    def test_natural_japanese_variant_does_not_need_english(self):
        c, e, m, _ = self.inputs("ja")
        phrase = "登録不要の無料画像から動画生成ツール"
        e["keyword_and_localization"].update({
            "focus_keyword": phrase,
            "requirement_id": RULE["requirement_id"],
            "preserved_meanings": RULE["required_meanings"],
            "localization_rationale": "Brand wording and Japanese expression; preserve all owner conditions.",
        })
        title = phrase + "：動きを指定する方法"
        m = {k: title for k in m}
        self.assertEqual(H.keyword_delivery_errors(c, e, m, '<h1 id="blog-title">' + title + "</h1>"), [])
        e["keyword_and_localization"]["preserved_meanings"] = ["免费", "图生视频"]
        self.assertTrue(any("protected meaning" in x for x in H.keyword_delivery_errors(c, e, m, '<h1 id="blog-title">' + title + "</h1>")))

    def test_localized_phrase_needs_inherited_id_and_rationale(self):
        c, e, m, _ = self.inputs("hu")
        errors = H.keyword_delivery_errors(c, e, m, '<h1 id="blog-title">Other title</h1>')
        self.assertTrue(any("requirement ID" in x for x in errors))
        self.assertTrue(any("rationale" in x for x in errors))

    def test_missing_legacy_rule_does_not_add_a_gate(self):
        self.assertEqual(H.keyword_delivery_errors({}, {}, {}, ""), [])
        cfg = {"articles": [{"article_id": "A1", "language": "en"}]}
        self.assertEqual(H.keyword_requirements_errors(cfg, {}), [])
        self.assertEqual(H.protected_prewrite_scope_snapshot(cfg, {}), H.protected_prewrite_scope_snapshot(cfg, {"keyword_requirements": []}))

    def test_malformed_context_is_reported_not_crashed(self):
        c, e, m, p = self.inputs()
        c["keyword_requirements"] = [None]
        self.assertTrue(H.keyword_delivery_errors(c, e, m, p))

    def test_compiled_payload_is_checked_against_owner_rule(self):
        helper = payload_fixtures.SingleSourcePayloadTests()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical, metadata, visuals, evidence, package = helper.make_workspace(root)
            title = PHRASE.title() + ": Prepare Two Frames"
            data = json.loads(metadata.read_text())
            data.update({"canonical_title": title, "platform_title": title})
            metadata.write_text(json.dumps(data))
            evidence.write_text(json.dumps({"keyword_and_localization": {"focus_keyword": PHRASE}}))
            data = json.loads(package.read_text())
            data["artifact_sources"]["metadata"]["sha256"] = H.sha256_file(metadata)
            data["artifact_sources"]["evidence_pack"]["sha256"] = H.sha256_file(evidence)
            package.write_text(json.dumps(data))
            output = root / "handoff/visual-payload.html"
            output.parent.mkdir()
            result = helper.run_script(
                payload_fixtures.BUILD, "--title", title,
                "--body-html", str(canonical), "--article-package", str(package),
                "--metadata-json", str(metadata), "--visual-manifest", str(visuals),
                "--output", str(output),
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            context = self.inputs()[0]
            context["artifact_paths"] = {
                "evidence_pack": "research/evidence-pack.json",
                "metadata": "canonical/metadata.json",
                "visual_payload": "handoff/visual-payload.html",
            }
            self.assertEqual(H.keyword_artifact_errors(root, context), [])
            evidence.write_text(json.dumps({"keyword_and_localization": {"focus_keyword": "prompts"}}))
            self.assertTrue(any("replaced" in x for x in H.keyword_artifact_errors(root, context)))

    def test_project_rule_covers_each_article_without_author_copy(self):
        plan = {"keyword_requirements": [copy.deepcopy(RULE)]}
        self.assertEqual(H.inherited_keyword_requirements(plan, "A1"), [RULE])
        self.assertEqual(H.inherited_keyword_requirements(plan, "A2"), [RULE])
        plan["keyword_requirements"][0]["article_ids"] = ["A1"]
        self.assertEqual(H.inherited_keyword_requirements(plan, "A2"), [])

    def test_invalid_scope_and_conflicting_main_rules_are_rejected(self):
        cfg = {"articles": [{"article_id": "A1", "language": "en"}]}
        rule = copy.deepcopy(RULE)
        rule["article_ids"] = ["A404"]
        self.assertTrue(H.keyword_requirements_errors(cfg, {"keyword_requirements": [rule]}))
        other = {**RULE, "requirement_id": "REQ-KEYWORD-002"}
        self.assertTrue(any("only one" in x for x in H.keyword_requirements_errors(cfg, {"keyword_requirements": [RULE, other]})))

    def test_keyword_is_rendered_in_existing_plan_not_a_new_report(self):
        plan = {"keyword_requirements": [RULE], "article_plans": [{"article_id": "A1"}]}
        rendered = H.render_prewrite_plan_markdown(plan, "test-hash")
        self.assertIn(PHRASE, rendered)
        self.assertIn("继承主关键词要求", rendered)

    def test_keyword_change_invalidates_confirmed_scope(self):
        cfg = {"schema_version": "2.14", "articles": [{"article_id": "A1", "language": "en"}]}
        plan = {"keyword_requirements": [copy.deepcopy(RULE)]}
        plan["confirmed_scope_snapshot"] = copy.deepcopy(H.protected_prewrite_scope_snapshot(cfg, plan))
        self.assertEqual(H.confirmed_scope_snapshot_errors(cfg, plan), [])
        plan["keyword_requirements"][0]["phrase"] = "prompts"
        self.assertTrue(H.confirmed_scope_snapshot_errors(cfg, plan))
        plan.pop("keyword_requirements")
        self.assertTrue(H.confirmed_scope_snapshot_errors(cfg, plan))

    def test_real_context_build_inherits_and_detects_deleted_rule(self):
        helper = fixtures.ResearchIntegrityTests()
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp) / "campaign"
            helper.prepare(workspace)
            result = helper.run_harness("invalidate-prewrite-confirmation", "--workspace", str(workspace), "--reason", "fixture keyword confirmation")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            fixtures.configure_confirmed_human_release_map(
                workspace, H, campaign_id="research-integrity",
                article=fixtures.article(), confirmation_id="OWNER-KEYWORD-001",
            )
            plan_path = workspace / "prewrite-plan.json"
            plan = json.loads(plan_path.read_text())
            plan["keyword_requirements"] = [copy.deepcopy(RULE)]
            plan_path.write_text(json.dumps(plan))
            result = helper.run_harness("sync-prewrite-plan", "--workspace", str(workspace))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            receipt = workspace / "evidence/owner-confirmations/owner-confirmation.md"
            receipt.write_text("OWNER_PREWRITE_PLAN_CONFIRMED\nRequired shared main keyword: " + PHRASE)
            result = helper.run_harness("confirm-prewrite-plan", "--workspace", str(workspace), "--confirmation-id", "OWNER-KEYWORD-001", "--receipt-file", str(receipt), "--receipt-type", "OWNER_MESSAGE", "--source-locator", "keyword fixture owner confirmation")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            context_path = workspace / "articles/A1/context/article-contract.json"
            result = helper.run_harness("build-article-context", "--workspace", str(workspace), "--article-id", "A1", "--output", str(context_path))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            context = json.loads(context_path.read_text())
            self.assertEqual(context["keyword_requirements"], [RULE])
            self.assertEqual(H.article_context_errors(workspace, context_path), [])
            context.pop("keyword_requirements")
            context_path.write_text(json.dumps(context))
            self.assertTrue(any("inheritance" in x for x in H.article_context_errors(workspace, context_path)))


if __name__ == "__main__":
    unittest.main()
