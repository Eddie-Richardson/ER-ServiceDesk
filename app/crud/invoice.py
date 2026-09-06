# ER-ServiceDesk/app/crud/invoice.py
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
        return db.query(Invoice).filter(Invoice.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(Invoice).offset(skip).limit(limit).all()

    def get_by_ticket(self, db: Session, ticket_id: int):
        return db.query(Invoice).filter(Invoice.ticket_id == ticket_id).all()

    def create(self, db: Session, obj_in: InvoiceCreate) -> Invoice:
        obj = Invoice(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Invoice, obj_in: InvoiceUpdate) -> Invoice:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, db_obj: Invoice):
        db.delete(db_obj)
        db.commit()

crud_invoice = InvoiceCRUD()
