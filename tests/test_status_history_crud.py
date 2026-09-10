# ER-ServiceDesk/tests/test_status_history_crud.py
"""
Covers StatusHistoryCRUD.get() and its real ticket_id filter on
get_multi().
"""

from app.models.ticket import Ticket
from app.crud.status_history import crud_status_history
from app.schemas.status_history import StatusHistoryCreate
from tests.factories import make_plain_user, make_ticket_dependencies


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


def test_get_returns_the_real_record_by_id(db):
    deps = make_ticket_dependencies(db)
    ticket = _second_ticket_for(db, deps, "Ticket")
    actor = make_plain_user(db)
    entry = crud_status_history.create(db, StatusHistoryCreate(ticket_id=ticket.id, status_id=deps["status"].id, changed_by=actor.id))

    result = crud_status_history.get(db, entry.id)

    assert result.id == entry.id


def test_get_multi_filters_by_ticket_id(db):
    deps = make_ticket_dependencies(db)
    ticket_a = _second_ticket_for(db, deps, "Ticket A")
    ticket_b = _second_ticket_for(db, deps, "Ticket B")
    actor = make_plain_user(db)
    crud_status_history.create(db, StatusHistoryCreate(ticket_id=ticket_a.id, status_id=deps["status"].id, changed_by=actor.id))
    crud_status_history.create(db, StatusHistoryCreate(ticket_id=ticket_b.id, status_id=deps["status"].id, changed_by=actor.id))

    result = crud_status_history.get_multi(db, ticket_id=ticket_a.id)

    assert len(result) == 1
    assert result[0].ticket_id == ticket_a.id


def test_is_read_only(client, agent_headers, db):
    """StatusHistory is a deliberately immutable, internally-generated record (created only when a ticket's status actually changes) -- no create route exists via the API, only listing."""
    from tests.factories import make_ticket_status, make_full_ticket, make_plain_user
    ticket = make_full_ticket(db)
    status2 = make_ticket_status(db, name="Closed")
    user = make_plain_user(db)

    list_resp = client.get("/status_histories/", headers=agent_headers)
    assert list_resp.status_code == 200

    create_resp = client.post("/status_histories/", json={"ticket_id": ticket.id, "status_id": status2.id, "changed_by": user.id}, headers=agent_headers)
    assert create_resp.status_code == 405
