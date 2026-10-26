"""Bounded account preparation must never unlock content release."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/blog-harness/scripts/check_account_preparation.py"
SPEC = importlib.util.spec_from_file_location("account_preparation_guard", SCRIPT)
assert SPEC and SPEC.loader
GUARD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GUARD)


class AccountPreparationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.workspace = Path(self.temp.name).resolve()
        self.cfg = {
            "campaign_id": "account-test",
            "scope_lock": {"status": "DRAFT"},
            "release_policy": {"mode": "HUMAN_NATIVE_ONLY", "machine_external_writes_allowed": False},
        }
        self.write_cfg()
        candidate = self.workspace / "evidence/owner-selection/candidates.md"
        candidate.parent.mkdir(parents=True)
        candidate.write_text("Owner candidates: ExampleNote, ExampleDirect.\n", encoding="utf-8")
        auth = self.workspace / "evidence/owner-confirmations/account-authorization.md"
        auth.parent.mkdir(parents=True)
        literal = "Allow ExampleNote / BrandX registration, login and a default blog; no content publication."
        auth.write_text(literal + "\n", encoding="utf-8")
        self.manifest = {
            "schema_version": "1.0", "campaign_id": "account-test",
            "mode": "OWNER_AUTHORIZED_MINIMAL_SETUP",
            "targets": [{
                "target_id": "ACCOUNT-01", "platform": "ExampleNote", "account": "BrandX",
                "candidate_source": {
                    "source_type": "OWNER_MESSAGE", "path": str(candidate.relative_to(self.workspace)),
                    "sha256": hashlib.sha256(candidate.read_bytes()).hexdigest(),
                    "source_locator": "owner list", "platform_source_literal": "ExampleNote",
                },
                "owner_authorization": {
                    "source_type": "OWNER_MESSAGE", "path": str(auth.relative_to(self.workspace)),
                    "sha256": hashlib.sha256(auth.read_bytes()).hexdigest(),
                    "confirmation_id": "OWNER-ACCOUNT-001", "source_locator": "owner instruction",
                    "literal": literal,
                },
                "allowed_actions": ["REGISTER", "LOGIN", "CREATE_PUBLISHING_SPACE"],
                "browser_ref": "Profile-7", "credential_ref": "vault-item-alias",
                "brand_profile_ref": "BrandX-profile-card",
            }],
        }

    @property
    def target(self) -> dict:
        return self.manifest["targets"][0]

    def write_cfg(self) -> None:
        (self.workspace / "campaign.json").write_text(json.dumps(self.cfg), encoding="utf-8")

    def check(self, *actions: str) -> list[str]:
        return GUARD.validate(self.workspace, self.manifest, "ACCOUNT-01", list(actions))

    def test_authorized_minimal_blog_setup_keeps_release_disabled(self) -> None:
        self.assertIn("CREATE_PUBLISHING_SPACE", self.check("CREATE_PUBLISHING_SPACE"))
        self.assertFalse(json.loads((self.workspace / "campaign.json").read_text())["release_policy"]["machine_external_writes_allowed"])

    def test_login_authorization_cannot_expand_to_register_or_create(self) -> None:
        self.target["allowed_actions"] = ["LOGIN"]
        self.assertEqual(self.check("LOGIN"), ["LOGIN"])
        for action in ("REGISTER", "CREATE_PUBLISHING_SPACE"):
            with self.subTest(action=action), self.assertRaises(ValueError):
                self.check(action)

    def test_content_writes_and_site_construction_are_not_actions(self) -> None:
        for action in ("PUBLISH", "SAVE_DRAFT", "UPLOAD_ARTICLE_IMAGE", "CONFIGURE_DNS", "PAY", "DELETE"):
            with self.subTest(action=action):
                self.target["allowed_actions"] = [action]
                with self.assertRaises(ValueError):
                    self.check()

    def test_invented_platform_cannot_pass_textual_owner_source(self) -> None:
        self.target["platform"] = "InventedPlatform"
        self.target["candidate_source"]["platform_source_literal"] = "InventedPlatform"
        with self.assertRaises(ValueError):
            self.check()

    def test_absent_authorization_and_changed_receipts_fail(self) -> None:
        self.target["owner_authorization"]["literal"] = "Allow a different operation."
        with self.assertRaises(ValueError):
            self.check()
        self.target["owner_authorization"]["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            self.check()

    def test_source_path_cannot_escape_or_use_internal_state_as_receipt(self) -> None:
        for path in ("../outside.md", "campaign.json"):
            with self.subTest(path=path):
                self.target["owner_authorization"]["path"] = path
                with self.assertRaises(ValueError):
                    self.check()

    def test_locked_scope_is_not_replaced_by_setup_authorization(self) -> None:
        self.cfg["scope_lock"]["status"] = "LOCKED"
        self.cfg["platform_scope"] = {"allowed_pairs": [{"platform": "ExampleNote", "account": "OtherIdentity"}]}
        self.write_cfg()
        with self.assertRaises(ValueError):
            self.check()

    def test_setup_cannot_enable_general_external_writes(self) -> None:
        self.cfg["release_policy"]["machine_external_writes_allowed"] = True
        self.write_cfg()
        with self.assertRaises(ValueError):
            self.check()

    def test_other_pending_target_does_not_hold_ready_target(self) -> None:
        pending = copy.deepcopy(self.target)
        pending["target_id"] = "ACCOUNT-02"
        pending["owner_authorization"] = None
        self.manifest["targets"].append(pending)
        self.assertIn("REGISTER", self.check("REGISTER"))
        with self.assertRaises(ValueError):
            GUARD.validate(self.workspace, self.manifest, "ACCOUNT-02", [])

    def test_plain_secret_fields_are_rejected_without_echo(self) -> None:
        self.target["password"] = "TEST_ONLY_NON_SECRET_VALUE"
        with self.assertRaises(ValueError):
            self.check()
        path = self.workspace / "authorization.json"
        path.write_text(json.dumps(self.manifest), encoding="utf-8")
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--workspace", str(self.workspace),
             "--manifest", path.name, "--target-id", "ACCOUNT-01"],
            capture_output=True, text=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("TEST_ONLY_NON_SECRET_VALUE", result.stdout + result.stderr)

    def test_minimal_setup_requires_existing_brand_information(self) -> None:
        self.target.pop("brand_profile_ref")
        with self.assertRaises(ValueError):
            self.check()


if __name__ == "__main__":
    unittest.main()
