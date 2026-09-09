# ER-ServiceDesk/tests/test_waiver_service.py
"""
Covers WaiverService.send() -- real, non-obvious behaviors: requiring
a customer email on file, the business name genuinely getting
substituted into the waiver template (real string formatting, not
just assumed to work), the "the shop" fallback when none is
configured, and a real send failure leaving waiver_sent_at untouched.
"""

import pytest
from fastapi import HTTPException

from app.services.waiver_service import waiver_service
from app.crud.audit_log import crud_audit_log
from app.services.business_info_service import business_info_service
from app.schemas.business_info import BusinessInfoUpdate
from tests.factories import make_full_ticket, make_plain_user


def test_returns_404_for_a_nonexistent_ticket(db):
    with pytest.raises(HTTPException) as exc_info:
        waiver_service.send(db, ticket_id=999999, current_user_id=make_plain_user(db).id)
    assert exc_info.value.status_code == 404


def test_rejects_a_customer_with_no_email_on_file(db):
    ticket = make_full_ticket(db)
    ticket.customer.email = ""
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        waiver_service.send(db, ticket.id, current_user_id=make_plain_user(db).id)
    assert exc_info.value.status_code == 400


def test_successful_send_sets_waiver_sent_at(db, monkeypatch):
    monkeypatch.setattr("app.services.waiver_service.send_email", lambda *args, **kwargs: None)
    ticket = make_full_ticket(db)

    result = waiver_service.send(db, ticket.id, current_user_id=make_plain_user(db).id)

    assert result.waiver_sent_at is not None


def test_the_real_configured_business_name_is_genuinely_substituted_into_the_template(db, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "app.services.waiver_service.send_email",
        lambda db, to_address, subject, body: captured.update(body=body),
    )
    business_info_service.update(db, BusinessInfoUpdate(
        business_name="Eddie's Repair Shop", business_phone="555-0100",
        email_address="shop@example.com", smtp_host="smtp.example.com",
        smtp_port=587, imap_host="imap.example.com", imap_port=993,
    ))
    ticket = make_full_ticket(db)

    waiver_service.send(db, ticket.id, current_user_id=make_plain_user(db).id)

    assert "I authorize Eddie's Repair Shop to perform work" in captured["body"]
    assert "{business_name}" not in captured["body"]


def test_falls_back_to_the_shop_when_no_business_name_is_configured(db, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "app.services.waiver_service.send_email",
        lambda db, to_address, subject, body: captured.update(body=body),
    )
    ticket = make_full_ticket(db)

    waiver_service.send(db, ticket.id, current_user_id=make_plain_user(db).id)

    assert "I authorize the shop to perform work" in captured["body"]


def test_a_real_send_failure_leaves_waiver_sent_at_untouched_and_logs_nothing(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.waiver_service.send_email",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("SMTP is down")),
    )
    ticket = make_full_ticket(db)

    with pytest.raises(HTTPException) as exc_info:
        waiver_service.send(db, ticket.id, current_user_id=make_plain_user(db).id)
    assert exc_info.value.status_code == 400

    db.refresh(ticket)
    assert ticket.waiver_sent_at is None

    entries = [e for e in crud_audit_log.get_multi(db, limit=500) if e.action == "waiver_sent"]
    assert len(entries) == 0
