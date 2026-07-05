# ER-ServiceDesk/app/crud/invoice.py
# CRUD operations for the Invoice model.
"""
Database access layer for a bill generated for work performed on a ticket.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate

class InvoiceCRUD:
    """Direct database access for Invoice records."""

    def get(self, db: Session, id: int) -> Invoice | None:
        """
        Fetch a single Invoice by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Invoice instance, or None if no record exists.
        """
        return db.query(Invoice).filter(Invoice.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple Invoice records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Invoice instances.
        """
        return db.query(Invoice).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: InvoiceCreate) -> Invoice:
        """
        Insert a new Invoice record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed Invoice instance.
        """
        obj = Invoice(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Invoice, obj_in: InvoiceUpdate) -> Invoice:
        """
        Apply a partial update to an existing Invoice record.

        Args:
            db: Active database session.
            db_obj: The existing Invoice instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed Invoice instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a Invoice record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(Invoice).filter(Invoice.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_invoice = InvoiceCRUD()
