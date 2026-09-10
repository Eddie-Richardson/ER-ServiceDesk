# ER-ServiceDesk/tests/test_system_setting_crud.py
"""
Covers SystemSetting CRUD.
"""

from tests.factories import assert_crud_lifecycle


def test_system_settings_crud(client, superuser_headers):
    assert_crud_lifecycle(
        client, superuser_headers, "/system_settings",
        {"key": "support_email", "value": "help@example.com"},
        {"value": "support@example.com"},
        update_check_field="value",
    )
