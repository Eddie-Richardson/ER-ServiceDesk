# ER-ServiceDesk/tests/test_user_role_crud.py
"""
Covers UserRole CRUD -- a pure join record, add/remove is the real
pattern (see RoleSaveWorker/UserSaveWorker), never an in-place edit.
Update is confirmed rejected rather than tested as working.
"""

from tests.factories import make_plain_user, make_role


def test_user_roles_crud(client, superuser_headers, db):
    user = make_plain_user(db)
    role = make_role(db)

    create_resp = client.post("/user_roles/", json={"user_id": user.id, "role_id": role.id}, headers=superuser_headers)
    assert create_resp.status_code == 200, create_resp.text
    user_role_id = create_resp.json()["id"]

    list_resp = client.get("/user_roles/", headers=superuser_headers)
    assert list_resp.status_code == 200
    assert any(item["id"] == user_role_id for item in list_resp.json())

    role2 = make_role(db, name="Manager")
    update_resp = client.put(f"/user_roles/{user_role_id}", json={"role_id": role2.id}, headers=superuser_headers)
    assert update_resp.status_code == 405

    delete_resp = client.delete(f"/user_roles/{user_role_id}", headers=superuser_headers)
    assert delete_resp.status_code in (200, 204)
