# ER-ServiceDesk/tests/test_device_crud.py
"""
Covers Device CRUD, and its AuditLog coverage.
"""

from tests.factories import assert_crud_lifecycle, make_customer


def test_devices_crud(client, agent_headers, db):
    customer = make_customer(db)
    assert_crud_lifecycle(
        client, agent_headers, "/devices",
        {"customer_id": customer.id, "device_type": "Desktop"},
        {"brand": "Dell"},
        update_check_field="brand",
    )


def test_device_create_and_update_appear_in_audit_log(client, superuser_headers, db):
    """Regression test: device_service.create()/update() previously never logged to the audit trail at all -- only delete() did, so no device creation or edit ever showed up in the Audit Log."""
    customer = make_customer(db)

    create_resp = client.post("/devices/", json={"customer_id": customer.id, "device_type": "Laptop", "brand": "Dell", "model": "Latitude 5420"}, headers=superuser_headers)
    assert create_resp.status_code == 200, create_resp.text
    device_id = create_resp.json()["id"]

    update_resp = client.put(f"/devices/{device_id}", json={"brand": "HP"}, headers=superuser_headers)
    assert update_resp.status_code == 200, update_resp.text

    audit_resp = client.get("/audit_logs/", headers=superuser_headers)
    assert audit_resp.status_code == 200
    actions = [entry["action"] for entry in audit_resp.json() if entry["entity_type"] == "device" and entry["entity_id"] == device_id]
    assert "device_created" in actions
    assert "device_updated" in actions
