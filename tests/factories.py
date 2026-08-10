# ER-ServiceDesk/tests/factories.py
# Test data factories
"""
Small helper functions for creating supporting records directly via the
ORM (bypassing the API) so individual tests can focus on the behavior
actually under test instead of repeating setup boilerplate.
"""

from app.models.customer import Customer
from app.models.device import Device
from app.models.ticket import Ticket
from app.models.ticket_category import TicketCategory
from app.models.ticket_type import TicketType
from app.models.ticket_status import TicketStatus
from app.models.ticket_stage import TicketStage
from app.models.ticket_type_stage import TicketTypeStage
from app.models.role import Role
from app.models.permission import Permission
from app.models.invoice import Invoice
from app.models.user import User
from app.core.security import hash_password


def make_role(db, name="Technician") -> Role:
    """Create and persist a minimal Role record."""
    obj = Role(name=name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def make_permission(db, name="ticket.view") -> Permission:
    """Create and persist a minimal Permission record."""
    obj = Permission(name=name)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def make_plain_user(db, email="plain_user@example.com") -> User:
    """Create and persist a minimal User record (not authenticated -- just a target FK)."""
    obj = User(
        email=email,
        hashed_password=hash_password("Irrelevant123!"),
        first_name="Plain",
        last_name="User",
        is_active=True,
        is_superuser=False,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def make_full_ticket(db) -> Ticket:
    """Create a Ticket plus every dependency it requires, and return the Ticket itself."""
    deps = make_ticket_dependencies(db)
    ticket = Ticket(
        customer_id=deps["customer"].id,
        device_id=deps["device"].id,
        category_id=deps["category"].id,
        type_id=deps["type"].id,
        status_id=deps["status"].id,
        title="Test ticket",
        priority="normal",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def make_invoice(db, ticket_id: int) -> Invoice:
    """Create and persist a minimal Invoice record for the given ticket."""
    obj = Invoice(ticket_id=ticket_id, amount=100.0, is_paid=False)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


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
