# ER-ServiceDesk/tests/test_invoice_line_items.py
"""
Covers InvoiceService's line-item management (add_line_item(),
update_line_item(), remove_line_item()) -- the largest genuinely
untested chunk of invoice_service.py. The existing test_invoices_crud
only ever creates an empty invoice; none of its real, non-obvious
behavior around adding/editing/removing a line item -- especially the
real inventory deduction/restoration a part line item triggers -- was
covered before this.
"""

from tests.factories import make_full_ticket, make_location


def _setup_deduction_location(client, superuser_headers, db):
    """add_line_item() hard-requires a configured part_deduction_location_id -- normally set by seed_data(), which the test database never runs."""
    location = make_location(db)
    resp = client.put("/system_settings/by-key/part_deduction_location_id", json={"value": str(location.id)}, headers=superuser_headers)
    assert resp.status_code == 200, resp.text
    return location


def test_adding_a_service_line_item_never_touches_inventory(client, agent_headers, superuser_headers, db):
    """A service line item is pure labor/diagnostic time -- confirms it genuinely never creates or touches any PartLocation row at all."""
    ticket = make_full_ticket(db)
    invoice_resp = client.post("/invoices/", json={"ticket_id": ticket.id}, headers=agent_headers)
    invoice_id = invoice_resp.json()["id"]

    service_resp = client.post("/services/", json={"name": "Diagnostic", "price": 50.0}, headers=superuser_headers)
    service_id = service_resp.json()["id"]

    add_resp = client.post(f"/invoices/{invoice_id}/line-items", params={"service_id": service_id, "quantity": 1}, headers=agent_headers)
    assert add_resp.status_code == 200, add_resp.text
    assert add_resp.json()["service_name"] == "Diagnostic"

    from app.models.part_location import PartLocation
    assert db.query(PartLocation).count() == 0

    invoice_get = client.get(f"/invoices/{invoice_id}", headers=agent_headers)
    assert float(invoice_get.json()["total"]) == 50.0


def test_adding_a_part_line_item_genuinely_deducts_real_inventory(client, agent_headers, superuser_headers, db):
    """The core, real behavior a part line item triggers -- actual stock at the configured deduction location goes down by the quantity billed."""
    ticket = make_full_ticket(db)
    location = _setup_deduction_location(client, superuser_headers, db)

    part_resp = client.post("/inventory/parts/", json={"name": "SSD 500GB", "sku": "SKU-LINE-001", "selling_price": 80.0, "locations": [{"location_id": location.id, "quantity": 10}]}, headers=superuser_headers)
    part_id = part_resp.json()["id"]

    invoice_resp = client.post("/invoices/", json={"ticket_id": ticket.id}, headers=agent_headers)
    invoice_id = invoice_resp.json()["id"]

    add_resp = client.post(f"/invoices/{invoice_id}/line-items", params={"part_id": part_id, "quantity": 2}, headers=agent_headers)
    assert add_resp.status_code == 200, add_resp.text

    part_get = client.get(f"/inventory/parts/{part_id}", headers=agent_headers)
    remaining = next(loc["quantity"] for loc in part_get.json()["locations"] if loc["location_id"] == location.id)
    assert remaining == 8  # started at 10, billed 2


def test_adding_a_line_item_requires_exactly_one_of_service_or_part(client, agent_headers, db):
    """Neither, and both, are genuinely rejected -- not silently defaulting to one or the other."""
    ticket = make_full_ticket(db)
    invoice_resp = client.post("/invoices/", json={"ticket_id": ticket.id}, headers=agent_headers)
    invoice_id = invoice_resp.json()["id"]

    neither_resp = client.post(f"/invoices/{invoice_id}/line-items", params={"quantity": 1}, headers=agent_headers)
    assert neither_resp.status_code == 400

    both_resp = client.post(f"/invoices/{invoice_id}/line-items", params={"service_id": 1, "part_id": 1, "quantity": 1}, headers=agent_headers)
    assert both_resp.status_code == 400


