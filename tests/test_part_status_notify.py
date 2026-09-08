# ER-ServiceDesk/tests/test_part_status_notify.py
"""
Two layers covered here:
  1. build_part_status_note_content: pure function, no DB/RQ needed -- given a
     TicketPart, does it produce the right customer-facing text (and the
     right *absence* of text for "needed")?
  2. TicketPartService.update: does changing status actually enqueue the
     notify job (and does a NON-change correctly NOT enqueue anything)?

The actual RQ job (notify_customer_of_part_status_change) is exercised
directly in test_notify_job_creates_outbound_note, calling it the same
way the real worker would -- but with send_email mocked, same pattern as
test_note_email.py, so no real email goes out.
"""

from app.workers.tasks import build_part_status_note_content, notify_customer_of_part_status_change
from app.services.ticket_part_service import ticket_part_service
from app.schemas.ticket_part import TicketPartCreate, TicketPartUpdate
from app.models.ticket import Ticket
from app.models.part import Part
from app.crud.note import crud_note
from tests.factories import make_ticket_dependencies, make_plain_user


def _make_ticket(db, deps, title="Screen replacement"):
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


def _make_part(db, name="Replacement Screen", sku="SKU-SCREEN-001"):
    part = Part(name=name, sku=sku)
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


# ---------------------------------------------------------------------------
# build_part_status_note_content
# ---------------------------------------------------------------------------

def test_needed_status_produces_no_note(db):
    """'needed' is the default status with nothing to report yet -- no notification."""
    deps = make_ticket_dependencies(db)
    ticket = _make_ticket(db, deps)
    part = _make_part(db)
    user = make_plain_user(db)

    tp = ticket_part_service.create(db, TicketPartCreate(
        ticket_id=ticket.id, part_id=part.id, status="needed",
    ), user.id)

    assert build_part_status_note_content(tp) is None


def test_shipped_status_includes_carrier_and_tracking_when_present(db):
    """'shipped' with carrier/tracking info includes both in the note_content."""
    deps = make_ticket_dependencies(db)
    ticket = _make_ticket(db, deps)
    part = _make_part(db)
    user = make_plain_user(db)

    tp = ticket_part_service.create(db, TicketPartCreate(
        ticket_id=ticket.id, part_id=part.id, status="shipped",
        carrier="UPS", tracking_number="1Z999AA10123456784",
    ), user.id)

    note_content = build_part_status_note_content(tp)
    assert "Replacement Screen" in note_content
    assert "shipped" in note_content
    assert "UPS" in note_content
    assert "1Z999AA10123456784" in note_content


def test_shipped_status_without_tracking_info_omits_it_gracefully(db):
    """'shipped' with no carrier/tracking entered yet still produces a note_content, just without those details."""
    deps = make_ticket_dependencies(db)
    ticket = _make_ticket(db, deps)
    part = _make_part(db)
    user = make_plain_user(db)

    tp = ticket_part_service.create(db, TicketPartCreate(
        ticket_id=ticket.id, part_id=part.id, status="shipped",
    ), user.id)

    note_content = build_part_status_note_content(tp)
    assert note_content is not None
    assert "Carrier" not in note_content


def test_received_status_does_not_include_tracking_info(db):
    """'received' shouldn't mention carrier/tracking -- the package already arrived, it's not useful anymore."""
    deps = make_ticket_dependencies(db)
    ticket = _make_ticket(db, deps)
    part = _make_part(db)
    user = make_plain_user(db)

    tp = ticket_part_service.create(db, TicketPartCreate(
        ticket_id=ticket.id, part_id=part.id, status="received",
        carrier="UPS", tracking_number="1Z999AA10123456784",
    ), user.id)

    note_content = build_part_status_note_content(tp)
    assert "arrived" in note_content
    assert "UPS" not in note_content
    assert "1Z999AA10123456784" not in note_content


# ---------------------------------------------------------------------------
# TicketPartService.update -> enqueue on status change
# ---------------------------------------------------------------------------

def test_status_change_enqueues_notify_job(db, monkeypatch):
    """Changing status from 'needed' to 'ordered' enqueues the notify job with this TicketPart's ID."""
    deps = make_ticket_dependencies(db)
    ticket = _make_ticket(db, deps)
    part = _make_part(db)
    user = make_plain_user(db)

    tp = ticket_part_service.create(db, TicketPartCreate(
        ticket_id=ticket.id, part_id=part.id, status="needed",
    ), user.id)

    enqueued = []

    class FakeQueue:
        def enqueue(self, func, *args):
            enqueued.append((func, args))

    monkeypatch.setattr(
        "app.services.ticket_part_service.get_queue", lambda: FakeQueue()
    )

    ticket_part_service.update(db, tp.id, TicketPartUpdate(status="ordered"), user.id)

    assert len(enqueued) == 1
    func, args = enqueued[0]
    assert func.__name__ == "notify_customer_of_part_status_change"
    assert args == (tp.id,)


