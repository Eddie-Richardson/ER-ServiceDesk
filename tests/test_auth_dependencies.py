# ER-ServiceDesk/tests/test_auth_dependencies.py
"""
Covers real, genuine gaps in app/api/dependencies.py -- the
require_permission() 403 rejection path specifically was never
exercised by any existing test, since every existing test uses either
agent_headers (which is deliberately granted every ordinary
permission) or superuser_headers, never a genuinely authenticated user
missing one specific permission. Also covers get_current_user()'s
rejection of a token whose user was since deleted, and one missing
its subject claim entirely.
"""

from app.core.security import create_access_token, hash_password
from app.models.user import User


def _make_authenticated_user_with_no_permissions(db, email="no_perms@example.com"):
    """A real, genuinely authenticated user with zero Role/Permission grants at all."""
    user = User(
        email=email, hashed_password=hash_password("Testpass123!"),
        first_name="No", last_name="Perms", is_active=True, is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


def test_require_permission_rejects_an_authenticated_user_missing_that_specific_permission(client, db):
    """A real, valid token for a real account that's simply never been granted inventory.manage -- confirms the 403 path genuinely fires, not just for an unauthenticated request."""
    headers = _make_authenticated_user_with_no_permissions(db)
    response = client.post("/inventory/parts/", json={"name": "Should Be Rejected", "sku": "SKU-REJECT"}, headers=headers)
    assert response.status_code == 403


def test_get_current_user_rejects_a_valid_token_whose_user_was_since_deleted(client, db):
    """A real, otherwise-valid token encoding a user_id that no longer exists -- e.g. the account was deleted after the token was issued."""
    token = create_access_token({"sub": "999999"})
    response = client.post("/auth/heartbeat", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_get_current_user_rejects_a_valid_token_missing_its_subject_claim(client, db):
    """A real, correctly-signed token that's simply missing the "sub" claim entirely -- constructed manually here, since create_access_token() itself always includes one."""
    from jose import jwt
    from app.core.security import SECRET_KEY, ALGORITHM
    token = jwt.encode({"not_sub": "999999"}, SECRET_KEY, algorithm=ALGORITHM)
    response = client.post("/auth/heartbeat", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401