def test_adding_a_part_with_no_selling_price_is_genuinely_rejected(client, agent_headers, superuser_headers, db):
    """A part that's never had a selling price configured can't be billed -- confirms the real, specific error message, not just a generic failure."""
    ticket = make_full_ticket(db)
    _setup_deduction_location(client, superuser_headers, db)

    part_resp = client.post("/inventory/parts/", json={"name": "Unpriced Part", "sku": "SKU-LINE-002"}, headers=superuser_headers)
    part_id = part_resp.json()["id"]

    invoice_resp = client.post("/invoices/", json={"ticket_id": ticket.id}, headers=agent_headers)
    invoice_id = invoice_resp.json()["id"]

    add_resp = client.post(f"/invoices/{invoice_id}/line-items", params={"part_id": part_id, "quantity": 1}, headers=agent_headers)
    assert add_resp.status_code == 400
    assert "no selling price" in add_resp.json()["error"]["message"].lower()


def test_increasing_a_part_line_items_quantity_deducts_the_additional_amount(client, agent_headers, superuser_headers, db):
    """Editing a part line's quantity upward genuinely deducts only the delta, not the full new quantity again."""
    ticket = make_full_ticket(db)
    location = _setup_deduction_location(client, superuser_headers, db)

    part_resp = client.post("/inventory/parts/", json={"name": "RAM Stick", "sku": "SKU-LINE-003", "selling_price": 40.0, "locations": [{"location_id": location.id, "quantity": 10}]}, headers=superuser_headers)
    part_id = part_resp.json()["id"]

    invoice_resp = client.post("/invoices/", json={"ticket_id": ticket.id}, headers=agent_headers)
    invoice_id = invoice_resp.json()["id"]

    add_resp = client.post(f"/invoices/{invoice_id}/line-items", params={"part_id": part_id, "quantity": 1}, headers=agent_headers)
    line_item_id = add_resp.json()["id"]

    update_resp = client.put(f"/invoices/line-items/{line_item_id}", json={"quantity": 3}, headers=agent_headers)
    assert update_resp.status_code == 200, update_resp.text

    part_get = client.get(f"/inventory/parts/{part_id}", headers=agent_headers)
    remaining = next(loc["quantity"] for loc in part_get.json()["locations"] if loc["location_id"] == location.id)
    assert remaining == 7  # started at 10, billed 1, then increased to 3 total (delta of 2 more deducted)


def test_decreasing_a_part_line_items_quantity_restores_the_difference(client, agent_headers, superuser_headers, db):
    """Editing a part line's quantity downward genuinely restores only the difference back to inventory."""
    ticket = make_full_ticket(db)
    location = _setup_deduction_location(client, superuser_headers, db)

    part_resp = client.post("/inventory/parts/", json={"name": "Thermal Paste", "sku": "SKU-LINE-004", "selling_price": 10.0, "locations": [{"location_id": location.id, "quantity": 10}]}, headers=superuser_headers)
    part_id = part_resp.json()["id"]

    invoice_resp = client.post("/invoices/", json={"ticket_id": ticket.id}, headers=agent_headers)
    invoice_id = invoice_resp.json()["id"]

    add_resp = client.post(f"/invoices/{invoice_id}/line-items", params={"part_id": part_id, "quantity": 5}, headers=agent_headers)
    line_item_id = add_resp.json()["id"]

    update_resp = client.put(f"/invoices/line-items/{line_item_id}", json={"quantity": 2}, headers=agent_headers)
    assert update_resp.status_code == 200, update_resp.text

    part_get = client.get(f"/inventory/parts/{part_id}", headers=agent_headers)
    remaining = next(loc["quantity"] for loc in part_get.json()["locations"] if loc["location_id"] == location.id)
    assert remaining == 8  # started at 10, billed 5 (5 left), reduced to 2 (3 restored -> 8 left)


