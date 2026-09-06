# ER-ServiceDesk/app/models/invoice_line_item.py
"""
ORM model for a single line on an invoice -- either a service (labor)
or a real inventory part. Same shape and reasoning as QuoteLineItem.
Adding a PART line item to an invoice specifically (never a quote) is
what triggers real inventory deduction -- see invoice_service.py's
add_line_item().
"""

from sqlalchemy import Column, Integer, Numeric, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class InvoiceLineItem(Base):
    """
    Represents one line on an invoice -- either a service or a part.

    Attributes:
        service_id: The service being billed, if this line item is a
            service. None if it's a part instead.
        service_name: The service's name at the moment this line item
            was added -- a snapshot. None if this line item is a part.
        part_id: The part being billed, if this line item is a part.
            None if it's a service instead.
        part_name: The part's name at the moment this line item was
            added -- a snapshot. None if this line item is a service.
        unit_price: The service's price or the part's selling_price at
            the moment this line item was added -- a snapshot, not a
            live lookup, so a later price change never alters an
            already-issued invoice.
    """
    __tablename__ = "invoice_line_items"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    service_name = Column(String, nullable=True)
    part_id = Column(Integer, ForeignKey("parts.id", ondelete="SET NULL"), nullable=True)
    part_name = Column(String, nullable=True)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric, nullable=False)

    invoice = relationship("Invoice", back_populates="line_items")
    service = relationship("Service")
    part = relationship("Part")
