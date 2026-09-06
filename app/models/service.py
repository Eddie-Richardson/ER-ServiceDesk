# ER-ServiceDesk/app/models/service.py
"""
ORM model for a billable service the shop offers (e.g. "Screen
Replacement", "Diagnostic Fee"), with its current price.

Superuser-managed via Settings -> Billing -> Services. Selected from an
expandable list when building a Quote/Invoice's line items (see
QuoteLineItem/InvoiceLineItem) -- each line item snapshots this
service's price at the moment it's added, so a later price change here
never silently alters an existing quote or invoice.
"""

from sqlalchemy import Column, Integer, String, Numeric, Text, Boolean, DateTime
from datetime import datetime, UTC
from app.db.base import Base


class Service(Base):
    """
    Represents one billable service the shop offers, with its current price.

    Attributes:
        price: Current price for this service. Existing line items
            keep their own snapshotted name and price regardless of
            later changes here -- see QuoteLineItem/InvoiceLineItem.
        is_active: Whether this service currently shows up in the
            "add a line item" picker for new bills. Purely a picker
            convenience (e.g. temporarily or seasonally deactivating
            one) -- NOT a data-integrity requirement, since existing
            line items snapshot their own name/price and stay correct
            regardless of whether this service is later deactivated
            or even deleted entirely.
    """
    __tablename__ = "services"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Numeric, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
