# ER-ServiceDesk/tests/test_ticket_category_crud.py
"""
Covers TicketCategory CRUD.
"""

from tests.factories import assert_crud_lifecycle


def test_ticket_categories_crud(client, superuser_headers):
    assert_crud_lifecycle(
        client, superuser_headers, "/ticket_categories",
        {"name": "Networking", "description": "Network issues"},
        {"description": "Network/connectivity issues"},
        update_check_field="description",
    )
