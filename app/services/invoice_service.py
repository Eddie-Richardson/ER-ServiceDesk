# ER-ServiceDesk/app/services/invoice_service.py
# Service layer for Invoice.
#
# Provides business logic for Invoice operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.invoice import crud_invoice
from app.schemas.invoice import InvoiceCreate, InvoiceUpdate

class InvoiceService:
    # Retrieves a single Invoice by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single Invoice instance.
        """
        return crud_invoice.get(db, id)

    # Retrieves multiple Invoice records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Invoice records.
        """
        return crud_invoice.get_multi(db, skip, limit)

    # Creates a new Invoice.
    def create(self, db: Session, obj_in: InvoiceCreate):
        """
        Creates a new Invoice using validated input data.
        """
        return crud_invoice.create(db, obj_in)

    # Updates an existing Invoice.
    def update(self, db: Session, id: int, obj_in: InvoiceUpdate):
        """
        Updates an existing Invoice using validated input data.
        """
        db_obj = crud_invoice.get(db, id)
        return crud_invoice.update(db, db_obj, obj_in)

    # Deletes an Invoice by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes an Invoice instance.
        """
        return crud_invoice.delete(db, id)

invoice_service = InvoiceService()
