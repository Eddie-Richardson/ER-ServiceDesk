# ER-ServiceDesk/tests/test_user_crud.py
"""
Covers /users route-level authorization and the /users/assignable
endpoint.
"""

from tests.factories import make_role, make_plain_user


def test_users_requires_superuser_not_just_auth(client, agent_headers):
    """A regular (non-superuser) authenticated user should be rejected from /users."""
    resp = client.get("/users/", headers=agent_headers)
    assert resp.status_code == 403


def test_assignable_users_available_to_non_superuser(client, agent_headers, db):
    """Unlike the rest of /users, /users/assignable is genuinely available to any authenticated user -- resolving a ticket's assignee is something every role needs, not just admins."""
    resp = client.get("/users/assignable", headers=agent_headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body) >= 1
    entry = body[0]
    assert set(entry.keys()) == {"id", "full_name", "is_front_desk"}


def test_assignable_users_correctly_flags_front_desk(client, agent_headers, db):
    """A user with the front_desk role shows is_front_desk=True; others show False -- lets the desktop filter front desk out of the assignment picker."""
    from app.models.user_role import UserRole

    front_desk_role = make_role(db, "front_desk")
    front_desk_user = make_plain_user(db, email="fd_test@example.com")
    db.add(UserRole(user_id=front_desk_user.id, role_id=front_desk_role.id))
    db.commit()

    resp = client.get("/users/assignable", headers=agent_headers)
    assert resp.status_code == 200
    entries = {e["id"]: e["is_front_desk"] for e in resp.json()}
    assert entries[front_desk_user.id] is True
