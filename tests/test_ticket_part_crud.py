# ER-ServiceDesk/tests/test_ticket_part_crud.py
"""
Covers TicketPartCRUD's get(), get_by_ticket(), and delete().
"""

from app.models.ticket import Ticket
from app.crud.ticket_part import crud_ticket_part
from app.schemas.ticket_part import TicketPartCreate
from tests.factories import make_full_ticket, make_ticket_dependencies


def _make_part(db, name="Test Part", sku="SKU-CRUD-TEST"):
    from app.models.part import Part
    part = Part(name=name, sku=sku)
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


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
    ticket = make_full_ticket(db)
    part = _make_part(db)
    tp = crud_ticket_part.create(db, TicketPartCreate(ticket_id=ticket.id, part_id=part.id, status="needed"))

    result = crud_ticket_part.get(db, tp.id)

    assert result.id == tp.id


def test_get_by_ticket_returns_only_that_tickets_own_parts(db):
    deps = make_ticket_dependencies(db)
    ticket_a = _second_ticket_for(db, deps, "Ticket A")
    ticket_b = _second_ticket_for(db, deps, "Ticket B")
    part = _make_part(db)
    tp_a = crud_ticket_part.create(db, TicketPartCreate(ticket_id=ticket_a.id, part_id=part.id, status="needed"))
    crud_ticket_part.create(db, TicketPartCreate(ticket_id=ticket_b.id, part_id=part.id, status="needed"))

    result = crud_ticket_part.get_by_ticket(db, ticket_a.id)

    assert len(result) == 1
    assert result[0].id == tp_a.id


def test_delete_genuinely_removes_the_record(db):
    ticket = make_full_ticket(db)
    part = _make_part(db)
    tp = crud_ticket_part.create(db, TicketPartCreate(ticket_id=ticket.id, part_id=part.id, status="needed"))
    tp_id = tp.id

    crud_ticket_part.delete(db, tp_id)

    assert crud_ticket_part.get(db, tp_id) is None
