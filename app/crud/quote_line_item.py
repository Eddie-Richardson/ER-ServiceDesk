# ER-ServiceDesk/app/crud/quote_line_item.py
# CRUD operations for the QuoteLineItem model.
"""
Database access layer for a single service line on a quote.
"""

from sqlalchemy.orm import Session
from app.models.quote_line_item import QuoteLineItem
from app.schemas.quote_line_item import QuoteLineItemUpdate


class QuoteLineItemCRUD:
    """Direct database access for QuoteLineItem records."""

    def get(self, db: Session, id: int) -> QuoteLineItem | None:
        """
        Fetch a single QuoteLineItem by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching QuoteLineItem instance, or None if not found.
        """
        return db.query(QuoteLineItem).filter(QuoteLineItem.id == id).first()

    def get_by_quote(self, db: Session, quote_id: int):
        """
        Fetch every line item on a given quote.

        Args:
            db: Active database session.
            quote_id: The quote to look up line items for.

        Returns:
            A list of QuoteLineItem instances for that quote.
        """
        return db.query(QuoteLineItem).filter(QuoteLineItem.quote_id == quote_id).all()

    def create(self, db: Session, quote_id: int, service_id: int, service_name: str, quantity: int, unit_price) -> QuoteLineItem:
        """
        Insert a new QuoteLineItem record. Takes explicit fields
        rather than a schema, since service_name and unit_price are
        server-computed snapshots never accepted from the client --
        see quote_service.add_line_item() for where this actually
        gets called from.

        Args:
            db: Active database session.
            quote_id: The quote this line item belongs to.
            service_id: The service being quoted.
            service_name: The service's name at this moment, snapshotted.
            quantity: How many units.
            unit_price: The service's price at this moment, snapshotted.

        Returns:
            The newly created, refreshed QuoteLineItem instance.
        """
        obj = QuoteLineItem(quote_id=quote_id, service_id=service_id, service_name=service_name, quantity=quantity, unit_price=unit_price)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: QuoteLineItem, obj_in: QuoteLineItemUpdate) -> QuoteLineItem:
        """
        Apply a partial update to an existing QuoteLineItem record.

        Args:
            db: Active database session.
            db_obj: The existing QuoteLineItem instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed QuoteLineItem instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a QuoteLineItem record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(QuoteLineItem).filter(QuoteLineItem.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_quote_line_item = QuoteLineItemCRUD()
