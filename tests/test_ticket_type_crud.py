# ER-ServiceDesk/tests/test_ticket_type_crud.py
"""
Covers TicketType CRUD.
"""

from tests.factories import assert_crud_lifecycle


def test_ticket_types_crud(client, superuser_headers):
    assert_crud_lifecycle(
        client, superuser_headers, "/ticket_types",
        {"name": "Feature Request"},
        {"description": "A requested new capability"},
        update_check_field="description",
    )
