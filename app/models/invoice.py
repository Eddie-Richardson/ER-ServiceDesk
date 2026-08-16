# ER-ServiceDesk/app/models/invoice.py
# ORM model for a bill generated for work performed on a ticket
"""
ORM model for a bill generated for work performed on a ticket.
"""

from sqlalchemy import Column, Integer, Numeric, String, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base

class Invoice(Base):
    """
    Represents a billing record tied to a ticket, tracking amount owed and payment status.

    Attributes:
        id: Primary key.
        ticket_id: The ticket this invoice bills for.
        subtotal: Sum of every line item (quantity x unit_price),
            before discount or tax. Computed and stored, not derived
            live -- see Quote.subtotal for the same reasoning.
        discount_id: The discount applied, if any.
        discount_name: The discount's name at the moment it was
            applied -- a snapshot, same reasoning as line items'
            service_name.
        discount_amount: The actual dollar amount the discount took
            off, snapshotted at the moment it was applied.
        tax_rate_id: The tax rate applied, if any.
        tax_rate_name: The tax rate's name at the moment it was
            applied -- a snapshot.
        tax_amount: The actual dollar amount of tax, calculated on
            (subtotal - discount_amount) and snapshotted the same way.
        total: subtotal - discount_amount + tax_amount. The final
            amount owed.
        details: Optional free-text notes about the invoice.
        is_paid: Whether the invoice has been fully paid.
        source_quote_id: The Quote this invoice was converted from, if
            any -- null for an invoice created directly, not via
            quote conversion.
        invoice_sent_at: Timestamp this invoice was last emailed to
            the customer, or None if never sent. Email-only, same
            design as Ticket.waiver_sent_at / Quote.quote_sent_at.
            Sendable even after is_paid is true -- re-sending a paid
            invoice serves as a receipt, not blocked.
        created_at: Timestamp the record was created.
        updated_at: Timestamp the record was last updated.
    """
    __tablename__ = "invoices"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)

    subtotal = Column(Numeric, nullable=False, default=0)
    discount_id = Column(Integer, ForeignKey("discounts.id", ondelete="SET NULL"), nullable=True)
    discount_name = Column(String, nullable=True)
    discount_amount = Column(Numeric, nullable=False, default=0)
    tax_rate_id = Column(Integer, ForeignKey("tax_rates.id", ondelete="SET NULL"), nullable=True)
    tax_rate_name = Column(String, nullable=True)
    tax_amount = Column(Numeric, nullable=False, default=0)
    total = Column(Numeric, nullable=False, default=0)

    details = Column(Text, nullable=True)
    is_paid = Column(Boolean, default=False)
    source_quote_id = Column(Integer, ForeignKey("quotes.id"), nullable=True)
    invoice_sent_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    ticket = relationship("Ticket")
    discount = relationship("Discount")
    tax_rate = relationship("TaxRate")
    payments = relationship("Payment", back_populates="invoice")
    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")
    source_quote = relationship("Quote", foreign_keys=[source_quote_id])
