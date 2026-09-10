# ER-ServiceDesk/tests/test_ticket_audit_log.py
"""
Covers TicketService.update()'s audit log entries -- only genuinely
changed fields are listed (not every field in a full-payload save),
and the entry shows real before/after values, not just which fields
changed.
"""

from tests.factories import make_full_ticket, make_plain_user


def test_ticket_update_audit_log_only_lists_genuinely_changed_fields(client, superuser_headers, db):
    """
    Regression test: the desktop's ticket form always sends the full
    payload on save (every field, not just the ones edited), matching
    the current values for anything untouched. The audit log used to
    report every field in the request as "changed" regardless of
    whether its value actually differed -- e.g. assigning a ticket to
    yourself showed up as if the customer, device, title, and every
    other field had also been edited. Now it should only list the
    field(s) that genuinely changed value.
    """
    ticket = make_full_ticket(db)

    full_payload = {
        "customer_id": ticket.customer_id,
        "device_id": ticket.device_id,
        "category_id": ticket.category_id,
        "type_id": ticket.type_id,
        "status_id": ticket.status_id,
        "priority": ticket.priority,
        "title": ticket.title,
        "assigned_to": None,
    }
    update_resp = client.put(f"/tickets/{ticket.id}", json=full_payload, headers=superuser_headers)
    assert update_resp.status_code == 200, update_resp.text

    other_user = make_plain_user(db, email="assign_target@example.com")

    second_payload = dict(full_payload)
    second_payload["assigned_to"] = other_user.id
    update_resp = client.put(f"/tickets/{ticket.id}", json=second_payload, headers=superuser_headers)
    assert update_resp.status_code == 200, update_resp.text

    audit_resp = client.get("/audit_logs/", headers=superuser_headers)
    assert audit_resp.status_code == 200
    entries = [e for e in audit_resp.json() if e["entity_type"] == "ticket" and e["entity_id"] == ticket.id and e["action"] == "ticket_updated"]
    assert entries, "Expected at least one ticket_updated audit log entry"

    most_recent = entries[0]
    assert "Assigned To" in most_recent["details"]
    assert "Unassigned" in most_recent["details"]
    assert other_user.full_name in most_recent["details"]
    assert "Customer" not in most_recent["details"]
    assert "Title" not in most_recent["details"]
    assert "Category" not in most_recent["details"]


def test_ticket_update_audit_log_shows_real_before_after_values(client, superuser_headers, db):
    """The audit log shows the actual old and new values for a genuine change, not just that a field changed -- e.g. "Title: 'Old' -> 'New'", not just "title" listed as changed."""
    ticket = make_full_ticket(db)

    update_resp = client.put(f"/tickets/{ticket.id}", json={"title": "A Genuinely New Title", "priority": "urgent"}, headers=superuser_headers)
    assert update_resp.status_code == 200, update_resp.text

    audit_resp = client.get("/audit_logs/", headers=superuser_headers)
    entries = [e for e in audit_resp.json() if e["entity_type"] == "ticket" and e["entity_id"] == ticket.id and e["action"] == "ticket_updated"]
    details = entries[0]["details"]

    assert "Title" in details
    assert "A Genuinely New Title" in details
    assert ticket.title in details  # the real old value, not just the field name
    assert "Priority" in details
    assert "urgent" in details
    assert "normal" in details  # the ticket's real starting priority
