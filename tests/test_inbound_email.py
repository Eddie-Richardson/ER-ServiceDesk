# ER-ServiceDesk/tests/test_inbound_email.py
# Tests for the inbound-email polling task.
"""
Covers poll_inbound_email's matching logic: a well-formed reply (has a
[Ticket #N] marker AND comes from a known customer's address) becomes an
inbound Message; anything missing either signal is left unmatched rather
than guessed at or silently dropped.

fetch_unread_emails is monkeypatched throughout so these tests never touch
a real IMAP server.
"""

from app.workers.tasks import poll_inbound_email
from app.core.email import InboundEmail
from app.crud.message import crud_message
from app.models.ticket import Ticket
from tests.factories import make_ticket_dependencies


def _make_ticket(db, deps, title="Laptop won't power on"):
    ticket = Ticket(
        customer_id=deps["customer"].id,
        device_id=deps["device"].id,
        category_id=deps["category"].id,
        type_id=deps["type"].id,
        status_id=deps["status"].id,
        title=title,
        priority="normal",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def test_matched_reply_becomes_inbound_message(db, monkeypatch):
    """A reply with a valid ticket marker and a known customer address is threaded onto the ticket."""
    deps = make_ticket_dependencies(db)
    ticket = _make_ticket(db, deps)

    fake_email = InboundEmail(
        ticket_id=ticket.id,
        from_address=deps["customer"].email,
        subject=f"Re: [Ticket #{ticket.id}] {ticket.title}",
        body="Sounds good, thanks!",
    )
    monkeypatch.setattr(
        "app.workers.tasks.fetch_unread_emails", lambda: [fake_email]
    )
    # tasks.py uses its own SessionLocal internally; point it at the same
    # test database the `db` fixture uses.
    import app.workers.tasks as tasks_module
    from tests.conftest import TestSessionLocal
    monkeypatch.setattr(tasks_module, "SessionLocal", TestSessionLocal)

    result = poll_inbound_email()

    assert result == {"processed": 1, "unmatched": 0}

    messages = crud_message.get_multi(db)
    assert len(messages) == 1
    assert messages[0].direction == "inbound"
    assert messages[0].ticket_id == ticket.id
    assert messages[0].customer_id == deps["customer"].id
    assert messages[0].content == "Sounds good, thanks!"


def test_reply_with_no_ticket_marker_is_unmatched(db, monkeypatch):
    """A subject with no [Ticket #N] marker can't be attributed, so it's left unmatched."""
    fake_email = InboundEmail(
        ticket_id=None,
        from_address="someone@example.com",
        subject="Question about my invoice",
        body="Hey, quick question...",
    )
    monkeypatch.setattr(
        "app.workers.tasks.fetch_unread_emails", lambda: [fake_email]
    )
    import app.workers.tasks as tasks_module
    from tests.conftest import TestSessionLocal
    monkeypatch.setattr(tasks_module, "SessionLocal", TestSessionLocal)

    result = poll_inbound_email()

    assert result == {"processed": 0, "unmatched": 1}
    assert len(crud_message.get_multi(db)) == 0


def test_reply_from_unknown_address_is_unmatched(db, monkeypatch):
    """A valid ticket marker from an address with no matching Customer record is left unmatched."""
    deps = make_ticket_dependencies(db)
    ticket = _make_ticket(db, deps)

    fake_email = InboundEmail(
        ticket_id=ticket.id,
        from_address="not_our_customer@example.com",
        subject=f"Re: [Ticket #{ticket.id}] {ticket.title}",
        body="Wait, is this even my ticket?",
    )
    monkeypatch.setattr(
        "app.workers.tasks.fetch_unread_emails", lambda: [fake_email]
    )
    import app.workers.tasks as tasks_module
    from tests.conftest import TestSessionLocal
    monkeypatch.setattr(tasks_module, "SessionLocal", TestSessionLocal)

    result = poll_inbound_email()

    assert result == {"processed": 0, "unmatched": 1}
    assert len(crud_message.get_multi(db)) == 0


def test_reply_referencing_nonexistent_ticket_is_unmatched(db, monkeypatch):
    """A [Ticket #N] marker for a ticket ID that doesn't exist is left unmatched, not errored."""
    fake_email = InboundEmail(
        ticket_id=999999,
        from_address="someone@example.com",
        subject="Re: [Ticket #999999] old ticket",
        body="Following up on this",
    )
    monkeypatch.setattr(
        "app.workers.tasks.fetch_unread_emails", lambda: [fake_email]
    )
    import app.workers.tasks as tasks_module
    from tests.conftest import TestSessionLocal
    monkeypatch.setattr(tasks_module, "SessionLocal", TestSessionLocal)

    result = poll_inbound_email()

    assert result == {"processed": 0, "unmatched": 1}
    assert len(crud_message.get_multi(db)) == 0
