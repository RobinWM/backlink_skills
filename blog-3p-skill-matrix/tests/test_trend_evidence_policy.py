#!/usr/bin/env python3
"""Regression checks for optional, bounded Google Trends evidence."""
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
SPEC = importlib.util.spec_from_file_location("blog_3p_harnessctl", HARNESS_PATH)
assert SPEC is not None and SPEC.loader is not None
HARNESS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(HARNESS)


class TrendEvidencePolicyTests(unittest.TestCase):
    def run_harness(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(HARNESS_PATH), *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def initialize(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temp_dir = tempfile.TemporaryDirectory()
        workspace = Path(temp_dir.name) / "campaign"
        initialized = self.run_harness("init", "--workspace", str(workspace), "--campaign-id", "example")
        self.assertEqual(initialized.returncode, 0, initialized.stdout + initialized.stderr)
        return temp_dir, workspace

    def test_schema_2_5_locks_optional_bounded_trends_policy(self) -> None:
        template = json.loads((ROOT / "templates/campaign.json").read_text(encoding="utf-8"))
        self.assertEqual(template, HARNESS.campaign("REPLACE_ME"))
        policy = template["keyword_research_policy"]["trend_evidence_policy"]
        self.assertEqual(policy, HARNESS.TREND_EVIDENCE_POLICY_2_5)
        self.assertEqual(policy["mode"], "OPTIONAL_ENGLISH_GLOBAL_RELATIVE_CONTEXT_ONLY")
        self.assertEqual(
            policy["insufficient_data_route"],
            "TARGET_PLATFORM_AUDIENCE_NEED_WITH_EXPLICIT_BOUNDARY",
        )
        self.assertIn("SEARCH_VOLUME", policy["prohibited_inferences"])
        self.assertIn("LOW_BASE_HIGH_MOMENTUM", policy["prohibited_inferences"])
        self.assertIn("MODEL_CAPABILITY", policy["prohibited_inferences"])

    def test_current_workspace_passes_without_any_trends_artifact(self) -> None:
        temp_dir, workspace = self.initialize()
        with temp_dir:
            self.assertFalse((workspace / "evidence/trends-momentum.md").exists())
            checked = self.run_harness("check", "--workspace", str(workspace))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertIn("CHECK_PASSED", checked.stdout)

    def test_current_schema_rejects_weakened_optional_trends_policy(self) -> None:
        temp_dir, workspace = self.initialize()
        with temp_dir:
            campaign_path = workspace / "campaign.json"
            cfg = json.loads(campaign_path.read_text(encoding="utf-8"))
            cfg["keyword_research_policy"]["trend_evidence_policy"] = copy.deepcopy(
                cfg["keyword_research_policy"]["trend_evidence_policy"]
            )
            cfg["keyword_research_policy"]["trend_evidence_policy"]["mode"] = "REQUIRED_BREAKOUT_SIGNAL"
            campaign_path.write_text(json.dumps(cfg), encoding="utf-8")
            checked = self.run_harness("check", "--workspace", str(workspace))
            self.assertNotEqual(checked.returncode, 0)
            self.assertIn("optional-trends evidence policy", checked.stdout)

    def test_schema_2_4_remains_compatible_without_new_policy(self) -> None:
        temp_dir, workspace = self.initialize()
        with temp_dir:
            campaign_path = workspace / "campaign.json"
            cfg = json.loads(campaign_path.read_text(encoding="utf-8"))
            cfg["schema_version"] = "2.4"
            cfg["keyword_research_policy"].pop("trend_evidence_policy")
            campaign_path.write_text(json.dumps(cfg), encoding="utf-8")
            checked = self.run_harness("check", "--workspace", str(workspace))
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)


if __name__ == "__main__":
    unittest.main()
