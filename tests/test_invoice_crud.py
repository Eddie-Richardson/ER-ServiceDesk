# ER-ServiceDesk/tests/test_invoice_crud.py
"""
Covers Invoice CRUD -- both the HTTP-level create/list/get/update/
delete lifecycle, and InvoiceCRUD's own get_by_ticket()/delete()
directly, since those aren't their own HTTP endpoints (invoices are
deleted via the service layer's rejection path, and get_by_ticket()
is an internal lookup used elsewhere).
"""

from app.crud.invoice import crud_invoice
from app.models.ticket import Ticket
from tests.factories import make_full_ticket, make_invoice, make_ticket_dependencies


def _second_ticket_for(db, deps):
    """A second, real ticket sharing the same customer/device -- avoids the unique-email conflict make_full_ticket() would hit if called twice."""
    ticket = Ticket(
        customer_id=deps["customer"].id, device_id=deps["device"].id,
        category_id=deps["category"].id, type_id=deps["type"].id,
        status_id=deps["status"].id, title="Second ticket", priority="normal",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def test_get_by_ticket_returns_only_that_tickets_own_invoices(db):
    deps = make_ticket_dependencies(db)
    ticket_a = _second_ticket_for(db, deps)
    ticket_b = _second_ticket_for(db, deps)

    invoice_a1 = make_invoice(db, ticket_a.id)
    make_invoice(db, ticket_a.id)
    make_invoice(db, ticket_b.id)

    result = crud_invoice.get_by_ticket(db, ticket_a.id)

    assert len(result) == 2
    assert invoice_a1.id in [inv.id for inv in result]
    assert all(inv.ticket_id == ticket_a.id for inv in result)


def test_get_by_ticket_returns_an_empty_list_for_a_ticket_with_no_invoices(db):
    ticket = make_full_ticket(db)
    assert crud_invoice.get_by_ticket(db, ticket.id) == []


def test_delete_genuinely_removes_the_record(db):
    ticket = make_full_ticket(db)
    invoice = make_invoice(db, ticket.id)
    invoice_id = invoice.id

    crud_invoice.delete(db, invoice)

    assert crud_invoice.get(db, invoice_id) is None


def test_updating_an_invoices_tax_rate_genuinely_recalculates_the_total(client, agent_headers, superuser_headers, db):
    """PUT /invoices/{id} was never exercised by the existing CRUD test at all (which only tests create/list/get/delete) -- confirms InvoiceUpdate genuinely reaches crud_invoice.update() and triggers a real recalculation, not just accepting the field."""
    ticket = make_full_ticket(db)
    invoice_resp = client.post("/invoices/", json={"ticket_id": ticket.id}, headers=agent_headers)
    invoice_id = invoice_resp.json()["id"]

    service_resp = client.post("/services/", json={"name": "Repair", "price": 100.0}, headers=superuser_headers)
    service_id = service_resp.json()["id"]
    client.post(f"/invoices/{invoice_id}/line-items", params={"service_id": service_id, "quantity": 1}, headers=agent_headers)

    tax_resp = client.post("/tax_rates", json={"name": "Sales Tax", "percentage": "10.00"}, headers=superuser_headers)
    tax_rate_id = tax_resp.json()["id"]

    update_resp = client.put(f"/invoices/{invoice_id}", json={"tax_rate_id": tax_rate_id}, headers=agent_headers)
    assert update_resp.status_code == 200, update_resp.text

    invoice_after = client.get(f"/invoices/{invoice_id}", headers=agent_headers).json()
    assert invoice_after["tax_rate_id"] == tax_rate_id
    assert float(invoice_after["tax_amount"]) == 10.0
    assert float(invoice_after["total"]) == 110.0


def test_invoices_crud(client, agent_headers, db):
    """Invoice creation starts empty (ticket_id only), same as Quote. Invoices are otherwise not deletable (financial record); this one is additionally blocked because it's marked paid -- see test_quotes_crud for the narrow empty/unsent/most-recent case where deletion succeeds."""
    from tests.factories import make_full_ticket
    ticket = make_full_ticket(db)

    create_resp = client.post("/invoices/", json={"ticket_id": ticket.id}, headers=agent_headers)
    assert create_resp.status_code == 200, create_resp.text
    invoice_id = create_resp.json()["id"]

    list_resp = client.get("/invoices/", headers=agent_headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == invoice_id for item in list_resp.json())

    get_resp = client.get(f"/invoices/{invoice_id}", headers=agent_headers)
    assert get_resp.status_code == 200

    # is_paid can no longer be set directly (see InvoiceUpdate) -- an
    # empty invoice's total defaults to 0, so recording any real
    # payment against it genuinely, correctly marks it paid.
    payment_resp = client.post("/payments/", json={"invoice_id": invoice_id, "amount": 0.01, "method": "cash"}, headers=agent_headers)
    assert payment_resp.status_code == 200, payment_resp.text

    get_after_payment_resp = client.get(f"/invoices/{invoice_id}", headers=agent_headers)
    assert get_after_payment_resp.json()["is_paid"] is True

    delete_resp = client.delete(f"/invoices/{invoice_id}", headers=agent_headers)
    assert delete_resp.status_code == 400