def test_removing_a_part_line_item_restores_its_full_deducted_inventory(client, agent_headers, superuser_headers, db):
    """Deleting a part line item genuinely gives the full quantity back, not just adjusting the invoice total."""
    ticket = make_full_ticket(db)
    location = _setup_deduction_location(client, superuser_headers, db)

    part_resp = client.post("/inventory/parts/", json={"name": "Fan", "sku": "SKU-LINE-005", "selling_price": 15.0, "locations": [{"location_id": location.id, "quantity": 10}]}, headers=superuser_headers)
    part_id = part_resp.json()["id"]

    invoice_resp = client.post("/invoices/", json={"ticket_id": ticket.id}, headers=agent_headers)
    invoice_id = invoice_resp.json()["id"]

    add_resp = client.post(f"/invoices/{invoice_id}/line-items", params={"part_id": part_id, "quantity": 4}, headers=agent_headers)
    line_item_id = add_resp.json()["id"]

    remove_resp = client.delete(f"/invoices/line-items/{line_item_id}", headers=agent_headers)
    assert remove_resp.status_code == 200

    part_get = client.get(f"/inventory/parts/{part_id}", headers=agent_headers)
    remaining = next(loc["quantity"] for loc in part_get.json()["locations"] if loc["location_id"] == location.id)
    assert remaining == 10  # fully restored to the original amount

    invoice_get = client.get(f"/invoices/{invoice_id}", headers=agent_headers)
    assert float(invoice_get.json()["total"]) == 0.0


def test_line_item_actions_each_produce_their_own_distinct_audit_log_entry(client, agent_headers, superuser_headers, db):
    """Adding, editing, and removing a line item are three separate, distinctly-named AuditLog actions, not one generic 'invoice_updated' entry."""
    ticket = make_full_ticket(db)
    location = _setup_deduction_location(client, superuser_headers, db)

    part_resp = client.post("/inventory/parts/", json={"name": "Keyboard", "sku": "SKU-LINE-006", "selling_price": 25.0, "locations": [{"location_id": location.id, "quantity": 5}]}, headers=superuser_headers)
    part_id = part_resp.json()["id"]

    invoice_resp = client.post("/invoices/", json={"ticket_id": ticket.id}, headers=agent_headers)
    invoice_id = invoice_resp.json()["id"]

    add_resp = client.post(f"/invoices/{invoice_id}/line-items", params={"part_id": part_id, "quantity": 1}, headers=agent_headers)
    line_item_id = add_resp.json()["id"]

    client.put(f"/invoices/line-items/{line_item_id}", json={"quantity": 2}, headers=agent_headers)
    client.delete(f"/invoices/line-items/{line_item_id}", headers=agent_headers)

    audit_resp = client.get("/audit_logs/", headers=superuser_headers)
    actions = [entry["action"] for entry in audit_resp.json() if entry["entity_type"] == "ticket" and entry["entity_id"] == ticket.id]

    assert "invoice_line_item_added" in actions
    assert "invoice_line_item_updated" in actions
    assert "invoice_line_item_removed" in actions


def test_adding_a_line_item_rejects_a_nonexistent_service_id(client, agent_headers, db):
    ticket = make_full_ticket(db)
    invoice_resp = client.post("/invoices/", json={"ticket_id": ticket.id}, headers=agent_headers)
    invoice_id = invoice_resp.json()["id"]

    resp = client.post(f"/invoices/{invoice_id}/line-items", params={"service_id": 999999, "quantity": 1}, headers=agent_headers)
    assert resp.status_code == 404


def test_adding_a_line_item_rejects_a_nonexistent_part_id(client, agent_headers, db):
    ticket = make_full_ticket(db)
    invoice_resp = client.post("/invoices/", json={"ticket_id": ticket.id}, headers=agent_headers)
    invoice_id = invoice_resp.json()["id"]

    resp = client.post(f"/invoices/{invoice_id}/line-items", params={"part_id": 999999, "quantity": 1}, headers=agent_headers)
    assert resp.status_code == 404


def test_removing_a_line_item_on_a_nonexistent_id_is_a_safe_no_op(db):
    from app.services.invoice_service import invoice_service
    from tests.factories import make_plain_user
    invoice_service.remove_line_item(db, line_item_id=999999, current_user_id=make_plain_user(db).id)  # must not raise
