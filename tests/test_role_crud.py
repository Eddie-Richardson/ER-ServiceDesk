# ER-ServiceDesk/tests/test_role_crud.py
"""
Covers Role CRUD.
"""

from tests.factories import assert_crud_lifecycle, assert_requires_auth


def test_roles_crud(client, superuser_headers):
    assert_crud_lifecycle(
        client, superuser_headers, "/roles",
        {"name": "Technician", "description": "Repair tech"},
        {"description": "Senior repair tech"},
        update_check_field="description",
    )


def test_roles_requires_auth(client):
    assert_requires_auth(client, "/roles")
