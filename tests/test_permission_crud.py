# ER-ServiceDesk/tests/test_permission_crud.py
"""
Covers Permission CRUD.
"""

from tests.factories import assert_crud_lifecycle


def test_permissions_crud(client, superuser_headers):
    assert_crud_lifecycle(
        client, superuser_headers, "/permissions",
        {"name": "ticket.create", "description": "Create tickets"},
        {"description": "Create new tickets"},
        update_check_field="description",
    )
