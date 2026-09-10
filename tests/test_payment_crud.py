# ER-ServiceDesk/tests/test_payment_crud.py
"""
Covers Payment CRUD. Editing a recorded payment in place is
deliberately not supported -- it would leave no trail and wouldn't
trigger a corrected receipt. Delete-and-re-record is the correct
pattern instead; update is confirmed rejected.
"""

from tests.factories import make_full_ticket, make_invoice


def test_payments_crud(client, agent_headers, db):
    ticket = make_full_ticket(db)
    invoice = make_invoice(db, ticket.id)

    create_resp = client.post("/payments/", json={"invoice_id": invoice.id, "amount": 200.0, "method": "cash"}, headers=agent_headers)
    assert create_resp.status_code == 200, create_resp.text
    payment_id = create_resp.json()["id"]

    list_resp = client.get("/payments/", headers=agent_headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == payment_id for item in list_resp.json())

    update_resp = client.put(f"/payments/{payment_id}", json={"method": "credit_card"}, headers=agent_headers)
    assert update_resp.status_code == 405

    delete_resp = client.delete(f"/payments/{payment_id}", headers=agent_headers)
    assert delete_resp.status_code in (200, 204)
