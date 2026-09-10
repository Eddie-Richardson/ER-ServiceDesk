# ER-ServiceDesk/tests/test_quote_service.py
"""
Covers the real gaps in quote_service.py not already exercised by
test_quotes_crud/test_convert_quote_to_invoice: the key property that
distinguishes a quote's line items from an invoice's (never touches
real inventory), delete()'s four distinct rejection conditions, and
convert_to_invoice()'s double-conversion rejection plus its actual,
real inventory deduction for part line items during conversion.
"""

import pytest
from fastapi import HTTPException

from app.services.quote_service import quote_service
from app.models.part_location import PartLocation
from tests.factories import make_full_ticket, make_location, make_plain_user


def _make_quote(db, ticket_id, actor_id):
    from app.schemas.quote import QuoteCreate
    return quote_service.create(db, QuoteCreate(ticket_id=ticket_id), current_user_id=actor_id)


def test_add_line_item_never_touches_real_inventory(db, client, superuser_headers, agent_headers):
    actor_id = make_plain_user(db).id
    ticket = make_full_ticket(db)
    location = make_location(db)

    part_resp = client.post("/inventory/parts/", json={"name": "Quote Part", "sku": "SKU-QUOTE-001", "selling_price": 50.0, "locations": [{"location_id": location.id, "quantity": 10}]}, headers=superuser_headers)
    part_id = part_resp.json()["id"]

    quote = _make_quote(db, ticket.id, actor_id)
    quote_service.add_line_item(db, quote.id, quantity=3, current_user_id=actor_id, part_id=part_id)

    remaining = db.query(PartLocation).filter_by(part_id=part_id, location_id=location.id).first().quantity
    assert remaining == 10  # genuinely untouched -- a quote is not a real transaction yet


def test_delete_rejects_a_quote_with_line_items(db):
    actor_id = make_plain_user(db).id
    ticket = make_full_ticket(db)
    quote = _make_quote(db, ticket.id, actor_id)
    from app.services.service_service import service_service
    from app.schemas.service import ServiceCreate
    service = service_service.create(db, ServiceCreate(name="Diagnostic", price=50), current_user_id=actor_id)
    quote_service.add_line_item(db, quote.id, quantity=1, current_user_id=actor_id, service_id=service.id)

    with pytest.raises(HTTPException) as exc_info:
        quote_service.delete(db, quote.id, current_user_id=actor_id)
    assert exc_info.value.status_code == 400


def test_delete_rejects_an_already_sent_quote(db):
    from datetime import datetime, UTC
    actor_id = make_plain_user(db).id
    ticket = make_full_ticket(db)
    quote = _make_quote(db, ticket.id, actor_id)
    quote.quote_sent_at = datetime.now(UTC)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        quote_service.delete(db, quote.id, current_user_id=actor_id)
    assert exc_info.value.status_code == 400


def test_delete_rejects_a_quote_thats_not_the_most_recently_created(db):
    """Deleting anything but the latest quote number would leave a permanent gap in the sequence."""
    actor_id = make_plain_user(db).id
    ticket = make_full_ticket(db)
    older_quote = _make_quote(db, ticket.id, actor_id)
    _make_quote(db, ticket.id, actor_id)  # a newer one now exists

    with pytest.raises(HTTPException) as exc_info:
        quote_service.delete(db, older_quote.id, current_user_id=actor_id)
    assert exc_info.value.status_code == 400


def test_delete_succeeds_for_an_untouched_most_recent_empty_quote(db):
    actor_id = make_plain_user(db).id
    ticket = make_full_ticket(db)
    quote = _make_quote(db, ticket.id, actor_id)
    quote_id = quote.id

    quote_service.delete(db, quote_id, current_user_id=actor_id)

    assert quote_service.get(db, quote_id) is None


def test_convert_to_invoice_rejects_a_quote_already_converted(db):
    actor_id = make_plain_user(db).id
    ticket = make_full_ticket(db)
    quote = _make_quote(db, ticket.id, actor_id)

    quote_service.convert_to_invoice(db, quote.id, current_user_id=actor_id)

    with pytest.raises(HTTPException) as exc_info:
        quote_service.convert_to_invoice(db, quote.id, current_user_id=actor_id)
    assert exc_info.value.status_code == 400


def test_convert_to_invoice_genuinely_deducts_real_inventory_for_part_line_items(db, client, superuser_headers, agent_headers):
    """The real, meaningful moment inventory actually leaves stock for a quoted part -- at conversion time, not when it was merely quoted."""
    actor_id = make_plain_user(db).id
    ticket = make_full_ticket(db)
    location = make_location(db)
    location_setting_resp = client.put("/system_settings/by-key/part_deduction_location_id", json={"value": str(location.id)}, headers=superuser_headers)
    assert location_setting_resp.status_code == 200, location_setting_resp.text

    part_resp = client.post("/inventory/parts/", json={"name": "Convert Part", "sku": "SKU-QUOTE-002", "selling_price": 30.0, "locations": [{"location_id": location.id, "quantity": 10}]}, headers=superuser_headers)
    part_id = part_resp.json()["id"]

    quote = _make_quote(db, ticket.id, actor_id)
    quote_service.add_line_item(db, quote.id, quantity=4, current_user_id=actor_id, part_id=part_id)

    remaining_before = db.query(PartLocation).filter_by(part_id=part_id, location_id=location.id).first().quantity
    assert remaining_before == 10  # still untouched before conversion

    quote_service.convert_to_invoice(db, quote.id, current_user_id=actor_id)

    remaining_after = db.query(PartLocation).filter_by(part_id=part_id, location_id=location.id).first().quantity
    assert remaining_after == 6  # genuinely deducted only now, at conversion


