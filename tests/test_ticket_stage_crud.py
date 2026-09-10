# ER-ServiceDesk/tests/test_ticket_stage_crud.py
"""
Covers TicketStage CRUD.
"""

from tests.factories import assert_crud_lifecycle


def test_ticket_stages_crud(client, superuser_headers):
    assert_crud_lifecycle(
        client, superuser_headers, "/ticket_stages",
        {"name": "Awaiting Parts"},
        {"description": "Waiting on an ordered part"},
        update_check_field="description",
    )
