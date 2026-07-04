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
from app.schemas.ticket import TicketCreate, TicketUpdate

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

        Args:
            db: Active database session.
            type_id: The ticket's type_id.
            stage_id: The stage_id being set, if any.

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
        """
        Fetch a single Ticket by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Ticket instance, or None if not found.
        """
        return crud_ticket.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Ticket records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Ticket instances.
        """
        return crud_ticket.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: TicketCreate):
        """
        Create a new Ticket using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created Ticket instance.

        Raises:
            HTTPException: 400 if stage_id is set but not allowed for
                the ticket's type_id.
        """
        self._validate_stage_for_type(db, obj_in.type_id, obj_in.stage_id)
        return crud_ticket.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: TicketUpdate):
        """
        Update an existing Ticket using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Ticket instance.

        Raises:
            HTTPException: 400 if the resulting stage_id is not allowed
                for the resulting type_id.
        """
        db_obj = crud_ticket.get(db, id)

        update_data = obj_in.dict(exclude_unset=True)
        effective_type_id = update_data.get("type_id", db_obj.type_id)
        effective_stage_id = update_data.get("stage_id", db_obj.stage_id)
        self._validate_stage_for_type(db, effective_type_id, effective_stage_id)

        return crud_ticket.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a Ticket by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_ticket.delete(db, id)

ticket_service = TicketService()
