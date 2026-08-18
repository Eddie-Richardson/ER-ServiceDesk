# ER-ServiceDesk/tests/test_inventory.py
# Tests for Asset/Part duplicate-key business rules.
"""
Covers the duplicate-serial-number (Asset) and duplicate-SKU (Part) checks.
"""


def test_duplicate_asset_serial_number_rejected(client, agent_headers):
    """Creating a second asset with the same serial number is rejected."""
    payload = {"name": "Dell Laptop", "serial_number": "SN-DUPLICATE-001"}

    first = client.post("/inventory/assets/", json=payload, headers=agent_headers)
    assert first.status_code == 200

    second = client.post("/inventory/assets/", json=payload, headers=agent_headers)
    assert second.status_code == 400


def test_duplicate_part_sku_rejected(client, agent_headers):
    """Creating a second part with the same SKU is rejected."""
    payload = {"name": "SSD 500GB", "sku": "SKU-DUPLICATE-001"}

    first = client.post("/inventory/parts/", json=payload, headers=agent_headers)
    assert first.status_code == 200

    second = client.post("/inventory/parts/", json=payload, headers=agent_headers)
    assert second.status_code == 400

