"""Brand names belong in target links, not just in nearby copy or metadata."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import unittest

from tests import test_lightweight_matrix as fixture


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "brand_anchor_checks", ROOT / "skills/blog-human-handoff/scripts/content_integrity.py")
CHECKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKS)


class BrandAnchorChecksTests(unittest.TestCase):
    CTA = {"anchor_text": "Try Flyne", "product_destination_url": "https://flyne.example/tool"}
    POLICY = {"target_brand_names": {"flyne.example": ["Flyne", "Flyne AI"]}}

    def errors(self, body, policy=None, cta=None):
        return CHECKS.check_links(body, self.POLICY if policy is None else policy,
                                  self.CTA if cta is None else cta)[1]

    def test_brand_can_be_natural_localized_and_formatted(self):
        for text in ("Flyne の画像から動画", "用 Flyne 制作短片", "Ｆｌｙｎｅ 的工具",
                     "<strong>Flyne</strong>’s image-to-video tool", "flyne AI"):
            with self.subTest(text=text):
                body = '<a href="https://flyne.example/tool">' + text + '</a>'
                parser = CHECKS.Links()
                parser.feed(body)
                self.assertFalse(CHECKS.brand_anchor_errors(parser.anchors, self.POLICY))

    def test_nearby_brand_does_not_fix_unbranded_anchor(self):
        body = '<p>Flyne offers a tool. <a href="https://flyne.example/tool">Try this tool</a></p>'
        self.assertTrue(any("confirmed brand name" in error for error in self.errors(body)))

    def test_url_and_brand_substrings_are_not_brand_names(self):
        for text in ("https://flyne.example/tool", "flyne.example/tool", "NotFlyne", "FlyneClone"):
            with self.subTest(text=text):
                body = '<a href="https://flyne.example/tool">' + text + '</a>'
                self.assertTrue(any("confirmed brand name" in error for error in self.errors(body)))

    def test_hidden_or_image_only_brand_does_not_count_as_visible_link_text(self):
        for text in ('<span hidden>Flyne</span>Try this tool',
                     '<span style="display: none">Flyne</span>Try this tool',
                     '<span style="visibility:hidden"><b>Flyne</b></span>Try this tool',
                     '<script>Flyne</script>Try this tool',
                     '<template>Flyne</template>Try this tool',
                     '<img src="cover.png" alt="Flyne">'):
            with self.subTest(text=text):
                body = '<a href="https://flyne.example/tool">' + text + '</a>'
                self.assertTrue(any("confirmed brand name" in error for error in self.errors(body)))

    def test_source_and_intro_links_are_checked_but_other_sources_are_not(self):
        body = '<a href="https://flyne.example/tool">Try Flyne</a>'
        self.assertFalse(self.errors(body + '<a href="https://docs.example/">Reference</a>'))
        self.assertTrue(self.errors(body + '<a href="https://www.flyne.example/pricing">Source</a>'))

    def test_each_target_uses_its_own_most_specific_brand(self):
        policy = {"target_brand_names": {"flyne.example": ["Flyne"],
                                        "music.flyne.example": ["Music Maker"],
                                        "other.example": ["Other Brand"]}}
        body = ('<a href="https://flyne.example/tool">Try Flyne</a>'
                '<a href="https://music.flyne.example/">Music Maker</a>'
                '<a href="https://other.example/">Other Brand</a>')
        self.assertFalse(self.errors(body, policy))
        self.assertTrue(self.errors(body.replace('>Music Maker<', '>Flyne<'), policy))

    def test_counts_and_locked_text_still_apply(self):
        body = '<a href="https://flyne.example/tool">Try Flyne</a>'
        policy = dict(self.POLICY, target_link_count=1)
        stats, errors = CHECKS.check_links(body * 2, policy, self.CTA)
        self.assertEqual(stats["target_link_occurrences"], 2)
        self.assertTrue(any("target_link_count" in error for error in errors))
        self.assertTrue(any("missing required link/anchor" in error
                            for error in self.errors(body.replace('>Try Flyne<', '>Use Flyne<'))))

    def test_malformed_brand_policy_cannot_disable_checks(self):
        for value in (False, [], {"flyne.example": []}, {"flyne.example": [""]},
                      {"https://flyne.example/tool": ["Flyne"]}):
            with self.subTest(value=value):
                self.assertTrue(CHECKS.policy_errors({"target_brand_names": value}))

    def test_legacy_context_without_brand_map_is_not_silently_rewritten(self):
        cta = {"anchor_text": "Try this tool", "product_destination_url": "https://flyne.example/tool"}
        body = '<a href="https://flyne.example/tool">Try this tool</a>'
        self.assertFalse(self.errors(body, {}, cta))


@unittest.skipUnless(importlib.util.find_spec("markdown_it"), "Markdown dependency required")
class BrandAnchorBuildTests(unittest.TestCase):
    def setUp(self):
        self.project = fixture.LightweightMatrixTests()
        self.project.setUp()
        self.addCleanup(self.project.doCleanups)

    def test_new_build_enforces_brand_without_a_new_plan_field(self):
        p = self.project
        p.freeze()
        self.assertEqual(p.build().returncode, 0)
        p.body += '\n[Source](https://example.com/pricing)\n'
        p.write_draft()
        result = p.build()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("confirmed brand name", result.stderr)

    def test_conflicting_frozen_anchor_is_reported_not_rewritten(self):
        p = self.project
        p.plan["shared"]["cta"]["anchor_text"] = "Try this tool"
        p.body = p.body.replace("Try Example Product", "Try this tool")
        p.write_plan()
        p.write_draft()
        p.freeze()
        original = p.plan_path.read_bytes()
        result = p.build("--brief")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("confirmed brand name", result.stderr)
        self.assertEqual(p.plan_path.read_bytes(), original)
        self.assertFalse((p.article / "handoff").exists())

    def test_confirmed_brand_map_handles_a_different_product_display_name(self):
        p = self.project
        p.plan["shared"]["cta"]["product_name"] = "Image-to-video tool"
        p.plan["shared"]["link_policy"] = {"target_brand_names": {"example.com": ["Example"]}}
        p.write_plan()
        p.freeze()
        self.assertEqual(p.build().returncode, 0)

    def test_missing_other_target_brand_is_reported(self):
        p = self.project
        p.plan["shared"]["link_policy"] = {"target_domains": ["other.example"]}
        p.write_plan()
        p.freeze()
        result = p.build("--brief")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("target domain needs confirmed", result.stderr)

    def test_brand_rule_cannot_be_disabled_with_an_empty_mapping(self):
        p = self.project
        p.plan["shared"]["link_policy"] = {"target_brand_names": {}}
        p.plan["shared"]["cta"]["anchor_text"] = "Try this tool"
        p.write_plan()
        p.freeze()
        self.assertNotEqual(p.build("--brief").returncode, 0)


if __name__ == "__main__":
    unittest.main()
