# ER-ServiceDesk/tests/test_tax_rate_crud.py
"""
Covers TaxRate CRUD. GET requires billing.manage (agent_headers has
it); create/update/delete require superuser specifically.
"""

from tests.factories import assert_crud_lifecycle


def test_tax_rates_crud(client, agent_headers, superuser_headers):
    assert_crud_lifecycle(
        client, superuser_headers, "/tax_rates",
        {"name": "Sales Tax", "percentage": "7.25"},
        {"percentage": "8.00"},
        update_check_field="percentage",
        read_headers=agent_headers,
    )


def test_tax_rates_write_requires_superuser(client, agent_headers):
    """billing.manage alone isn't enough to create a tax rate -- catalog writes are superuser-only, matching services.py's own gating split."""
    resp = client.post("/tax_rates/", json={"name": "VAT", "percentage": "20.00"}, headers=agent_headers)
    assert resp.status_code == 403
