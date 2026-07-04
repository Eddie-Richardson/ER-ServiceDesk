# ER-ServiceDesk/tests/factories.py
# Test data factories
"""
Small helper functions for creating supporting records directly via the
ORM (bypassing the API) so individual tests can focus on the behavior
actually under test instead of repeating setup boilerplate.
"""

from app.models.customer import Customer
from app.models.device import Device
from app.models.ticket_category import TicketCategory
from app.models.ticket_type import TicketType
from app.models.ticket_status import TicketStatus
from app.models.ticket_stage import TicketStage
from app.models.ticket_type_stage import TicketTypeStage


def make_customer(db, email="customer@example.com") -> Customer:
    """Create and persist a minimal Customer record."""
    obj = Customer(first_name="Test", last_name="Customer", email=email)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def make_device(db, customer_id: int) -> Device:
    """Create and persist a minimal Device record owned by the given customer."""
    obj = Device(customer_id=customer_id, device_type="Laptop")
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def make_ticket_category(db, name="Hardware") -> TicketCategory:
    """Create and persist a minimal TicketCategory record."""
    obj = TicketCategory(name=name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def make_ticket_type(db, name="Repair") -> TicketType:
    """Create and persist a minimal TicketType record."""
    obj = TicketType(name=name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def make_ticket_status(db, name="Open") -> TicketStatus:
    """Create and persist a minimal TicketStatus record."""
    obj = TicketStatus(name=name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def make_ticket_stage(db, name="Diagnosing") -> TicketStage:
    """Create and persist a minimal TicketStage record."""
    obj = TicketStage(name=name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def allow_stage_for_type(db, type_id: int, stage_id: int) -> TicketTypeStage:
    """Create an allow-list entry permitting a stage for a given ticket type."""
    obj = TicketTypeStage(type_id=type_id, stage_id=stage_id)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def make_ticket_dependencies(db):
    """
    Create the full minimal set of records a Ticket's foreign keys require.

    Returns:
        A dict with customer, device, category, type, and status objects,
        ready to plug their `.id` into a ticket creation payload.
    """
    customer = make_customer(db)
    device = make_device(db, customer.id)
    category = make_ticket_category(db)
    ttype = make_ticket_type(db)
    status = make_ticket_status(db)
    return {
        "customer": customer,
        "device": device,
        "category": category,
        "type": ttype,
        "status": status,
    }
