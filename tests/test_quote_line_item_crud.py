# ER-ServiceDesk/tests/test_quote_line_item_crud.py
"""
Covers QuoteLineItemCRUD's get_by_quote() and delete()'s safe no-op
behavior for a nonexistent id -- create/update/delete-of-a-real-row
are already indirectly exercised via quote_service.py's own
add_line_item()/update_line_item()/remove_line_item(), but
get_by_quote() and the safe-no-op path aren't.
"""

from app.crud.quote_line_item import crud_quote_line_item
from tests.factories import make_full_ticket


def _make_quote_for(db, ticket_id):
    from app.models.quote import Quote
    quote = Quote(ticket_id=ticket_id, quote_number=1)
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return quote


def test_get_by_quote_returns_only_that_quotes_own_line_items(db):
    ticket = make_full_ticket(db)
    quote_a = _make_quote_for(db, ticket.id)

    item_1 = crud_quote_line_item.create(db, quote_a.id, quantity=1, unit_price=50, service_name="Diagnostic")
    item_2 = crud_quote_line_item.create(db, quote_a.id, quantity=2, unit_price=30, service_name="Cleanup")

    result = crud_quote_line_item.get_by_quote(db, quote_a.id)

    assert len(result) == 2
    assert {item.id for item in result} == {item_1.id, item_2.id}


def test_get_by_quote_returns_an_empty_list_for_a_quote_with_no_line_items(db):
    ticket = make_full_ticket(db)
    quote = _make_quote_for(db, ticket.id)
    assert crud_quote_line_item.get_by_quote(db, quote.id) == []


def test_delete_of_a_nonexistent_id_is_a_safe_no_op(db):
    crud_quote_line_item.delete(db, id=999999)  # must not raise


def test_get_returns_the_real_record_by_id(db):
    ticket = make_full_ticket(db)
    quote = _make_quote_for(db, ticket.id)
    item = crud_quote_line_item.create(db, quote.id, quantity=1, unit_price=50, service_name="Diagnostic")

    result = crud_quote_line_item.get(db, item.id)

    assert result.id == item.id
    assert result.service_name == "Diagnostic"


def test_get_returns_none_for_a_nonexistent_id(db):
    assert crud_quote_line_item.get(db, id=999999) is None


def test_update_genuinely_changes_the_quantity(db):
    from app.schemas.quote_line_item import QuoteLineItemUpdate
    ticket = make_full_ticket(db)
    quote = _make_quote_for(db, ticket.id)
    item = crud_quote_line_item.create(db, quote.id, quantity=1, unit_price=50, service_name="Diagnostic")

    updated = crud_quote_line_item.update(db, item, QuoteLineItemUpdate(quantity=5))

    assert updated.quantity == 5


def test_delete_of_an_existing_record_genuinely_removes_it(db):
    ticket = make_full_ticket(db)
    quote = _make_quote_for(db, ticket.id)
    item = crud_quote_line_item.create(db, quote.id, quantity=1, unit_price=50, service_name="Diagnostic")
    item_id = item.id

    crud_quote_line_item.delete(db, item_id)

    assert crud_quote_line_item.get(db, item_id) is None
