# ER-ServiceDesk/tests/test_ticket_part_shipping_info.py
# Tests for TicketPart's carrier/tracking_number fields.
"""
Covers the manually-entered shipping-lookup fields on TicketPart: a tech
enters carrier + tracking_number by hand (from the retailer's shipping
confirmation email) so anyone looking at the ticket knows exactly where
to check for current status, without this app trying to auto-parse or
guess at it.
"""

from app.models.part import Part
from tests.factories import make_ticket_dependencies


def _make_ticket_and_part(client, db, deps, agent_headers):
    from app.models.ticket import Ticket

    ticket = Ticket(
        customer_id=deps["customer"].id,
        device_id=deps["device"].id,
        category_id=deps["category"].id,
        type_id=deps["type"].id,
        status_id=deps["status"].id,
        title="Screen replacement",
        priority="normal",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    part = Part(name="Replacement Screen", sku="SKU-SCREEN-001")
    db.add(part)
    db.commit()
    db.refresh(part)

    return ticket, part


def test_ticket_part_stores_carrier_and_tracking_number(client, db, agent_headers):
    """Creating a TicketPart with carrier/tracking_number persists and returns both."""
    deps = make_ticket_dependencies(db)
    ticket, part = _make_ticket_and_part(client, db, deps, agent_headers)

    response = client.post(
        "/ticket_parts/",
        json={
            "ticket_id": ticket.id,
            "part_id": part.id,
            "quantity_needed": 1,
            "status": "shipped",
            "carrier": "UPS",
            "tracking_number": "1Z999AA10123456784",
        },
        headers=agent_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "shipped"
    assert body["carrier"] == "UPS"
    assert body["tracking_number"] == "1Z999AA10123456784"


def test_ticket_part_carrier_and_tracking_number_default_to_none(client, db, agent_headers):
    """A TicketPart created without shipping info leaves carrier/tracking_number null, not required."""
    deps = make_ticket_dependencies(db)
    ticket, part = _make_ticket_and_part(client, db, deps, agent_headers)

    response = client.post(
        "/ticket_parts/",
        json={"ticket_id": ticket.id, "part_id": part.id, "quantity_needed": 1},
        headers=agent_headers,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["carrier"] is None
    assert body["tracking_number"] is None


def test_ticket_part_shipping_info_can_be_updated_as_it_becomes_available(client, db, agent_headers):
    """
    Carrier/tracking_number are typically unknown at order time and filled
    in later once the retailer's shipping confirmation arrives -- update
    should support adding them after the fact.
    """
    deps = make_ticket_dependencies(db)
    ticket, part = _make_ticket_and_part(client, db, deps, agent_headers)

    created = client.post(
        "/ticket_parts/",
        json={"ticket_id": ticket.id, "part_id": part.id, "status": "ordered"},
        headers=agent_headers,
    ).json()

    updated = client.put(
        f"/ticket_parts/{created['id']}",
        json={"status": "shipped", "carrier": "FedEx", "tracking_number": "789123456"},
        headers=agent_headers,
    )

    assert updated.status_code == 200
    body = updated.json()
    assert body["status"] == "shipped"
    assert body["carrier"] == "FedEx"
    assert body["tracking_number"] == "789123456"
