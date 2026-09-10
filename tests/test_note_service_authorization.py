# ER-ServiceDesk/tests/test_note_service_authorization.py
"""
Covers NoteService.update()/delete()'s real, security-relevant
authorization matrix -- likely untested before this, since
test_note_email.py only exercises the email-sending path in create().
Own author can edit/delete their own entry; a different, non-superuser
cannot; a superuser can touch anything; an inbound (customer-authored)
entry has no staff author to defer to at all, so only a superuser may
touch it.
"""

import pytest
from fastapi import HTTPException

from app.services.note_service import note_service
from app.schemas.note import NoteCreate, NoteUpdate
from tests.factories import make_full_ticket, make_plain_user


def _make_note(db, ticket_id, direction, user_id=None, customer_id=None):
    return note_service.create(db, NoteCreate(ticket_id=ticket_id, direction=direction, content="Original content", user_id=user_id, customer_id=customer_id))


class _FakeUser:
    def __init__(self, id, is_superuser=False):
        self.id = id
        self.is_superuser = is_superuser


def test_own_author_can_edit_their_own_note(db):
    author = make_plain_user(db)
    ticket = make_full_ticket(db)
    note = _make_note(db, ticket.id, "internal", user_id=author.id)

    updated = note_service.update(db, note.id, NoteUpdate(content="Edited by author"), current_user=_FakeUser(author.id))
    assert updated.content == "Edited by author"


def test_a_different_non_superuser_cannot_edit_someone_elses_note(db):
    author = make_plain_user(db)
    ticket = make_full_ticket(db)
    note = _make_note(db, ticket.id, "internal", user_id=author.id)

    with pytest.raises(HTTPException) as exc_info:
        note_service.update(db, note.id, NoteUpdate(content="Sneaky edit"), current_user=_FakeUser(id=99999, is_superuser=False))
    assert exc_info.value.status_code == 403


def test_a_superuser_can_edit_anyone_elses_note(db):
    author = make_plain_user(db)
    ticket = make_full_ticket(db)
    note = _make_note(db, ticket.id, "internal", user_id=author.id)

    updated = note_service.update(db, note.id, NoteUpdate(content="Admin edit"), current_user=_FakeUser(id=99999, is_superuser=True))
    assert updated.content == "Admin edit"


def test_only_a_superuser_can_edit_an_inbound_customer_note(db):
    """An inbound note has no staff author to defer to at all -- only a superuser may touch one."""
    ticket = make_full_ticket(db)
    note = _make_note(db, ticket.id, "inbound", customer_id=ticket.customer_id)

    with pytest.raises(HTTPException) as exc_info:
        note_service.update(db, note.id, NoteUpdate(content="Not allowed"), current_user=_FakeUser(id=99999, is_superuser=False))
    assert exc_info.value.status_code == 403

    updated = note_service.update(db, note.id, NoteUpdate(content="Allowed"), current_user=_FakeUser(id=99999, is_superuser=True))
    assert updated.content == "Allowed"


def test_own_author_can_delete_their_own_note(db):
    author = make_plain_user(db)
    ticket = make_full_ticket(db)
    note = _make_note(db, ticket.id, "internal", user_id=author.id)
    note_id = note.id

    note_service.delete(db, note_id, current_user=_FakeUser(author.id))

    assert note_service.get(db, note_id) is None


def test_a_different_non_superuser_cannot_delete_someone_elses_note(db):
    author = make_plain_user(db)
    ticket = make_full_ticket(db)
    note = _make_note(db, ticket.id, "internal", user_id=author.id)

    with pytest.raises(HTTPException) as exc_info:
        note_service.delete(db, note.id, current_user=_FakeUser(id=99999, is_superuser=False))
    assert exc_info.value.status_code == 403

    assert note_service.get(db, note.id) is not None
