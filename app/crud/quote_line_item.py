# ER-ServiceDesk/app/crud/quote_line_item.py
"""
Database access layer for a single service line on a quote.
"""

from sqlalchemy.orm import Session
from app.models.quote_line_item import QuoteLineItem
from app.schemas.quote_line_item import QuoteLineItemUpdate


class QuoteLineItemCRUD:
    """Direct database access for QuoteLineItem records."""

    def get(self, db: Session, id: int) -> QuoteLineItem | None:
        return db.query(QuoteLineItem).filter(QuoteLineItem.id == id).first()

    def get_by_quote(self, db: Session, quote_id: int):
        return db.query(QuoteLineItem).filter(QuoteLineItem.quote_id == quote_id).all()

    def create(self, db: Session, quote_id: int, quantity: int, unit_price, service_id: int | None = None, service_name: str | None = None, part_id: int | None = None, part_name: str | None = None) -> QuoteLineItem:
        """
        Takes explicit fields rather than a schema, since the *_name
        fields and unit_price are server-computed snapshots never
        accepted from the client -- see quote_service.add_line_item()
        for where this actually gets called from, including the
        "exactly one of service/part" validation this layer doesn't
        enforce itself.
        """
        obj = QuoteLineItem(
            quote_id=quote_id, quantity=quantity, unit_price=unit_price,
            service_id=service_id, service_name=service_name,
            part_id=part_id, part_name=part_name,
        )
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: QuoteLineItem, obj_in: QuoteLineItemUpdate) -> QuoteLineItem:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(QuoteLineItem).filter(QuoteLineItem.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_quote_line_item = QuoteLineItemCRUD()
