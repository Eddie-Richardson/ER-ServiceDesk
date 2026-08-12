# ER-ServiceDesk/app/models/quote_line_item.py
# ORM model for a single service line on a quote
"""
ORM model for a single service line on a quote -- which service, how
many, and the service's price at the moment it was added.

unit_price is deliberately a snapshot, not a live lookup against
Service.price -- if the shop's price for a service changes later, an
already-issued quote should keep showing what the customer was
actually quoted, not silently drift.
"""

from sqlalchemy import Column, Integer, Numeric, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class QuoteLineItem(Base):
    """
    Represents one service line on a quote.

    Attributes:
        id: Primary key.
        quote_id: The quote this line item belongs to.
        service_id: The service being quoted.
        service_name: The service's name at the moment this line item
            was added -- a snapshot, same reasoning as unit_price. Keeps
            this line item fully self-contained and correctly
            renderable even if the Service is later renamed or
            deleted entirely.
        quantity: How many units of this service.
        unit_price: The service's price at the moment this line item
            was added -- a snapshot, not a live lookup, so a later
            price change on the Service itself never alters an
            already-issued quote.
    """
    __tablename__ = "quote_line_items"
    id = Column(Integer, primary_key=True, index=True)
    quote_id = Column(Integer, ForeignKey("quotes.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    service_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric, nullable=False)

    quote = relationship("Quote", back_populates="line_items")
    service = relationship("Service")
