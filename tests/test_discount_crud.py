# ER-ServiceDesk/tests/test_discount_crud.py
"""
Covers Discount CRUD. GET requires billing.manage (agent_headers has
it); create/update/delete require superuser specifically.
"""

from tests.factories import assert_crud_lifecycle


def test_discounts_crud(client, agent_headers, superuser_headers):
    assert_crud_lifecycle(
        client, superuser_headers, "/discounts",
        {"name": "Loyalty Discount", "percentage": "10.00"},
        {"percentage": "15.00"},
        update_check_field="percentage",
        read_headers=agent_headers,
    )


def test_discounts_write_requires_superuser(client, agent_headers):
    """billing.manage alone isn't enough to create a discount -- catalog writes are superuser-only."""
    resp = client.post("/discounts/", json={"name": "Referral", "percentage": "5.00"}, headers=agent_headers)
    assert resp.status_code == 403
