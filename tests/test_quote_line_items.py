# ER-ServiceDesk/tests/test_quote_line_items.py
"""
Covers QuoteService's line-item management -- add_line_item()'s
service/part-not-found rejections, update_line_item() genuinely
working, and remove_line_item()'s safe no-op for a nonexistent id.
"""

import pytest
from fastapi import HTTPException

from app.services.quote_service import quote_service
from app.crud.audit_log import crud_audit_log
from tests.factories import make_full_ticket, make_plain_user


def _make_quote(db, ticket_id, actor_id):
    from app.schemas.quote import QuoteCreate
    return quote_service.create(db, QuoteCreate(ticket_id=ticket_id), current_user_id=actor_id)


def test_add_line_item_rejects_a_nonexistent_service_id(db):
    actor_id = make_plain_user(db).id
    ticket = make_full_ticket(db)
    quote = _make_quote(db, ticket.id, actor_id)

    with pytest.raises(HTTPException) as exc_info:
        quote_service.add_line_item(db, quote.id, quantity=1, current_user_id=actor_id, service_id=999999)
    assert exc_info.value.status_code == 404


def test_add_line_item_rejects_a_nonexistent_part_id(db):
    actor_id = make_plain_user(db).id
    ticket = make_full_ticket(db)
    quote = _make_quote(db, ticket.id, actor_id)

    with pytest.raises(HTTPException) as exc_info:
        quote_service.add_line_item(db, quote.id, quantity=1, current_user_id=actor_id, part_id=999999)
    assert exc_info.value.status_code == 404


def test_update_line_item_genuinely_changes_the_quantity_and_logs_it(db):
    actor_id = make_plain_user(db).id
    ticket = make_full_ticket(db)
    quote = _make_quote(db, ticket.id, actor_id)
    from app.services.service_service import service_service
    from app.schemas.service import ServiceCreate
    service = service_service.create(db, ServiceCreate(name="Diagnostic", price=50), current_user_id=actor_id)
    line_item = quote_service.add_line_item(db, quote.id, quantity=1, current_user_id=actor_id, service_id=service.id)

    from app.schemas.quote_line_item import QuoteLineItemUpdate
    updated = quote_service.update_line_item(db, line_item.id, QuoteLineItemUpdate(quantity=3), current_user_id=actor_id)

    assert updated.quantity == 3
    entries = crud_audit_log.get_multi(db, limit=500)
    assert any(e.action == "quote_line_item_updated" for e in entries)


def test_remove_line_item_on_a_nonexistent_id_is_a_safe_no_op(db):
    actor_id = make_plain_user(db).id
    quote_service.remove_line_item(db, line_item_id=999999, current_user_id=actor_id)  # must not raise