def test_non_status_field_update_does_not_enqueue(db, monkeypatch):
    """Updating carrier/tracking_number alone (status unchanged) does NOT enqueue a notification."""
    deps = make_ticket_dependencies(db)
    ticket = _make_ticket(db, deps)
    part = _make_part(db)
    user = make_plain_user(db)

    tp = ticket_part_service.create(db, TicketPartCreate(
        ticket_id=ticket.id, part_id=part.id, status="shipped",
    ), user.id)

    enqueued = []

    class FakeQueue:
        def enqueue(self, func, *args):
            enqueued.append((func, args))

    monkeypatch.setattr(
        "app.services.ticket_part_service.get_queue", lambda: FakeQueue()
    )

    # Same status, just filling in tracking info after the fact.
    ticket_part_service.update(db, tp.id, TicketPartUpdate(
        carrier="FedEx", tracking_number="789123456",
    ), user.id)

    assert len(enqueued) == 0


def test_setting_same_status_again_does_not_enqueue(db, monkeypatch):
    """Explicitly setting status to its current value is not a 'change' -- no notification."""
    deps = make_ticket_dependencies(db)
    ticket = _make_ticket(db, deps)
    part = _make_part(db)
    user = make_plain_user(db)

    tp = ticket_part_service.create(db, TicketPartCreate(
        ticket_id=ticket.id, part_id=part.id, status="ordered",
    ), user.id)

    enqueued = []

    class FakeQueue:
        def enqueue(self, func, *args):
            enqueued.append((func, args))

    monkeypatch.setattr(
        "app.services.ticket_part_service.get_queue", lambda: FakeQueue()
    )

    ticket_part_service.update(db, tp.id, TicketPartUpdate(status="ordered"), user.id)

    assert len(enqueued) == 0


def test_enqueue_failure_does_not_break_the_status_update(db, monkeypatch):
    """If Redis/enqueueing is unavailable, the status update itself still succeeds."""
    deps = make_ticket_dependencies(db)
    ticket = _make_ticket(db, deps)
    part = _make_part(db)
    user = make_plain_user(db)

    tp = ticket_part_service.create(db, TicketPartCreate(
        ticket_id=ticket.id, part_id=part.id, status="needed",
    ), user.id)

    def broken_get_queue():
        raise ConnectionError("Redis is down")

    monkeypatch.setattr(
        "app.services.ticket_part_service.get_queue", broken_get_queue
    )

    # Should not raise, despite get_queue() raising internally.
    updated = ticket_part_service.update(db, tp.id, TicketPartUpdate(status="ordered"), user.id)

    assert updated.status == "ordered"


# ---------------------------------------------------------------------------
# The actual RQ job, called directly (as the worker would call it)
# ---------------------------------------------------------------------------

def test_notify_job_creates_outbound_note(db, monkeypatch):
    """Running the job for real (send_email mocked) creates the expected outbound Note."""
    deps = make_ticket_dependencies(db)
    ticket = _make_ticket(db, deps)
    part = _make_part(db)
    user = make_plain_user(db)

    tp = ticket_part_service.create(db, TicketPartCreate(
        ticket_id=ticket.id, part_id=part.id, status="shipped",
        carrier="USPS", tracking_number="9400111202555842761234",
    ), user.id)

    sent = {}

    def fake_send_email(db, to_address, subject, body):
        sent["to_address"] = to_address
        sent["body"] = body

    monkeypatch.setattr("app.services.note_service.send_email", fake_send_email)

    # tasks.py opens its own SessionLocal internally; point it at the same
    # test database the `db` fixture uses.
    import app.workers.tasks as tasks_module
    from tests.conftest import TestSessionLocal
    monkeypatch.setattr(tasks_module, "SessionLocal", TestSessionLocal)

    notify_customer_of_part_status_change(tp.id)

    notes = crud_note.get_multi(db)
    assert len(notes) == 1
    assert notes[0].direction == "outbound"
    assert notes[0].ticket_id == ticket.id
    assert notes[0].customer_id == deps["customer"].id
    assert "USPS" in notes[0].content
    assert sent["to_address"] == deps["customer"].email


def test_ticket_part_create_and_update_appear_in_audit_log(db):
    """Regression test: ticket_part_service previously had zero AuditLog coverage at all -- no TicketPart creation or edit ever showed up in the Audit Log."""
    from app.crud.audit_log import crud_audit_log

    deps = make_ticket_dependencies(db)
    ticket = _make_ticket(db, deps)
    part = _make_part(db)
    user = make_plain_user(db)

    tp = ticket_part_service.create(db, TicketPartCreate(
        ticket_id=ticket.id, part_id=part.id, status="needed",
    ), user.id)

    ticket_part_service.update(db, tp.id, TicketPartUpdate(carrier="USPS"), user.id)

    entries = crud_audit_log.get_multi(db, limit=500)
    actions = [e.action for e in entries if e.entity_type == "ticket" and e.entity_id == ticket.id]
    assert "ticket_part_created" in actions
    assert "ticket_part_updated" in actions
