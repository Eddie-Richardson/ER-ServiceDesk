# ER-ServiceDesk/tests/test_role_permission_crud.py
"""
Covers RolePermission CRUD.
"""

from tests.factories import assert_crud_lifecycle, make_role, make_permission


def test_role_permissions_crud(client, superuser_headers, db):
    role = make_role(db)
    permission = make_permission(db)
    role2 = make_role(db, name="Manager")
    permission2 = make_permission(db, name="ticket.delete")
    assert_crud_lifecycle(
        client, superuser_headers, "/role_permissions",
        {"role_id": role.id, "permission_id": permission.id},
        {"role_id": role2.id, "permission_id": permission2.id},
        update_check_field="role_id",
    )
