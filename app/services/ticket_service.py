# ER-ServiceDesk/app/services/ticket_service.py
# Service layer for Ticket.
"""
Business logic for a support/repair job tracked from intake to completion.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from app.crud.ticket import crud_ticket
from app.crud.ticket_type_stage import crud_ticket_type_stage
from app.crud.status_history import crud_status_history
from app.crud.customer import crud_customer
from app.crud.device import crud_device
from app.crud.ticket_category import crud_ticket_category
from app.crud.ticket_stage import crud_ticket_stage
from app.crud.ticket_status import crud_ticket_status
from app.crud.ticket_type import crud_ticket_type
from app.crud.user import crud_user
from app.crud.location import crud_location
from app.schemas.ticket import TicketCreate, TicketUpdate
from app.schemas.status_history import StatusHistoryCreate
from app.services.audit_log_service import audit_log_service

class TicketService:
    """Business logic for Ticket operations."""

    def _validate_stage_for_type(self, db: Session, type_id: int, stage_id: int | None) -> None:
        """
        Enforce that stage_id, if given, is allowed for the ticket's type.

        A ticket type with no configured allow-list entries is treated as
        unrestricted (any stage is valid) -- restrictions only take effect
        once at least one entry has been added for that type via
        /ticket_type_stages. This keeps existing tickets/types working
        with no configuration required.

        Raises:
            HTTPException: 400 if the type has a configured allow-list and
                stage_id is not on it.
        """
        if stage_id is None:
            return

        configured_stages = crud_ticket_type_stage.get_for_type(db, type_id)
        if not configured_stages:
            return  # unrestricted: no allow-list configured for this type

        if not crud_ticket_type_stage.is_allowed(db, type_id, stage_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This stage is not allowed for the ticket's type",
            )

    def get(self, db: Session, id: int):
        return crud_ticket.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_ticket.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: TicketCreate, current_user_id: int):
        """
        Also records the ticket's initial status as its first
        StatusHistory entry, so a ticket's history is never missing
        where it started.

        Raises:
            HTTPException: 400 if stage_id is set but not allowed for
                the ticket's type_id.
        """
        self._validate_stage_for_type(db, obj_in.type_id, obj_in.stage_id)
        new_ticket = crud_ticket.create(db, obj_in)

        crud_status_history.create(db, StatusHistoryCreate(
            ticket_id=new_ticket.id,
            status_id=new_ticket.status_id,
            changed_by=current_user_id,
        ))

        audit_log_service.log(
            db, "ticket_created", "ticket", new_ticket.id, user_id=current_user_id,
            details=f"Created ticket: {new_ticket.title}",
        )

        return new_ticket

    def update(self, db: Session, id: int, obj_in: TicketUpdate, current_user_id: int):
        """
        If status_id actually changes as a result, also records a
        StatusHistory entry for it -- who changed it, to what, and
        when.

        Raises:
            HTTPException: 400 if the resulting stage_id is not allowed
                for the resulting type_id.
        """
        db_obj = crud_ticket.get(db, id)
        previous_status_id = db_obj.status_id

        update_data = obj_in.model_dump(exclude_unset=True)
        effective_type_id = update_data.get("type_id", db_obj.type_id)
        effective_stage_id = update_data.get("stage_id", db_obj.stage_id)
        self._validate_stage_for_type(db, effective_type_id, effective_stage_id)

        old_values = {field: getattr(db_obj, field) for field in update_data if getattr(db_obj, field) != update_data[field]}
        changed_fields = list(old_values.keys())

        updated = crud_ticket.update(db, db_obj, obj_in)

        if "status_id" in update_data and update_data["status_id"] != previous_status_id:
            crud_status_history.create(db, StatusHistoryCreate(
                ticket_id=id,
                status_id=update_data["status_id"],
                changed_by=current_user_id,
            ))

        if changed_fields:
            change_lines = [
                f"{self._field_display_name(field)}: {self._resolve_field_value(db, field, old_values[field])} -> {self._resolve_field_value(db, field, update_data[field])}"
                for field in changed_fields
            ]
            audit_log_service.log(
                db, "ticket_updated", "ticket", id, user_id=current_user_id,
                details="; ".join(change_lines),
            )

        return updated

    # Human-readable label for each TicketUpdate field, used in audit
    # log messages -- falls back to the raw field name for anything
    # not listed here, so a newly-added field degrades gracefully
    # rather than crashing.
    _FIELD_DISPLAY_NAMES = {
        "customer_id": "Customer",
        "device_id": "Device",
        "category_id": "Category",
        "type_id": "Ticket Type",
        "status_id": "Status",
        "stage_id": "Stage",
        "assigned_to": "Assigned To",
        "current_location_id": "Location",
        "title": "Title",
        "description": "Description",
        "priority": "Priority",
        "pickup_person": "Pickup Person",
        "accessories_included": "Accessories",
    }

    def _field_display_name(self, field: str) -> str:
        return self._FIELD_DISPLAY_NAMES.get(field, field)

    def _resolve_field_value(self, db: Session, field: str, value):
        """
        Resolves a raw field value to a real, readable string for the
        audit log -- e.g. assigned_to's raw user id becomes the actual
        person's name, not a number nobody reading the log later could
        make sense of. Resolved at the moment of logging (not looked
        up when the log is later viewed), so the audit trail stays
        accurate even if the referenced record is later renamed,
        reassigned, or deleted.

        Returns:
            The resolved display value, or "(none)" for a None value,
            or "(deleted)" if the referenced record can no longer be
            found (e.g. since deleted) -- either way, never a bare,
            meaningless id.
        """
        if value is None:
            return "Unassigned" if field == "assigned_to" else "(none)"

        resolvers = {
            "customer_id": lambda: (lambda c: f"{c.first_name} {c.last_name}" if c else None)(crud_customer.get(db, value)),
            "device_id": lambda: (lambda d: (" ".join(filter(None, [d.brand, d.model])) or d.device_type) if d else None)(crud_device.get(db, value)),
            "category_id": lambda: (lambda c: c.name if c else None)(crud_ticket_category.get(db, value)),
            "type_id": lambda: (lambda t: t.name if t else None)(crud_ticket_type.get(db, value)),
            "status_id": lambda: (lambda s: s.name if s else None)(crud_ticket_status.get(db, value)),
            "stage_id": lambda: (lambda s: s.name if s else None)(crud_ticket_stage.get(db, value)),
            "assigned_to": lambda: (lambda u: u.full_name if u else None)(crud_user.get(db, value)),
            "current_location_id": lambda: (lambda l: l.name if l else None)(crud_location.get(db, value)),
        }

        if field not in resolvers:
            return str(value)

        resolved = resolvers[field]()
        return resolved if resolved is not None else "(deleted)"

ticket_service = TicketService()
