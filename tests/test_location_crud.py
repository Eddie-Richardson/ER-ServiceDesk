# ER-ServiceDesk/tests/test_location_crud.py
"""
Covers Location CRUD.
"""

from tests.factories import assert_crud_lifecycle


def test_locations_crud(client, superuser_headers):
    assert_crud_lifecycle(
        client, superuser_headers, "/inventory/locations",
        {"name": "Front Counter", "description": "Customer-facing intake area", "show_in_ticket_picker": True},
        {"description": "Main intake and pickup area", "show_in_ticket_picker": False},
        update_check_field="show_in_ticket_picker",
    )
