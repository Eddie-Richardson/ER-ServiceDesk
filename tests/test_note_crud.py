# ER-ServiceDesk/tests/test_note_crud.py
"""
Covers NoteCRUD.get() directly.
"""

from app.crud.note import crud_note
from app.schemas.note import NoteCreate
from tests.factories import make_full_ticket


def test_get_returns_the_real_record_by_id(db):
    ticket = make_full_ticket(db)
    note = crud_note.create(db, NoteCreate(ticket_id=ticket.id, direction="internal", content="Test note"))

    result = crud_note.get(db, note.id)

    assert result.id == note.id
    assert result.content == "Test note"


def test_get_returns_none_for_a_nonexistent_id(db):
    assert crud_note.get(db, id=999999) is None


def test_notes_crud(client, superuser_headers, db):
    """Covers the internal-note case specifically -- not outbound/inbound sending or the author-or-superuser authorization rule."""
    from tests.factories import assert_crud_lifecycle, make_plain_user
    ticket = make_full_ticket(db)
    user = make_plain_user(db)
    assert_crud_lifecycle(
        client, superuser_headers, "/notes",
        {"ticket_id": ticket.id, "user_id": user.id, "direction": "internal", "content": "Internal note"},
        {"content": "Updated internal note"},
        update_check_field="content",
    )
