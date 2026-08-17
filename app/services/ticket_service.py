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

        updated = crud_ticket.update(db, db_obj, obj_in)

        if "status_id" in update_data and update_data["status_id"] != previous_status_id:
            crud_status_history.create(db, StatusHistoryCreate(
                ticket_id=id,
                status_id=update_data["status_id"],
                changed_by=current_user_id,
            ))

        changed_fields = list(update_data.keys())
        if changed_fields:
            audit_log_service.log(
                db, "ticket_updated", "ticket", id, user_id=current_user_id,
                details=f"Changed fields: {', '.join(changed_fields)}",
            )

        return updated

ticket_service = TicketService()
