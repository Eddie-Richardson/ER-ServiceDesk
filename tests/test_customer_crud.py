# ER-ServiceDesk/tests/test_customer_crud.py
"""
Covers Customer CRUD at the HTTP level.
"""

from tests.factories import assert_crud_lifecycle


def test_customers_crud(client, agent_headers):
    assert_crud_lifecycle(
        client, agent_headers, "/customers",
        {"first_name": "Jane", "last_name": "Doe", "email": "jane@example.com", "street": "123 Main St", "city": "Dallas", "state": "TX", "zip_code": "75001"},
        {"phone": "555-1234", "street": "456 Oak Ave", "city": "Los Angeles", "state": "CA", "zip_code": "90210"},
        update_check_field="city",
    )
