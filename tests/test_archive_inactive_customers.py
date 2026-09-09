# ER-ServiceDesk/tests/test_archive_inactive_customers.py
"""
Covers app.workers.tasks.archive_inactive_customers() -- the automatic,
scheduled backstop alongside the manual Archive action, driven by the
configurable customer_inactivity_archive_months SystemSetting.
"""

from datetime import datetime, timedelta, timezone

import app.workers.tasks as tasks_module
from app.workers.tasks import archive_inactive_customers
from app.models.background_job import BackgroundJob
from app.services.system_setting_service import system_setting_service
from tests.conftest import TestSessionLocal
from tests.factories import make_customer


def test_archives_a_genuinely_inactive_customer_and_reports_the_real_count(db, monkeypatch):
    monkeypatch.setattr(tasks_module, "SessionLocal", TestSessionLocal)

    customer = make_customer(db)
    customer.created_at = datetime.now(timezone.utc) - timedelta(days=800)
    db.commit()

    result = archive_inactive_customers()

    assert result == {"archived": 1}
    db.refresh(customer)
    assert customer.is_archived is True


def test_a_recently_active_customer_is_never_archived(db, monkeypatch):
    monkeypatch.setattr(tasks_module, "SessionLocal", TestSessionLocal)

    customer = make_customer(db)  # created_at defaults to now

    result = archive_inactive_customers()

    assert result == {"archived": 0}
    db.refresh(customer)
    assert customer.is_archived is False


def test_the_configured_threshold_setting_genuinely_controls_the_cutoff(db, monkeypatch):
    """A customer inactive for 100 days is archived under a 3-month threshold, but not under the real, default 24-month one -- confirms the SystemSetting genuinely drives the real behavior, not a hardcoded number."""
    monkeypatch.setattr(tasks_module, "SessionLocal", TestSessionLocal)

    customer = make_customer(db)
    customer.created_at = datetime.now(timezone.utc) - timedelta(days=100)
    db.commit()

    result_with_default = archive_inactive_customers()
    assert result_with_default == {"archived": 0}

    system_setting_service.upsert(db, "customer_inactivity_archive_months", "3")
    result_with_custom_threshold = archive_inactive_customers()
    assert result_with_custom_threshold == {"archived": 1}


def test_a_real_failure_marks_the_background_job_as_failed(db, monkeypatch):
    monkeypatch.setattr(tasks_module, "SessionLocal", TestSessionLocal)
    monkeypatch.setattr(
        "app.services.customer_service.customer_service.get_customers_eligible_for_archiving",
        lambda db, threshold_months: (_ for _ in ()).throw(RuntimeError("genuine database failure")),
    )

    try:
        archive_inactive_customers()
    except RuntimeError:
        pass

    job = db.query(BackgroundJob).filter_by(job_type="archive_inactive_customers").order_by(BackgroundJob.id.desc()).first()
    assert job is not None
    assert job.status == "failed"
