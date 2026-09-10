# ER-ServiceDesk/tests/test_note_template_crud.py
"""
Covers NoteTemplate CRUD.
"""

from tests.factories import assert_crud_lifecycle


def test_note_templates_crud(client, superuser_headers):
    assert_crud_lifecycle(
        client, superuser_headers, "/note_templates",
        {"name": "ticket_created", "body": "We got your ticket."},
        {"body": "We received your repair request."},
        update_check_field="body",
    )
