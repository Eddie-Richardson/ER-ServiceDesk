# ER-ServiceDesk/tests/test_part_crud.py
"""
Covers Part CRUD -- the duplicate-SKU rejection, full lifecycle, and
AuditLog coverage.
"""

from tests.factories import assert_crud_lifecycle, make_location


def test_duplicate_sku_rejected(client, agent_headers):
    """Creating a second part with the same SKU is rejected."""
    payload = {"name": "SSD 500GB", "sku": "SKU-DUPLICATE-001"}

    first = client.post("/inventory/parts/", json=payload, headers=agent_headers)
    assert first.status_code == 200

    second = client.post("/inventory/parts/", json=payload, headers=agent_headers)
    assert second.status_code == 400


def test_parts_crud(client, agent_headers, db):
    location = make_location(db)
    assert_crud_lifecycle(
        client, agent_headers, "/inventory/parts",
        {"name": "SATA Cable", "sku": "SATA-001", "reorder_threshold": 2, "locations": [{"location_id": location.id, "quantity": 10}]},
        {"reorder_threshold": 3},
        update_check_field="reorder_threshold",
    )


def test_create_and_update_appear_in_audit_log(client, superuser_headers, db):
    """Regression test: part_service previously had zero AuditLog coverage at all -- no part creation or edit ever showed up in the Audit Log."""
    location = make_location(db)

    create_resp = client.post(
        "/inventory/parts",
        json={"name": "SATA Cable", "sku": "SATA-AUDIT-001", "locations": [{"location_id": location.id, "quantity": 10}]},
        headers=superuser_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    part_id = create_resp.json()["id"]

    update_resp = client.put(f"/inventory/parts/{part_id}", json={"reorder_threshold": 5}, headers=superuser_headers)
    assert update_resp.status_code == 200, update_resp.text

    audit_resp = client.get("/audit_logs/", headers=superuser_headers)
    assert audit_resp.status_code == 200
    actions = [entry["action"] for entry in audit_resp.json() if entry["entity_type"] == "part" and entry["entity_id"] == part_id]
    assert "part_created" in actions
    assert "part_updated" in actions
