# ER-ServiceDesk/app/models/tax_rate.py
# ORM model for a named tax rate
"""
ORM model for a named tax rate (e.g. "Standard Sales Tax"), with its
percentage.

Superuser-managed via Settings -> Billing -> Tax Rates. Optionally
applied to a Quote/Invoice's total (see Quote.tax_rate_id/
Invoice.tax_rate_id), calculated on the amount AFTER any discount is
applied.
"""

from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime
from datetime import datetime, UTC
from app.db.base import Base


class TaxRate(Base):
    """
    Represents one named tax rate and its percentage.

    Attributes:
        percentage: The tax rate as a percentage (e.g. 8.25 for
            8.25%), applied to a quote/invoice's total after any
            discount.
        is_active: Whether this tax rate currently shows up as an
            option for new bills. Purely a picker convenience, same
            reasoning as Service.is_active -- existing quotes/invoices
            snapshot the tax rate's own name and dollar amount, so
            deactivating (or even deleting) this later never affects
            anything already billed.
    """
    __tablename__ = "tax_rates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    percentage = Column(Numeric, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
