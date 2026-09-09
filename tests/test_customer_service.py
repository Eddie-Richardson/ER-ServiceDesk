# ER-ServiceDesk/tests/test_customer_service.py
"""
Covers CustomerService's real, non-obvious behaviors: duplicate email
rejection, audit logging only firing on a genuine change,
archive/unarchive being fully reversible, delete refusing to touch a
customer with real ticket/device history, and the actual date-math
behind automatic inactivity-based archiving eligibility.
"""

import pytest
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

from app.services.customer_service import customer_service
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.models.customer import Customer
from app.models.ticket import Ticket
from app.crud.audit_log import crud_audit_log
from tests.factories import make_customer, make_device, make_plain_user, make_ticket_dependencies


def _customer_create(email="newcustomer@example.com"):
    return CustomerCreate(first_name="New", last_name="Customer", email=email)


def _actor(db):
    return make_plain_user(db, email="actor@example.com").id


def test_create_rejects_a_duplicate_email(db):
    existing = make_customer(db)
    with pytest.raises(HTTPException) as exc_info:
        customer_service.create(db, _customer_create(email=existing.email), current_user_id=_actor(db))
    assert exc_info.value.status_code == 400


def test_update_rejects_changing_email_to_one_already_used_by_a_different_customer(db):
    customer_a = make_customer(db, email="a@example.com")
    customer_b = make_customer(db, email="b@example.com")

    with pytest.raises(HTTPException) as exc_info:
        customer_service.update(db, customer_a.id, CustomerUpdate(email="b@example.com"), current_user_id=_actor(db))
    assert exc_info.value.status_code == 400

    db.refresh(customer_a)
    assert customer_a.email == "a@example.com"


def test_update_only_logs_an_audit_entry_when_something_genuinely_changed(db):
    customer = make_customer(db)
    actor_id = _actor(db)

    customer_service.update(db, customer.id, CustomerUpdate(first_name=customer.first_name), current_user_id=actor_id)
    noop_entries = [e for e in crud_audit_log.get_multi(db, limit=500) if e.entity_type == "customer" and e.entity_id == customer.id and e.action == "customer_updated"]
    assert len(noop_entries) == 0

    customer_service.update(db, customer.id, CustomerUpdate(first_name="Genuinely Different"), current_user_id=actor_id)
    real_entries = [e for e in crud_audit_log.get_multi(db, limit=500) if e.entity_type == "customer" and e.entity_id == customer.id and e.action == "customer_updated"]
    assert len(real_entries) == 1


def test_archive_and_unarchive_are_genuinely_reversible(db):
    customer = make_customer(db)
    actor_id = _actor(db)

    customer_service.archive(db, customer.id, current_user_id=actor_id)
    db.refresh(customer)
    assert customer.is_archived is True

    customer_service.unarchive(db, customer.id, current_user_id=actor_id)
    db.refresh(customer)
    assert customer.is_archived is False

    entries = crud_audit_log.get_multi(db, limit=500)
    actions = [e.action for e in entries if e.entity_type == "customer" and e.entity_id == customer.id]
    assert "customer_archived" in actions
    assert "customer_unarchived" in actions


def test_archive_accepts_a_null_user_id_for_the_automatic_system_initiated_case(db):
    """archive_inactive_customers() calls this with current_user_id=None, since no admin genuinely triggered it -- the automatic backstop must not raise on a null actor."""
    customer = make_customer(db)
    customer_service.archive(db, customer.id, current_user_id=None)
    db.refresh(customer)
    assert customer.is_archived is True


def test_delete_rejects_a_customer_with_tickets_on_file(db):
    deps = make_ticket_dependencies(db)
    ticket = Ticket(
        customer_id=deps["customer"].id, device_id=deps["device"].id,
        category_id=deps["category"].id, type_id=deps["type"].id,
        status_id=deps["status"].id, title="Real ticket", priority="normal",
    )
    db.add(ticket)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        customer_service.delete(db, deps["customer"].id, current_user_id=_actor(db))
    assert exc_info.value.status_code == 400
    assert db.query(Customer).filter_by(id=deps["customer"].id).first() is not None


def test_delete_rejects_a_customer_with_devices_on_file(db):
    customer = make_customer(db)
    make_device(db, customer.id)

    with pytest.raises(HTTPException) as exc_info:
        customer_service.delete(db, customer.id, current_user_id=_actor(db))
    assert exc_info.value.status_code == 400
    assert db.query(Customer).filter_by(id=customer.id).first() is not None


def test_delete_succeeds_for_a_customer_with_no_tickets_or_devices(db):
    customer = make_customer(db)
    customer_id = customer.id

    customer_service.delete(db, customer_id, current_user_id=_actor(db))

    assert db.query(Customer).filter_by(id=customer_id).first() is None


def test_eligible_for_archiving_uses_own_created_at_when_theres_never_been_a_ticket(db):
    customer = make_customer(db)
    customer.created_at = datetime.now(timezone.utc) - timedelta(days=200)
    db.commit()

    eligible = customer_service.get_customers_eligible_for_archiving(db, threshold_months=6)
    assert customer.id in [c.id for c in eligible]


def test_eligible_for_archiving_uses_most_recent_ticket_not_customers_own_created_at(db):
    """A customer created long ago but with a genuinely recent ticket is NOT eligible -- their real, most recent activity is what matters, not when their record was first created."""
    deps = make_ticket_dependencies(db)
    customer = deps["customer"]
    customer.created_at = datetime.now(timezone.utc) - timedelta(days=400)
    db.commit()

    recent_ticket = Ticket(
        customer_id=customer.id, device_id=deps["device"].id,
        category_id=deps["category"].id, type_id=deps["type"].id,
        status_id=deps["status"].id, title="Just happened", priority="normal",
    )
    db.add(recent_ticket)
    db.commit()

    eligible = customer_service.get_customers_eligible_for_archiving(db, threshold_months=6)
    assert customer.id not in [c.id for c in eligible]


def test_already_archived_customers_are_never_returned_regardless_of_inactivity(db):
    customer = make_customer(db)
    customer.created_at = datetime.now(timezone.utc) - timedelta(days=1000)
    customer.is_archived = True
    db.commit()

    eligible = customer_service.get_customers_eligible_for_archiving(db, threshold_months=1)
    assert customer.id not in [c.id for c in eligible]
