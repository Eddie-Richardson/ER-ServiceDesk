# ER-ServiceDesk/tests/test_service_crud.py
"""
Covers Service (billing catalog item) CRUD. GET requires
billing.manage (agent_headers has it); create/update/delete require
superuser specifically.
"""

from tests.factories import assert_crud_lifecycle


def test_services_crud(client, agent_headers, superuser_headers):
    assert_crud_lifecycle(
        client, superuser_headers, "/services",
        {"name": "Diagnostic", "price": "50.00"},
        {"price": "60.00"},
        update_check_field="price",
        read_headers=agent_headers,
    )


def test_services_write_requires_superuser(client, agent_headers):
    """billing.manage alone isn't enough to create a service -- catalog writes are superuser-only."""
    resp = client.post("/services/", json={"name": "Cleaning", "price": "25.00"}, headers=agent_headers)
    assert resp.status_code == 403
