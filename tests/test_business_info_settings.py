# ER-ServiceDesk/tests/test_business_info_settings.py
"""
Covers the superuser-only Business Info Settings screen -- password
handling (never returned, omitted keeps the existing one), and that
the narrow, any-logged-in-user business-name endpoint genuinely reads
the same underlying setting.
"""


def test_business_info_settings_requires_superuser(client, agent_headers):
    """billing.manage/other ordinary permissions aren't enough -- this screen includes setting the email password, so it's superuser-only, no exceptions."""
    resp = client.get("/business_info_settings/", headers=agent_headers)
    assert resp.status_code == 403


def test_business_info_settings_password_never_returned(client, superuser_headers):
    """Setting an email password never gets it back out through the API -- only whether one is set."""
    payload = {
        "business_name": "Eddie's Repair Shop", "business_phone": "555-0100",
        "email_address": "shop@example.com", "email_password": "a-genuinely-secret-value",
        "smtp_host": "smtp.gmail.com", "smtp_port": 587,
        "imap_host": "imap.gmail.com", "imap_port": 993,
    }
    update_resp = client.put("/business_info_settings/", json=payload, headers=superuser_headers)
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["email_password_is_set"] is True
    assert "a-genuinely-secret-value" not in update_resp.text

    get_resp = client.get("/business_info_settings/", headers=superuser_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["email_password_is_set"] is True
    assert "a-genuinely-secret-value" not in get_resp.text


def test_business_info_settings_omitted_password_leaves_existing_one(client, superuser_headers):
    """Updating other fields without sending email_password keeps the previously-set password, rather than wiping it out."""
    initial_payload = {
        "business_name": "Eddie's Repair Shop", "business_phone": "555-0100",
        "email_address": "shop@example.com", "email_password": "the-original-password",
        "smtp_host": "smtp.gmail.com", "smtp_port": 587,
        "imap_host": "imap.gmail.com", "imap_port": 993,
    }
    first_resp = client.put("/business_info_settings/", json=initial_payload, headers=superuser_headers)
    assert first_resp.status_code == 200, first_resp.text
    assert first_resp.json()["email_password_is_set"] is True

    followup_payload = dict(initial_payload)
    followup_payload["business_phone"] = "555-0199"
    followup_payload["email_password"] = None
    second_resp = client.put("/business_info_settings/", json=followup_payload, headers=superuser_headers)
    assert second_resp.status_code == 200, second_resp.text
    assert second_resp.json()["business_phone"] == "555-0199"
    assert second_resp.json()["email_password_is_set"] is True


def test_business_info_narrow_endpoint_reflects_the_same_name(client, agent_headers, superuser_headers):
    """business-info's narrow, any-logged-in-user endpoint reads the same business_name set through the full superuser management screen -- confirming the two genuinely share one underlying setting, not two separate values."""
    payload = {
        "business_name": "Shared Name Shop", "business_phone": "555-0100",
        "email_address": "shop@example.com",
        "smtp_host": "smtp.gmail.com", "smtp_port": 587,
        "imap_host": "imap.gmail.com", "imap_port": 993,
    }
    update_resp = client.put("/business_info_settings/", json=payload, headers=superuser_headers)
    assert update_resp.status_code == 200, update_resp.text

    narrow_resp = client.get("/business-info/business-name", headers=agent_headers)
    assert narrow_resp.status_code == 200
    assert narrow_resp.json()["business_name"] == "Shared Name Shop"
