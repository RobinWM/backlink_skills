from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
SKILL_MD = SKILL_ROOT / "SKILL.md"
AUTH_MD = SKILL_ROOT / "references" / "account-authentication.md"


def test_skill_loads_account_authentication_reference():
    skill = SKILL_MD.read_text(encoding="utf-8")
    assert "references/account-authentication.md" in skill
    assert "continue the original submission" in skill


def test_auth_flow_covers_login_registration_and_gws_verification():
    auth = AUTH_MD.read_text(encoding="utf-8").lower()
    required_phrases = (
        "one normal login",
        "explicitly says this email has no account",
        "gws gmail users messages list",
        "gws gmail +read",
        "`gws` is unavailable",
        "https://mail.google.com",
        "same browser session",
        "poll every 10 seconds for at most 2 minutes",
    )
    for phrase in required_phrases:
        assert phrase in auth


def test_repository_does_not_embed_default_password():
    forbidden = str(8) * 8
    for path in SKILL_ROOT.rglob("*"):
        if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix in {".pyc", ".png", ".jpg", ".gif"}:
            continue
        assert forbidden not in path.read_text(encoding="utf-8", errors="ignore"), path
