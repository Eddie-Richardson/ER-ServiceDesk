# ER-ServiceDesk/app/models/invoice_line_item.py
# ORM model for a single service line on an invoice
"""
ORM model for a single service line on an invoice -- which service,
how many, and the service's price at the moment it was added. Same
price-snapshot reasoning as QuoteLineItem.
"""

from sqlalchemy import Column, Integer, Numeric, String, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class InvoiceLineItem(Base):
    """
    Represents one service line on an invoice.

    Attributes:
        id: Primary key.
        invoice_id: The invoice this line item belongs to.
        service_id: The service being billed.
        service_name: The service's name at the moment this line item
            was added -- a snapshot, same reasoning as unit_price.
        quantity: How many units of this service.
        unit_price: The service's price at the moment this line item
            was added -- a snapshot, not a live lookup, so a later
            price change on the Service itself never alters an
            already-issued invoice.
    """
    __tablename__ = "invoice_line_items"
    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="SET NULL"), nullable=True)
    service_name = Column(String, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    unit_price = Column(Numeric, nullable=False)

    invoice = relationship("Invoice", back_populates="line_items")
    service = relationship("Service")
