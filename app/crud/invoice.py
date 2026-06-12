# ER-ServiceDesk/app/crud/invoice.py
# CRUD operations for the Invoice model.
#
# Provides database access for creating, reading, updating, and deleting Invoice records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.invoice import Invoice
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate

class InvoiceCRUD:
    # Retrieves a single Invoice by ID.
    def get(self, db: Session, id: int) -> Invoice | None:
        """
        Returns a single Invoice instance matching the given ID.
        """
        return db.query(Invoice).filter(Invoice.id == id).first()

    # Retrieves multiple Invoice records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Invoice records with pagination support.
        """
        return db.query(Invoice).offset(skip).limit(limit).all()

    # Creates a new Invoice record.
    def create(self, db: Session, obj_in: InvoiceCreate) -> Invoice:
        """
        Creates a new Invoice using the provided input schema.
        """
        obj = Invoice(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing Invoice record.
    def update(self, db: Session, db_obj: Invoice, obj_in: InvoiceUpdate) -> Invoice:
        """
        Updates the given Invoice instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes an Invoice record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the Invoice instance matching the given ID.
        """
        obj = db.query(Invoice).filter(Invoice.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_invoice = InvoiceCRUD()
