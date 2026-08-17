# ER-ServiceDesk/app/models/quote.py
# ORM model for an estimated price for ticket-related work, pending customer approval
"""
ORM model for an estimated price for ticket-related work, pending customer approval.
"""

from sqlalchemy import Column, Integer, Numeric, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base

class Quote(Base):
    """
    Represents a cost estimate given to a customer before work is approved.

    Attributes:
        ticket_id: The ticket this quote is for.
        subtotal: Sum of every line item (quantity x unit_price),
            before discount or tax. Computed and stored (not derived
            live), so a quote's own totals stay accurate even if a
            line item's underlying Service is later changed.
        discount_name: The discount's name at the moment it was
            applied -- a snapshot, same reasoning as line items'
            service_name. Keeps this quote fully self-contained and
            correctly renderable even if the Discount is later
            renamed or deleted entirely.
        discount_amount: The actual dollar amount the discount took
            off, snapshotted at the moment it was applied -- a later
            change to Discount.percentage never alters this quote's
            own numbers.
        tax_rate_name: The tax rate's name at the moment it was
            applied -- a snapshot, same reasoning as discount_name.
        tax_amount: The actual dollar amount of tax, calculated on
            (subtotal - discount_amount) and snapshotted the same way.
        total: subtotal - discount_amount + tax_amount. The final
            quoted price.
        converted_invoice_id: The Invoice this quote became, once
            approved and converted -- null until that happens. See
            quote_service.convert_to_invoice().
        quote_sent_at: Timestamp this quote was last emailed to the
            customer, or None if never sent. Email-only, same design
            as Ticket.waiver_sent_at -- the customer's "I APPROVE"
            reply, if any, comes back as a normal Note on the ticket
            through the existing inbound-email system, not tracked
            here. This field only tracks whether the quote itself went
            out, not whether it was answered.
    """
    __tablename__ = "quotes"
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
    quote_sent_at = Column(DateTime(timezone=True), nullable=True)
    # Quote <-> Invoice is a genuine mutual reference (this points at
    # invoices.id, and Invoice.source_quote_id points back at
    # quotes.id) -- name= and use_alter=True are required so
    # SQLAlchemy's own metadata can resolve the cycle (e.g. sorting
    # tables for a test-teardown delete). name= matches the constraint
    # name Postgres auto-generates for this column.
    converted_invoice_id = Column(
        Integer,
        ForeignKey("invoices.id", name="quotes_converted_invoice_id_fkey", use_alter=True),
        nullable=True,
    )

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)

    ticket = relationship("Ticket")
    discount = relationship("Discount")
    tax_rate = relationship("TaxRate")
    # cascade="all, delete-orphan": inert in practice -- Quote
    # records are not deletable at any layer (no route, no service
    # method, no CRUD method), so this never actually fires.
    line_items = relationship("QuoteLineItem", back_populates="quote", cascade="all, delete-orphan")
    # foreign_keys= disambiguates the circular reference with Invoice
    # -- see the comment on converted_invoice_id above for why.
    converted_invoice = relationship("Invoice", foreign_keys=[converted_invoice_id])
