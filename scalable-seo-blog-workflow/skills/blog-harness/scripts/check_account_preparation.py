#!/usr/bin/env python3
"""Check a bounded account-preparation receipt; never operate a browser.

This proves local integrity, not human origin or the meaning of an authorization.
G must verify the original owner instruction before using the approved actions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


ACTIONS = frozenset({
    "USE_EXISTING_SESSION", "LOGIN", "REGISTER", "VERIFY_EMAIL",
    "SET_REQUIRED_PROFILE", "CREATE_PUBLISHING_SPACE", "CHECK_PUBLISHING_ACCESS",
})
SECRET_KEYS = frozenset({
    "password", "passwd", "secret", "token", "access_token", "refresh_token",
    "cookie", "cookies", "otp", "verification_code", "credentials", "api_key",
    "authorization", "session_token",
})


def nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and "REPLACE_" not in value


def local_path(root: Path, value: object) -> Path:
    if not nonempty(value) or Path(str(value)).is_absolute():
        raise ValueError("requires a relative workspace path")
    path = (root / str(value)).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("path escapes the workspace") from exc
    return path


def contains_secret_field(value: object) -> bool:
    if isinstance(value, dict):
        return any(
            str(key).casefold() in SECRET_KEYS or contains_secret_field(item)
            for key, item in value.items()
        )
    if isinstance(value, list):
        return any(contains_secret_field(item) for item in value)
    return False


def source_bytes(root: Path, record: object, prefix: str) -> bytes:
    if not isinstance(record, dict):
        raise ValueError("missing source record")
    path = local_path(root, record.get("path"))
    if not path.is_relative_to(root / prefix):
        raise ValueError("source is outside its evidence directory")
    if not nonempty(record.get("source_locator")):
        raise ValueError("missing original source location")
    data = path.read_bytes()
    if record.get("sha256") != hashlib.sha256(data).hexdigest():
        raise ValueError("source hash mismatch")
    return data


def validate(root: Path, manifest: dict, target_id: str, requested: list[str]) -> list[str]:
    cfg = json.loads((root / "campaign.json").read_text(encoding="utf-8"))
    if contains_secret_field(manifest):
        raise ValueError("secret fields prohibited; use credential references")
    if manifest.get("schema_version") != "1.0" or manifest.get("mode") != "OWNER_AUTHORIZED_MINIMAL_SETUP":
        raise ValueError("unsupported account-preparation manifest")
    if manifest.get("campaign_id") != cfg.get("campaign_id"):
        raise ValueError("campaign identity mismatch")
    release = cfg.get("release_policy")
    if not isinstance(release, dict) or release.get("mode") != "HUMAN_NATIVE_ONLY" or release.get("machine_external_writes_allowed") is not False:
        raise ValueError("human-only content release must remain unchanged")
    rows = manifest.get("targets")
    if not isinstance(rows, list) or not rows or any(not isinstance(row, dict) for row in rows):
        raise ValueError("requires target records")
    ids = [row.get("target_id") for row in rows]
    if any(not nonempty(item) for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("target IDs must be unique and nonempty")
    selected = [row for row in rows if row.get("target_id") == target_id]
    if not selected:
        raise ValueError("target is not in the authorization manifest")
    row = selected[0]
    platform, account = row.get("platform"), row.get("account")
    if not nonempty(platform) or not nonempty(account) or not nonempty(row.get("browser_ref")):
        raise ValueError("requires platform, safe identity label and designated browser")
    actions = row.get("allowed_actions")
    if not isinstance(actions, list) or not actions or any(not isinstance(item, str) for item in actions):
        raise ValueError("requires explicit actions")
    if len(set(actions)) != len(actions) or not set(actions) <= ACTIONS:
        raise ValueError("unsupported or duplicate action; content writes are prohibited")
    if not set(requested) <= set(actions):
        raise ValueError("requested action is outside this target authorization")
    if set(actions) & {"SET_REQUIRED_PROFILE", "CREATE_PUBLISHING_SPACE"} and not nonempty(row.get("brand_profile_ref")):
        raise ValueError("minimal setup requires existing brand-profile information")
    candidate = row.get("candidate_source")
    candidate_data = source_bytes(root, candidate, "evidence/owner-selection")
    if candidate.get("source_type") not in {"OWNER_MESSAGE", "OWNER_TABLE", "OWNER_XLSX"}:
        raise ValueError("candidate requires an owner-originated source type")
    if candidate.get("platform_source_literal") != platform:
        raise ValueError("platform does not match its original source literal")
    # XLSX location semantics remain G's responsibility; do not pretend that a
    # byte hash proves a particular spreadsheet cell or audience suitability.
    if candidate.get("source_type") != "OWNER_XLSX" and platform not in candidate_data.decode("utf-8"):
        raise ValueError("platform is absent from the textual candidate source")
    auth = row.get("owner_authorization")
    auth_data = source_bytes(root, auth, "evidence/owner-confirmations")
    if auth.get("source_type") not in {"OWNER_MESSAGE", "OWNER_FILE"}:
        raise ValueError("authorization requires an owner-originated receipt type")
    literal = auth.get("literal")
    if not nonempty(auth.get("confirmation_id")) or not nonempty(literal):
        raise ValueError("requires confirmation ID and exact non-secret authorization quote")
    if literal not in auth_data.decode("utf-8") or platform not in literal:
        raise ValueError("authorization quote must be present and name this platform")
    scope = cfg.get("scope_lock", {})
    if isinstance(scope, dict) and scope.get("status") == "LOCKED":
        pairs = cfg.get("platform_scope", {}).get("allowed_pairs", [])
        if not any(isinstance(pair, dict) and pair.get("platform") == platform and pair.get("account") == account for pair in pairs):
            raise ValueError("target differs from the locked platform/account scope")
    return actions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--target-id", required=True)
    parser.add_argument("--action", action="append", default=[], choices=sorted(ACTIONS))
    args = parser.parse_args()
    try:
        root = args.workspace.resolve()
        manifest = json.loads(local_path(root, args.manifest).read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("manifest must be an object")
        actions = validate(root, manifest, args.target_id, args.action)
    except (json.JSONDecodeError, UnicodeError, OSError, TypeError, AttributeError, KeyError):
        # Do not print raw parser/file errors or user-provided data.
        print("ACCOUNT_PREPARATION_AUTHORIZATION_INVALID\nreason=missing or malformed local record")
        return 1
    except ValueError as exc:
        # Our integrity errors contain fixed descriptions, never input values.
        print("ACCOUNT_PREPARATION_AUTHORIZATION_INVALID\nreason=" + str(exc))
        return 1
    print("ACCOUNT_PREPARATION_AUTHORIZATION_VALID")
    print("actions=" + ",".join(actions))
    print("Local integrity only; verify owner intent. No browser action or publication proof.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
