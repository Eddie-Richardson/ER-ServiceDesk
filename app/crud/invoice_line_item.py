# ER-ServiceDesk/app/crud/invoice_line_item.py
# CRUD operations for the InvoiceLineItem model.
"""
Database access layer for a single service line on an invoice.
"""

from sqlalchemy.orm import Session
from app.models.invoice_line_item import InvoiceLineItem
from app.schemas.invoice_line_item import InvoiceLineItemUpdate


class InvoiceLineItemCRUD:
    """Direct database access for InvoiceLineItem records."""

    def get(self, db: Session, id: int) -> InvoiceLineItem | None:
        return db.query(InvoiceLineItem).filter(InvoiceLineItem.id == id).first()

    def get_by_invoice(self, db: Session, invoice_id: int):
        return db.query(InvoiceLineItem).filter(InvoiceLineItem.invoice_id == invoice_id).all()

    def create(self, db: Session, invoice_id: int, quantity: int, unit_price, service_id: int | None = None, service_name: str | None = None, part_id: int | None = None, part_name: str | None = None) -> InvoiceLineItem:
        """
        Takes explicit fields rather than a schema, since the *_name
        fields and unit_price are server-computed snapshots never
        accepted from the client.
        """
        obj = InvoiceLineItem(
            invoice_id=invoice_id, quantity=quantity, unit_price=unit_price,
            service_id=service_id, service_name=service_name,
            part_id=part_id, part_name=part_name,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: InvoiceLineItem, obj_in: InvoiceLineItemUpdate) -> InvoiceLineItem:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(InvoiceLineItem).filter(InvoiceLineItem.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_invoice_line_item = InvoiceLineItemCRUD()
