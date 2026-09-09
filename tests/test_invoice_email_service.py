# ER-ServiceDesk/tests/test_invoice_email_service.py
"""
Covers InvoiceEmailService.send() -- real, non-obvious behaviors:
blocking an empty invoice, requiring a customer email on file, the
body genuinely differing for a paid vs unpaid invoice, and that a real
send failure leaves invoice_sent_at untouched with no audit entry.
"""

import pytest
from fastapi import HTTPException

from app.services.invoice_email_service import invoice_email_service
from app.models.invoice import Invoice
from app.models.invoice_line_item import InvoiceLineItem
from app.crud.audit_log import crud_audit_log
from tests.factories import make_full_ticket, make_plain_user


def _make_invoice_with_line_item(db, ticket_id, is_paid=False):
    invoice = Invoice(ticket_id=ticket_id, invoice_number=1, subtotal=100, total=100, is_paid=is_paid)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    line_item = InvoiceLineItem(invoice_id=invoice.id, service_name="Screen Repair", quantity=1, unit_price=100)
    db.add(line_item)
    db.commit()
    db.refresh(invoice)
    return invoice


def test_rejects_an_invoice_with_no_line_items(db):
    ticket = make_full_ticket(db)
    invoice = Invoice(ticket_id=ticket.id, invoice_number=1, subtotal=0, total=0)
    db.add(invoice)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        invoice_email_service.send(db, invoice.id, current_user_id=make_plain_user(db).id)
    assert exc_info.value.status_code == 400


def test_rejects_a_customer_with_no_email_on_file(db):
    ticket = make_full_ticket(db)
    ticket.customer.email = ""
    db.commit()
    invoice = _make_invoice_with_line_item(db, ticket.id)

    with pytest.raises(HTTPException) as exc_info:
        invoice_email_service.send(db, invoice.id, current_user_id=make_plain_user(db).id)
    assert exc_info.value.status_code == 400


def test_successful_send_sets_invoice_sent_at(db, monkeypatch):
    monkeypatch.setattr("app.services.invoice_email_service.send_email", lambda *args, **kwargs: None)
    ticket = make_full_ticket(db)
    invoice = _make_invoice_with_line_item(db, ticket.id)

    result = invoice_email_service.send(db, invoice.id, current_user_id=make_plain_user(db).id)

    assert result.invoice_sent_at is not None


def test_an_unpaid_invoice_body_asks_for_payment(db, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "app.services.invoice_email_service.send_email",
        lambda db, to_address, subject, body: captured.update(body=body),
    )
    ticket = make_full_ticket(db)
    invoice = _make_invoice_with_line_item(db, ticket.id, is_paid=False)

    invoice_email_service.send(db, invoice.id, current_user_id=make_plain_user(db).id)

    assert "Payment is due" in captured["body"]
    assert "paid in full" not in captured["body"]


def test_a_paid_invoice_body_reads_as_a_receipt_instead(db, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "app.services.invoice_email_service.send_email",
        lambda db, to_address, subject, body: captured.update(body=body),
    )
    ticket = make_full_ticket(db)
    invoice = _make_invoice_with_line_item(db, ticket.id, is_paid=True)

    invoice_email_service.send(db, invoice.id, current_user_id=make_plain_user(db).id)

    assert "paid in full" in captured["body"]
    assert "Payment is due" not in captured["body"]


def test_a_real_send_failure_leaves_invoice_sent_at_untouched_and_logs_nothing(db, monkeypatch):
    monkeypatch.setattr(
        "app.services.invoice_email_service.send_email",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("SMTP is down")),
    )
    ticket = make_full_ticket(db)
    invoice = _make_invoice_with_line_item(db, ticket.id)

    with pytest.raises(HTTPException) as exc_info:
        invoice_email_service.send(db, invoice.id, current_user_id=make_plain_user(db).id)
    assert exc_info.value.status_code == 400

    db.refresh(invoice)
    assert invoice.invoice_sent_at is None

    entries = [e for e in crud_audit_log.get_multi(db, limit=500) if e.action == "invoice_sent"]
    assert len(entries) == 0
