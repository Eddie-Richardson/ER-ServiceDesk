# ER-ServiceDesk/app/models/discount.py
# ORM model for a named discount category
"""
ORM model for a named discount category (e.g. "Teacher", "Military",
"Family", "Employee"), with its percentage off.

Superuser-managed via Settings -> Billing -> Discounts. Optionally
applied to a Quote/Invoice's total (see Quote.discount_id/
Invoice.discount_id) -- one discount per quote/invoice, applied to the
whole total rather than per line item.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime
from datetime import datetime, UTC
from app.db.base import Base


class Discount(Base):
    """
    Represents one named discount category and its percentage off.

    Attributes:
        id: Primary key.
        name: The discount's display name, e.g. "Teacher".
        percentage: How much this discount takes off, as a percentage
            (e.g. 10 for 10% off), applied to a quote/invoice's
            pre-tax total.
        is_active: Whether this discount currently shows up as an
            option for new bills. Purely a picker convenience, same
            reasoning as Service.is_active -- existing quotes/invoices
            snapshot the discount's own name and dollar amount, so
            deactivating (or even deleting) this later never affects
            anything already billed.
        created_at: Timestamp the record was created.
        updated_at: Timestamp the record was last updated.
    """
    __tablename__ = "discounts"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    percentage = Column(Numeric, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
