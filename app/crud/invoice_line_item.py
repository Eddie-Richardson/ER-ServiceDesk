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
        """
        Fetch a single InvoiceLineItem by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching InvoiceLineItem instance, or None if not found.
        """
        return db.query(InvoiceLineItem).filter(InvoiceLineItem.id == id).first()

    def get_by_invoice(self, db: Session, invoice_id: int):
        """
        Fetch every line item on a given invoice.

        Args:
            db: Active database session.
            invoice_id: The invoice to look up line items for.

        Returns:
            A list of InvoiceLineItem instances for that invoice.
        """
        return db.query(InvoiceLineItem).filter(InvoiceLineItem.invoice_id == invoice_id).all()

    def create(self, db: Session, invoice_id: int, quantity: int, unit_price, service_id: int | None = None, service_name: str | None = None, part_id: int | None = None, part_name: str | None = None) -> InvoiceLineItem:
        """
        Insert a new InvoiceLineItem record. Takes explicit fields
        rather than a schema, since the *_name fields and unit_price
        are server-computed snapshots never accepted from the client.

        Args:
            db: Active database session.
            invoice_id: The invoice this line item belongs to.
            quantity: How many units.
            unit_price: The service's price or the part's
                selling_price at this moment, snapshotted.
            service_id: The service being billed, if this is a service line.
            service_name: The service's name at this moment, snapshotted.
            part_id: The part being billed, if this is a part line.
            part_name: The part's name at this moment, snapshotted.

        Returns:
            The newly created, refreshed InvoiceLineItem instance.
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
        """
        Apply a partial update to an existing InvoiceLineItem record.

        Args:
            db: Active database session.
            db_obj: The existing InvoiceLineItem instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed InvoiceLineItem instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete an InvoiceLineItem record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(InvoiceLineItem).filter(InvoiceLineItem.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_invoice_line_item = InvoiceLineItemCRUD()
