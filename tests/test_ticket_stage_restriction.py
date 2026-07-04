# ER-ServiceDesk/tests/test_ticket_stage_restriction.py
# Tests for the opt-in TicketTypeStage allow-list enforcement.
"""
Covers TicketService's stage-restriction rule: a TicketType with zero
configured allow-list entries stays unrestricted (any stage is valid);
once at least one entry exists for that type, only allow-listed stages
are accepted.
"""

from tests.factories import (
    make_ticket_dependencies,
    make_ticket_stage,
    allow_stage_for_type,
)


def _ticket_payload(deps, stage_id=None):
    return {
        "customer_id": deps["customer"].id,
        "device_id": deps["device"].id,
        "category_id": deps["category"].id,
        "type_id": deps["type"].id,
        "status_id": deps["status"].id,
        "stage_id": stage_id,
        "title": "Test ticket",
        "priority": "normal",
    }


def test_unrestricted_type_accepts_any_stage(client, db, agent_headers):
    """A ticket type with no allow-list entries accepts any existing stage."""
    deps = make_ticket_dependencies(db)
    stage = make_ticket_stage(db, name="Diagnosing")

    response = client.post(
        "/tickets/",
        json=_ticket_payload(deps, stage_id=stage.id),
        headers=agent_headers,
    )

    assert response.status_code == 200
    assert response.json()["stage_id"] == stage.id


def test_restricted_type_accepts_allowed_stage(client, db, agent_headers):
    """Once an allow-list entry exists for a type, that specific stage is accepted."""
    deps = make_ticket_dependencies(db)
    allowed_stage = make_ticket_stage(db, name="Assembling")
    allow_stage_for_type(db, type_id=deps["type"].id, stage_id=allowed_stage.id)

    response = client.post(
        "/tickets/",
        json=_ticket_payload(deps, stage_id=allowed_stage.id),
        headers=agent_headers,
    )

    assert response.status_code == 200
    assert response.json()["stage_id"] == allowed_stage.id


def test_restricted_type_rejects_disallowed_stage(client, db, agent_headers):
    """Once a type has an allow-list, a stage NOT on that list is rejected."""
    deps = make_ticket_dependencies(db)
    allowed_stage = make_ticket_stage(db, name="Assembling")
    other_stage = make_ticket_stage(db, name="Burn-in Test")
    allow_stage_for_type(db, type_id=deps["type"].id, stage_id=allowed_stage.id)

    response = client.post(
        "/tickets/",
        json=_ticket_payload(deps, stage_id=other_stage.id),
        headers=agent_headers,
    )

    assert response.status_code == 400


def test_update_to_disallowed_stage_is_rejected(client, db, agent_headers):
    """Updating an existing ticket to a disallowed stage is rejected the same way creation is."""
    deps = make_ticket_dependencies(db)
    allowed_stage = make_ticket_stage(db, name="Assembling")
    other_stage = make_ticket_stage(db, name="Burn-in Test")
    allow_stage_for_type(db, type_id=deps["type"].id, stage_id=allowed_stage.id)

    create_response = client.post(
        "/tickets/",
        json=_ticket_payload(deps, stage_id=allowed_stage.id),
        headers=agent_headers,
    )
    ticket_id = create_response.json()["id"]

    update_response = client.put(
        f"/tickets/{ticket_id}",
        json={"stage_id": other_stage.id},
        headers=agent_headers,
    )

    assert update_response.status_code == 400


def test_ticket_with_no_stage_is_always_allowed(client, db, agent_headers):
    """A ticket with stage_id left null is valid regardless of any allow-list."""
    deps = make_ticket_dependencies(db)
    stage = make_ticket_stage(db, name="Assembling")
    allow_stage_for_type(db, type_id=deps["type"].id, stage_id=stage.id)

    response = client.post(
        "/tickets/",
        json=_ticket_payload(deps, stage_id=None),
        headers=agent_headers,
    )

    assert response.status_code == 200
    assert response.json()["stage_id"] is None
