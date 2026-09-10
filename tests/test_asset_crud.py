# ER-ServiceDesk/tests/test_asset_crud.py
"""
Covers Asset CRUD -- the duplicate-serial-number rejection, full
lifecycle (Assets intentionally deviate from the generic CRUD response
shape: wrapped create response, paginated list response, so this is
tested directly rather than via the generic helper), and AuditLog
coverage.
"""


def test_duplicate_serial_number_rejected(client, agent_headers):
    """Creating a second asset with the same serial number is rejected."""
    payload = {"name": "Dell Laptop", "serial_number": "SN-DUPLICATE-001"}

    first = client.post("/inventory/assets/", json=payload, headers=agent_headers)
    assert first.status_code == 200

    second = client.post("/inventory/assets/", json=payload, headers=agent_headers)
    assert second.status_code == 400


def test_assets_crud(client, agent_headers):
    create_resp = client.post(
        "/inventory/assets/",
        json={"name": "Soldering Station", "serial_number": "SS-001"},
        headers=agent_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    body = create_resp.json()
    assert body["message"] == "Asset created successfully"
    asset_id = body["asset"]["id"]

    list_resp = client.get("/inventory/assets/", headers=agent_headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == asset_id for item in list_resp.json()["items"])

    get_resp = client.get(f"/inventory/assets/{asset_id}", headers=agent_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == asset_id

    update_resp = client.put(
        f"/inventory/assets/{asset_id}", json={"condition": "good"}, headers=agent_headers
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["condition"] == "good"

    delete_resp = client.delete(f"/inventory/assets/{asset_id}", headers=agent_headers)
    assert delete_resp.status_code in (200, 204)


def test_create_and_update_appear_in_audit_log(client, superuser_headers):
    """Regression test: asset_service previously had zero AuditLog coverage at all -- no asset creation or edit ever showed up in the Audit Log."""
    create_resp = client.post(
        "/inventory/assets/",
        json={"name": "Soldering Station", "serial_number": "SS-AUDIT-001"},
        headers=superuser_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    asset_id = create_resp.json()["asset"]["id"]

    update_resp = client.put(f"/inventory/assets/{asset_id}", json={"condition": "good"}, headers=superuser_headers)
    assert update_resp.status_code == 200, update_resp.text

    audit_resp = client.get("/audit_logs/", headers=superuser_headers)
    assert audit_resp.status_code == 200
    actions = [entry["action"] for entry in audit_resp.json() if entry["entity_type"] == "asset" and entry["entity_id"] == asset_id]
    assert "asset_created" in actions
    assert "asset_updated" in actions
