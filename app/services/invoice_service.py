# ER-ServiceDesk/app/services/invoice_service.py
# Service layer for Invoice.
"""
Business logic for a bill generated for work performed on a ticket.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.invoice import crud_invoice
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate

class InvoiceService:
    """Business logic for Invoice operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Invoice by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Invoice instance, or None if not found.
        """
        return crud_invoice.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Invoice records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Invoice instances.
        """
        return crud_invoice.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: InvoiceCreate):
        """
        Create a new Invoice using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created Invoice instance.
        """
        return crud_invoice.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: InvoiceUpdate):
        """
        Update an existing Invoice using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Invoice instance.
        """
        db_obj = crud_invoice.get(db, id)
        return crud_invoice.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a Invoice by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_invoice.delete(db, id)

invoice_service = InvoiceService()
