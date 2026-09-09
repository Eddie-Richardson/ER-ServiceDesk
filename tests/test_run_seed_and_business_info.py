# ER-ServiceDesk/tests/test_run_seed_and_business_info.py
"""
Covers run_seed.py's run() and seed_business_info.py's run() -- both
standalone entrypoints the Setup Wizard invokes as subprocesses,
exercised directly here rather than via a real subprocess.
"""

import pytest

from app.db import run_seed as run_seed_module
from app.db import seed_business_info as seed_business_info_module
from app.models.role import Role
from app.services.business_info_service import business_info_service
from tests.conftest import TestSessionLocal


def test_run_seed_populates_real_roles(db, monkeypatch):
    """The real success path -- run() genuinely calls seed_data() against a real database session."""
    monkeypatch.setattr(run_seed_module, "SessionLocal", TestSessionLocal)

    run_seed_module.run()  # must not raise or exit

    role_names = {r.name for r in db.query(Role).all()}
    assert "admin" in role_names


def test_run_seed_exits_with_status_1_on_a_genuine_failure(db, monkeypatch):
    """A real failure inside seed_data() is genuinely caught and reported via the real exit code the Setup Wizard's subprocess call actually checks -- not a silent failure or an uncaught traceback."""
    monkeypatch.setattr(run_seed_module, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(
        run_seed_module, "seed_data",
        lambda db: (_ for _ in ()).throw(RuntimeError("genuine database failure")),
    )

    with pytest.raises(SystemExit) as exc_info:
        run_seed_module.run()
    assert exc_info.value.code == 1


def test_seed_business_info_saves_real_env_values(db, monkeypatch):
    """Real environment variables genuinely end up saved as real SystemSetting values, through the exact same service the desktop Settings screen uses."""
    monkeypatch.setattr(seed_business_info_module, "SessionLocal", TestSessionLocal)
    monkeypatch.setenv("BUSINESS_NAME", "Eddie's Repair Shop")
    monkeypatch.setenv("BUSINESS_PHONE", "555-0100")
    monkeypatch.setenv("EMAIL_ADDRESS", "shop@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "a-genuinely-real-secret")
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "2525")
    monkeypatch.setenv("IMAP_HOST", "imap.example.com")
    monkeypatch.setenv("IMAP_PORT", "1993")

    seed_business_info_module.run()  # must not raise or exit

    info = business_info_service.get_full(db)
    assert info.business_name == "Eddie's Repair Shop"
    assert info.email_address == "shop@example.com"
    assert info.smtp_host == "smtp.example.com"
    assert info.smtp_port == 2525
    assert info.imap_port == 1993


def test_seed_business_info_uses_real_smtp_imap_defaults_when_unset(db, monkeypatch):
    """Business name/phone/email are required inputs, but SMTP/IMAP host and port genuinely fall back to their real, documented Gmail defaults when the corresponding env vars are absent."""
    monkeypatch.setattr(seed_business_info_module, "SessionLocal", TestSessionLocal)
    monkeypatch.setenv("BUSINESS_NAME", "Eddie's Repair Shop")
    monkeypatch.setenv("BUSINESS_PHONE", "555-0100")
    monkeypatch.setenv("EMAIL_ADDRESS", "shop@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "a-genuinely-real-secret")
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.delenv("SMTP_PORT", raising=False)
    monkeypatch.delenv("IMAP_HOST", raising=False)
    monkeypatch.delenv("IMAP_PORT", raising=False)

    seed_business_info_module.run()

    info = business_info_service.get_full(db)
    assert info.smtp_host == "smtp.gmail.com"
    assert info.smtp_port == 587
    assert info.imap_host == "imap.gmail.com"
    assert info.imap_port == 993


def test_seed_business_info_password_ends_up_genuinely_encrypted(db, monkeypatch):
    """The email password saved through this script is genuinely encrypted at rest, the same way the desktop Settings screen's own save path encrypts it -- never stored as plaintext."""
    monkeypatch.setattr(seed_business_info_module, "SessionLocal", TestSessionLocal)
    monkeypatch.setenv("BUSINESS_NAME", "Eddie's Repair Shop")
    monkeypatch.setenv("BUSINESS_PHONE", "555-0100")
    monkeypatch.setenv("EMAIL_ADDRESS", "shop@example.com")
    monkeypatch.setenv("EMAIL_PASSWORD", "a-genuinely-real-secret")

    seed_business_info_module.run()

    from app.services.system_setting_service import system_setting_service
    encrypted = system_setting_service.get_str(db, "email_password_encrypted", "")
    assert encrypted != ""
    assert "a-genuinely-real-secret" not in encrypted
