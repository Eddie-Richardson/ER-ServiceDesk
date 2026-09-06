# ER-ServiceDesk/app/models/quote_line_item.py
"""
ORM model for a single line on a quote -- either a service (labor) or
a real inventory part, how many, and its price at the moment it was
added. Deliberately one unified line-item shape covering both, not two
separate tables -- matches the real invoice this was modeled on, which
lists labor and parts together in one list, taxed together at the end.

Exactly one of service_id/part_id is set per line item, never both,
never neither -- enforced at the service layer (see quote_service.py's
add_line_item()), not a database constraint.

unit_price is deliberately a snapshot, not a live lookup against
Service.price/Part.selling_price -- if the shop's price changes later,
an already-issued quote should keep showing what the customer was
actually quoted, not silently drift.
"""

from sqlalchemy import Column, Integer, Numeric, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class QuoteLineItem(Base):
    """
    Represents one line on a quote -- either a service or a part.

    Attributes:
        service_id: The service being quoted, if this line item is a
            service. None if it's a part instead.
        service_name: The service's name at the moment this line item
            was added -- a snapshot, same reasoning as unit_price. Keeps
            this line item fully self-contained and correctly
            renderable even if the Service is later renamed or
            deleted entirely. None if this line item is a part.
        part_id: The part being quoted, if this line item is a part.
            None if it's a service instead.
        part_name: The part's name at the moment this line item was
            added -- same snapshot reasoning as service_name. None if
            this line item is a service.
        unit_price: The service's price or the part's selling_price at
            the moment this line item was added -- a snapshot, not a
            live lookup, so a later price change never alters an
            already-issued quote.
    """
    __tablename__ = "quote_line_items"
    id = Column(Integer, primary_key=True, index=True)
    quote_id = Column(Integer, ForeignKey("quotes.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    service_name = Column(String, nullable=True)
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="SET NULL"), nullable=True)
    part_name = Column(String, nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric, nullable=False)

    quote = relationship("Quote", back_populates="line_items")
    service = relationship("Service")
    part = relationship("Part")
