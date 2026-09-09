# ER-ServiceDesk/tests/test_quote_email_service.py
"""
Covers QuoteEmailService.send() -- real, non-obvious behaviors:
blocking an empty quote, requiring a customer email on file, the
"reply I APPROVE" instruction genuinely appearing in the body (the
real, only way an approval reaches the system, per this file's own
docstring), and a real send failure leaving quote_sent_at untouched.
"""

import pytest
from fastapi import HTTPException

from app.services.quote_email_service import quote_email_service
from app.models.quote import Quote
from app.models.quote_line_item import QuoteLineItem
from app.crud.audit_log import crud_audit_log
from tests.factories import make_full_ticket, make_plain_user


def _make_quote_with_line_item(db, ticket_id):
    quote = Quote(ticket_id=ticket_id, quote_number=1, subtotal=100, total=100)
    db.add(quote)
    db.commit()
    db.refresh(quote)

    line_item = QuoteLineItem(quote_id=quote.id, service_name="Diagnostic", quantity=1, unit_price=100)
    db.add(line_item)
    db.commit()
    db.refresh(quote)
    return quote


def test_rejects_a_quote_with_no_line_items(db):
    ticket = make_full_ticket(db)
    quote = Quote(ticket_id=ticket.id, quote_number=1, subtotal=0, total=0)
    db.add(quote)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        quote_email_service.send(db, quote.id, current_user_id=make_plain_user(db).id)
    assert exc_info.value.status_code == 400


def test_rejects_a_customer_with_no_email_on_file(db):
    ticket = make_full_ticket(db)
    ticket.customer.email = ""
    db.commit()
    quote = _make_quote_with_line_item(db, ticket.id)

    with pytest.raises(HTTPException) as exc_info:
        quote_email_service.send(db, quote.id, current_user_id=make_plain_user(db).id)
    assert exc_info.value.status_code == 400


def test_successful_send_sets_quote_sent_at(db, monkeypatch):
    monkeypatch.setattr("app.services.quote_email_service.send_email", lambda *args, **kwargs: None)
    ticket = make_full_ticket(db)
    quote = _make_quote_with_line_item(db, ticket.id)

    result = quote_email_service.send(db, quote.id, current_user_id=make_plain_user(db).id)

    assert result.quote_sent_at is not None


def test_body_genuinely_contains_the_real_approval_instruction(db, monkeypatch):
    """The only real way an approval reaches the system is a customer replying "I APPROVE" -- confirms that instruction genuinely appears in what actually gets sent, not just assumed."""
    captured = {}
    monkeypatch.setattr(
        "app.services.quote_email_service.send_email",
        lambda db, to_address, subject, body: captured.update(body=body),
    )
    ticket = make_full_ticket(db)
    quote = _make_quote_with_line_item(db, ticket.id)

    quote_email_service.send(db, quote.id, current_user_id=make_plain_user(db).id)

    assert "I APPROVE" in captured["body"]
    assert "estimate, not a bill" in captured["body"]


def test_a_real_send_failure_leaves_quote_sent_at_untouched_and_logs_nothing(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.quote_email_service.send_email",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("SMTP is down")),
    )
    ticket = make_full_ticket(db)
    quote = _make_quote_with_line_item(db, ticket.id)

    with pytest.raises(HTTPException) as exc_info:
        quote_email_service.send(db, quote.id, current_user_id=make_plain_user(db).id)
    assert exc_info.value.status_code == 400

    db.refresh(quote)
    assert quote.quote_sent_at is None

    entries = [e for e in crud_audit_log.get_multi(db, limit=500) if e.action == "quote_sent"]
    assert len(entries) == 0
