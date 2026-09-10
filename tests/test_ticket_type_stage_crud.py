# ER-ServiceDesk/tests/test_ticket_type_stage_crud.py
"""
Covers TicketTypeStage CRUD.
"""

from tests.factories import assert_crud_lifecycle, make_ticket_type, make_ticket_stage


def test_ticket_type_stages_crud(client, superuser_headers, db):
    ttype = make_ticket_type(db)
    stage = make_ticket_stage(db)
    ttype2 = make_ticket_type(db, name="Bug")
    assert_crud_lifecycle(
        client, superuser_headers, "/ticket_type_stages",
        {"type_id": ttype.id, "stage_id": stage.id},
        {"type_id": ttype2.id},
        update_check_field="type_id",
    )
