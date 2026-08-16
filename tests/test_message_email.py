# ER-ServiceDesk/tests/test_message_email.py
# Tests for MessageService's outbound-email wiring.
"""
Covers MessageService.create's behavior when a Message is outbound:
it should call app.core.email.send_email with the right recipient,
subject (built from the parent ticket), and body -- and it should not
lose the Message record if the send itself fails.

send_email is monkeypatched throughout so these tests never touch a real
SMTP server.
"""

import pytest

from app.services.message_service import message_service
from app.schemas.message import MessageCreate
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


def test_outbound_message_sends_email_with_ticket_subject(db, monkeypatch):
    """An outbound Message triggers send_email with a [Ticket #N]-prefixed subject."""
    deps = make_ticket_dependencies(db)
    ticket = _make_ticket(db, deps)

    sent = {}

    def fake_send_email(db, to_address, subject, body):
        sent["to_address"] = to_address
        sent["subject"] = subject
        sent["body"] = body

    monkeypatch.setattr("app.services.message_service.send_email", fake_send_email)

    obj_in = MessageCreate(
        ticket_id=ticket.id,
        customer_id=deps["customer"].id,
        direction="outbound",
        content="Your laptop is ready for pickup.",
    )
    message = message_service.create(db, obj_in)

    assert sent["to_address"] == deps["customer"].email
    assert sent["subject"] == f"[Ticket #{ticket.id}] {ticket.title}"
    assert sent["body"] == "Your laptop is ready for pickup."
    assert message.email_status == "sent"


def test_inbound_message_does_not_send_email(db, monkeypatch):
    """An inbound Message (customer -> shop) never triggers an outbound send."""
    deps = make_ticket_dependencies(db)
    ticket = _make_ticket(db, deps)

    called = {"count": 0}

    def fake_send_email(db, to_address, subject, body):
        called["count"] += 1

    monkeypatch.setattr("app.services.message_service.send_email", fake_send_email)

    obj_in = MessageCreate(
        ticket_id=ticket.id,
        customer_id=deps["customer"].id,
        direction="inbound",
        content="When will it be ready?",
    )
    message = message_service.create(db, obj_in)

    assert called["count"] == 0
    assert message.email_status is None


def test_outbound_message_persists_even_if_send_fails(db, monkeypatch):
    """A send failure is swallowed (and logged) -- the Message record still exists."""
    deps = make_ticket_dependencies(db)
    ticket = _make_ticket(db, deps)

    def failing_send_email(db, to_address, subject, body):
        raise RuntimeError("SMTP connection refused")

    monkeypatch.setattr("app.services.message_service.send_email", failing_send_email)

    obj_in = MessageCreate(
        ticket_id=ticket.id,
        customer_id=deps["customer"].id,
        direction="outbound",
        content="This send will fail.",
    )
    # Should not raise, despite send_email raising internally.
    message = message_service.create(db, obj_in)

    assert message.id is not None
    persisted = message_service.get(db, message.id)
    assert persisted is not None
    assert persisted.content == "This send will fail."
    assert persisted.email_status == "failed"


def test_failed_send_is_logged_with_full_content_for_manual_followup(db, monkeypatch, caplog):
    """
    A failed send logs the actual message content (not just IDs), and
    explicitly flags that a tech should retry or call the customer --
    since the log is the only trace of *why* email_status is "failed"
    if a tech goes looking for it.
    """
    import logging
    deps = make_ticket_dependencies(db)
    ticket = _make_ticket(db, deps)

    def failing_send_email(db, to_address, subject, body):
        raise RuntimeError("SMTP connection refused")

    monkeypatch.setattr("app.services.message_service.send_email", failing_send_email)

    obj_in = MessageCreate(
        ticket_id=ticket.id,
        customer_id=deps["customer"].id,
        direction="outbound",
        content="Your part arrived, come pick up your device.",
    )
    with caplog.at_level(logging.ERROR):
        message_service.create(db, obj_in)

    assert "FAILED TO SEND" in caplog.text
    assert "Your part arrived, come pick up your device." in caplog.text
    assert "call the customer" in caplog.text