def test_delete_returns_404_for_a_nonexistent_quote(db):
    actor_id = make_plain_user(db).id
    with pytest.raises(HTTPException) as exc_info:
        quote_service.delete(db, id=999999, current_user_id=actor_id)
    assert exc_info.value.status_code == 404


def test_delete_rejects_a_quote_already_converted_to_an_invoice(db):
    actor_id = make_plain_user(db).id
    ticket = make_full_ticket(db)
    quote = _make_quote(db, ticket.id, actor_id)
    quote_service.convert_to_invoice(db, quote.id, current_user_id=actor_id)

    with pytest.raises(HTTPException) as exc_info:
        quote_service.delete(db, quote.id, current_user_id=actor_id)
    assert exc_info.value.status_code == 400


def test_convert_to_invoice_returns_404_for_a_nonexistent_quote(db):
    actor_id = make_plain_user(db).id
    with pytest.raises(HTTPException) as exc_info:
        quote_service.convert_to_invoice(db, quote_id=999999, current_user_id=actor_id)
    assert exc_info.value.status_code == 404


def test_convert_quote_to_invoice(client, agent_headers, superuser_headers, db):
    """
    Converting a quote copies every line item over to the new invoice --
    both service-based and part-based ones -- along with the discount/tax
    selection and totals, then links the quote to the invoice it became.
    Regression test: a real positional-argument mismatch in the copy loop
    (service_id/service_name landing in the quantity/unit_price slots,
    and part-based line items never being copied at all) shipped
    undetected since nothing exercised this path before. Also covers a
    second, separate gap found afterward: convert_to_invoice() copied
    line item data but never triggered inventory deduction for
    part-based ones, since it bypasses add_line_item() entirely --
    only the direct-invoice-line-item path deducted stock before this.
    """
    ticket = make_full_ticket(db)
    location = make_location(db)
    location_setting_resp = client.put("/system_settings/by-key/part_deduction_location_id", json={"value": str(location.id)}, headers=superuser_headers)
    assert location_setting_resp.status_code == 200, location_setting_resp.text

    service_resp = client.post("/services/", json={"name": "Diagnostic", "price": 50.0}, headers=superuser_headers)
    assert service_resp.status_code == 200, service_resp.text
    service_id = service_resp.json()["id"]

    part_resp = client.post("/inventory/parts/", json={"name": "SSD 500GB", "sku": "SKU-CONVERT-001", "selling_price": 80.0}, headers=superuser_headers)
    assert part_resp.status_code == 200, part_resp.text
    part_id = part_resp.json()["id"]

    quote_resp = client.post("/quotes/", json={"ticket_id": ticket.id}, headers=agent_headers)
    assert quote_resp.status_code == 200, quote_resp.text
    quote_id = quote_resp.json()["id"]

    add_service_resp = client.post(f"/quotes/{quote_id}/line-items", params={"service_id": service_id, "quantity": 1}, headers=agent_headers)
    assert add_service_resp.status_code == 200, add_service_resp.text

    add_part_resp = client.post(f"/quotes/{quote_id}/line-items", params={"part_id": part_id, "quantity": 2}, headers=agent_headers)
    assert add_part_resp.status_code == 200, add_part_resp.text

    convert_resp = client.post(f"/quotes/{quote_id}/convert-to-invoice", headers=agent_headers)
    assert convert_resp.status_code == 200, convert_resp.text
    invoice = convert_resp.json()
    invoice_id = invoice["id"]

    invoice_line_items = invoice["line_items"]
    assert len(invoice_line_items) == 2

    service_line = next(li for li in invoice_line_items if li["service_id"] == service_id)
    assert service_line["service_name"] == "Diagnostic"
    assert service_line["quantity"] == 1
    assert float(service_line["unit_price"]) == 50.0
    assert service_line["part_id"] is None

    part_line = next(li for li in invoice_line_items if li["part_id"] == part_id)
    assert part_line["part_name"] == "SSD 500GB"
    assert part_line["quantity"] == 2
    assert float(part_line["unit_price"]) == 80.0
    assert part_line["service_id"] is None

    quote_after_resp = client.get(f"/quotes/{quote_id}", headers=agent_headers)
    quote_after = quote_after_resp.json()
    assert quote_after["converted_invoice_id"] == invoice_id
    assert quote_after["converted_invoice_number"] == invoice["invoice_number"]

    part_after_resp = client.get(f"/inventory/parts/{part_id}", headers=agent_headers)
    assert part_after_resp.status_code == 200
    part_location = next(loc for loc in part_after_resp.json()["locations"] if loc["location_id"] == location.id)
    assert part_location["quantity"] == -2  # started at 0 (no initial stock breakdown), 2 units deducted
