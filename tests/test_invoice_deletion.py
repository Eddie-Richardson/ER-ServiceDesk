# ER-ServiceDesk/tests/test_invoice_deletion.py
"""
Covers InvoiceService.delete()'s full, real rejection matrix -- has
line items, already sent, has payments recorded, came from a
converted quote, and the "only the most recently created invoice"
numbering-gap protection. All real, money-relevant rejections.
"""

import pytest
from datetime import datetime, UTC
from fastapi import HTTPException

from app.services.invoice_service import invoice_service
from tests.factories import make_full_ticket, make_plain_user


def test_delete_rejects_an_invoice_with_line_items(client, agent_headers, superuser_headers, db):
    ticket = make_full_ticket(db)
    invoice_resp = client.post("/invoices/", json={"ticket_id": ticket.id}, headers=agent_headers)
    invoice_id = invoice_resp.json()["id"]
    service_resp = client.post("/services/", json={"name": "Diagnostic", "price": 50.0}, headers=superuser_headers)
    client.post(f"/invoices/{invoice_id}/line-items", params={"service_id": service_resp.json()["id"], "quantity": 1}, headers=agent_headers)

    resp = client.delete(f"/invoices/{invoice_id}", headers=agent_headers)
    assert resp.status_code == 400


def test_delete_rejects_an_already_sent_invoice(db):
    ticket = make_full_ticket(db)
    actor_id = make_plain_user(db).id
    from app.schemas.invoice import InvoiceCreate
    invoice = invoice_service.create(db, InvoiceCreate(ticket_id=ticket.id), actor_id)
    invoice.invoice_sent_at = datetime.now(UTC)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        invoice_service.delete(db, invoice.id, actor_id)
    assert exc_info.value.status_code == 400


def test_delete_rejects_an_invoice_with_payments_recorded(client, agent_headers, db):
    ticket = make_full_ticket(db)
    invoice_resp = client.post("/invoices/", json={"ticket_id": ticket.id}, headers=agent_headers)
    invoice_id = invoice_resp.json()["id"]
    client.post("/payments/", json={"invoice_id": invoice_id, "amount": "10.00", "method": "cash"}, headers=agent_headers)

    resp = client.delete(f"/invoices/{invoice_id}", headers=agent_headers)
    assert resp.status_code == 400


def test_delete_rejects_an_invoice_that_came_from_a_converted_quote(client, agent_headers, superuser_headers, db):
    ticket = make_full_ticket(db)
    quote_resp = client.post("/quotes/", json={"ticket_id": ticket.id}, headers=agent_headers)
    quote_id = quote_resp.json()["id"]
    convert_resp = client.post(f"/quotes/{quote_id}/convert-to-invoice", headers=agent_headers)
    invoice_id = convert_resp.json()["id"]

    resp = client.delete(f"/invoices/{invoice_id}", headers=agent_headers)
    assert resp.status_code == 400


def test_delete_rejects_an_invoice_thats_not_the_most_recently_created(db):
    """Deleting anything but the latest invoice number would leave a permanent gap in the sequence."""
    ticket = make_full_ticket(db)
    actor_id = make_plain_user(db).id
    from app.schemas.invoice import InvoiceCreate
    older_invoice = invoice_service.create(db, InvoiceCreate(ticket_id=ticket.id), actor_id)
    invoice_service.create(db, InvoiceCreate(ticket_id=ticket.id), actor_id)  # a newer one now exists

    with pytest.raises(HTTPException) as exc_info:
        invoice_service.delete(db, older_invoice.id, actor_id)
    assert exc_info.value.status_code == 400


def test_delete_succeeds_for_an_untouched_most_recent_empty_invoice(db):
    ticket = make_full_ticket(db)
    actor_id = make_plain_user(db).id
    from app.schemas.invoice import InvoiceCreate
    invoice = invoice_service.create(db, InvoiceCreate(ticket_id=ticket.id), actor_id)
    invoice_id = invoice.id

    invoice_service.delete(db, invoice_id, actor_id)

    assert invoice_service.get(db, invoice_id) is None
