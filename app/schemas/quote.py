# ER-ServiceDesk/app/schemas/quote.py
"""
Request/response schemas for a cost estimate given to a customer
before work is approved.

Creation is deliberately simple (just ticket_id + optional discount/tax
+ details) -- line items get added afterward, one at a time, via their
own dedicated endpoint (see schemas/quote_line_item.py), the same
expandable-list pattern as TicketPart. subtotal/discount_amount/
tax_amount/total are never client-supplied; they're computed
server-side (see quote_service.py) whenever a line item or the
discount/tax selection changes.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from app.schemas.quote_line_item import QuoteLineItem as QuoteLineItemSchema

class QuoteBase(BaseModel):
    """Shared fields for Quote across create/read/update."""
    ticket_id: int
    discount_id: int | None = None
    tax_rate_id: int | None = None
    details: str | None = None

class QuoteCreate(QuoteBase):
    """Schema for creating a new Quote record (client -> server). Starts with zero line items."""
    pass

class QuoteUpdate(BaseModel):
    """Schema for partially updating an existing Quote record. All fields optional. Changing discount_id/tax_rate_id triggers a totals recalculation."""
    discount_id: int | None = None
    tax_rate_id: int | None = None
    details: str | None = None

class Quote(QuoteBase):
    """Schema returned to the client for a Quote record (server -> client)."""
    id: int
    quote_number: int
    subtotal: Decimal
    discount_name: str | None = None
    discount_amount: Decimal
    tax_rate_name: str | None = None
    tax_amount: Decimal
    total: Decimal
    converted_invoice_id: int | None = None
    converted_invoice_number: int | None = None
    quote_sent_at: datetime | None = None
    line_items: list[QuoteLineItemSchema] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
