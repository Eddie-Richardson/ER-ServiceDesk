# ER-ServiceDesk/tests/test_inventory.py
# Tests for Asset/Part duplicate-key business rules and Part low-stock lookup.
"""
Covers the duplicate-serial-number (Asset) and duplicate-SKU (Part) checks
ported from InventoryHub, plus the low-stock endpoint that Part adds.
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


def test_low_stock_endpoint_returns_only_parts_at_or_below_threshold(client, agent_headers):
    """The low-stock endpoint returns parts at/below reorder_threshold, and excludes well-stocked ones."""
    client.post(
        "/inventory/parts/",
        json={"name": "Low Stock Part", "sku": "SKU-LOW", "quantity_on_hand": 2, "reorder_threshold": 5},
        headers=agent_headers,
    )
    client.post(
        "/inventory/parts/",
        json={"name": "Well Stocked Part", "sku": "SKU-HIGH", "quantity_on_hand": 50, "reorder_threshold": 5},
        headers=agent_headers,
    )

    response = client.get("/inventory/parts/low-stock", headers=agent_headers)
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert "Low Stock Part" in names
    assert "Well Stocked Part" not in names
