# ER-ServiceDesk/tests/test_ticket_status_crud.py
"""
Covers TicketStatus CRUD.
"""

from tests.factories import assert_crud_lifecycle


def test_ticket_statuses_crud(client, superuser_headers):
    assert_crud_lifecycle(
        client, superuser_headers, "/ticket_statuses",
        {"name": "In Progress", "description": "Actively being worked"},
        {"description": "Currently on the bench"},
        update_check_field="description",
    )
