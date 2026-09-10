# ER-ServiceDesk/tests/test_device_user_account_crud.py
"""
Covers DeviceUserAccountCRUD's update() -- specifically the is_admin
field. The other two optional fields (account_name, encrypted
password) are exercised elsewhere; is_admin specifically wasn't.
"""

from tests.factories import make_customer, make_device


def test_update_genuinely_changes_is_admin(client, agent_headers, db):
    customer = make_customer(db)
    device = make_device(db, customer.id)
    create_resp = client.post("/device_user_accounts/", json={"device_id": device.id, "account_name": "user@outlook.com", "password": "TestPassword1!", "is_admin": False}, headers=agent_headers)
    account_id = create_resp.json()["id"]

    update_resp = client.put(f"/device_user_accounts/{account_id}", json={"is_admin": True}, headers=agent_headers)
    assert update_resp.status_code == 200
    assert update_resp.json()["is_admin"] is True


def test_password_round_trips_correctly(client, agent_headers, db):
    """A password set through create() comes back as the exact same plaintext -- confirms the encrypt/decrypt round-trip genuinely works, not just that the API returns some value."""
    customer = make_customer(db)
    device = make_device(db, customer.id)

    create_resp = client.post(
        "/device_user_accounts/",
        json={"device_id": device.id, "account_name": "jsmith@outlook.com", "password": "Correct-Horse-Battery-Staple-9", "is_admin": False},
        headers=agent_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    account_id = create_resp.json()["id"]
    assert create_resp.json()["password"] == "Correct-Horse-Battery-Staple-9"

    list_resp = client.get("/device_user_accounts/", params={"device_id": device.id}, headers=agent_headers)
    assert list_resp.status_code == 200
    listed = next(a for a in list_resp.json() if a["id"] == account_id)
    assert listed["password"] == "Correct-Horse-Battery-Staple-9"


def test_password_update_and_omit_behavior(client, agent_headers, db):
    """Updating with a new password replaces it; updating other fields while omitting password leaves the existing one unchanged."""
    customer = make_customer(db)
    device = make_device(db, customer.id)

    create_resp = client.post(
        "/device_user_accounts/",
        json={"device_id": device.id, "account_name": "jsmith@outlook.com", "password": "original-password", "is_admin": False},
        headers=agent_headers,
    )
    account_id = create_resp.json()["id"]

    new_password_resp = client.put(f"/device_user_accounts/{account_id}", json={"password": "replaced-password"}, headers=agent_headers)
    assert new_password_resp.status_code == 200, new_password_resp.text
    assert new_password_resp.json()["password"] == "replaced-password"

    rename_only_resp = client.put(f"/device_user_accounts/{account_id}", json={"account_name": "jsmith-renamed@outlook.com"}, headers=agent_headers)
    assert rename_only_resp.status_code == 200, rename_only_resp.text
    assert rename_only_resp.json()["account_name"] == "jsmith-renamed@outlook.com"
    assert rename_only_resp.json()["password"] == "replaced-password"


def test_delete(client, agent_headers, db):
    customer = make_customer(db)
    device = make_device(db, customer.id)

    create_resp = client.post(
        "/device_user_accounts/",
        json={"device_id": device.id, "account_name": "temp@outlook.com", "password": "temp-pass", "is_admin": True},
        headers=agent_headers,
    )
    account_id = create_resp.json()["id"]

    delete_resp = client.delete(f"/device_user_accounts/{account_id}", headers=agent_headers)
    assert delete_resp.status_code in (200, 204)

    list_resp = client.get("/device_user_accounts/", params={"device_id": device.id}, headers=agent_headers)
    assert not any(a["id"] == account_id for a in list_resp.json())


def test_list_requires_device_id(client, agent_headers):
    """device_id is a required query param, not optional -- there's no legitimate reason to fetch every device's accounts across the whole app at once."""
    resp = client.get("/device_user_accounts/", headers=agent_headers)
    assert resp.status_code == 422
