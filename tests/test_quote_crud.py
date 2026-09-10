# ER-ServiceDesk/tests/test_quote_crud.py
"""
Covers QuoteCRUD.get_by_ticket() directly. QuoteCRUD.create() is
deliberately not tested here -- confirmed dead code in production:
quote_service.create() constructs Quote directly and never calls it.
"""

from app.models.quote import Quote
from app.models.ticket import Ticket
from app.crud.quote import crud_quote
from tests.factories import make_ticket_dependencies


def _second_ticket_for(db, deps, title="Second ticket"):
    """A second, real ticket sharing the same customer/device -- avoids the unique-email conflict make_full_ticket() would hit if called twice."""
    ticket = Ticket(
        customer_id=deps["customer"].id, device_id=deps["device"].id,
        category_id=deps["category"].id, type_id=deps["type"].id,
        status_id=deps["status"].id, title=title, priority="normal",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def test_get_by_ticket_returns_only_that_tickets_own_quotes(db):
    deps = make_ticket_dependencies(db)
    ticket_a = _second_ticket_for(db, deps, "Ticket A")
    ticket_b = _second_ticket_for(db, deps, "Ticket B")
    quote_a = Quote(ticket_id=ticket_a.id, quote_number=1)
    quote_b = Quote(ticket_id=ticket_b.id, quote_number=2)
    db.add_all([quote_a, quote_b])
    db.commit()

    result = crud_quote.get_by_ticket(db, ticket_a.id)

    assert len(result) == 1
    assert result[0].ticket_id == ticket_a.id


def test_quotes_crud(client, agent_headers, db):
    """Quote creation starts empty (ticket_id only) -- line items get added separately, one at a time, via their own endpoint. Quotes are otherwise not deletable (financial record), except for the one narrow case exercised here: an empty, never-sent, never-converted quote that's also still the most recently created one."""
    from tests.factories import make_full_ticket, make_discount
    ticket = make_full_ticket(db)
    discount = make_discount(db)

    create_resp = client.post("/quotes/", json={"ticket_id": ticket.id}, headers=agent_headers)
    assert create_resp.status_code == 200, create_resp.text
    quote_id = create_resp.json()["id"]

    list_resp = client.get("/quotes/", headers=agent_headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == quote_id for item in list_resp.json())

    get_resp = client.get(f"/quotes/{quote_id}", headers=agent_headers)
    assert get_resp.status_code == 200

    update_resp = client.put(f"/quotes/{quote_id}", json={"discount_id": discount.id}, headers=agent_headers)
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["discount_id"] == discount.id

    delete_resp = client.delete(f"/quotes/{quote_id}", headers=agent_headers)
    assert delete_resp.status_code == 200, delete_resp.text

    get_after_delete_resp = client.get(f"/quotes/{quote_id}", headers=agent_headers)
    assert get_after_delete_resp.status_code == 404
