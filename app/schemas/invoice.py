# ER-ServiceDesk/app/schemas/invoice.py
"""
Request/response schemas for a bill generated for work performed on a
ticket. Same shape and reasoning as Quote -- see schemas/quote.py.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict
from app.schemas.invoice_line_item import InvoiceLineItem as InvoiceLineItemSchema

class InvoiceBase(BaseModel):
    """Shared fields for Invoice across create/read/update."""
    ticket_id: int
    discount_id: int | None = None
    tax_rate_id: int | None = None
    details: str | None = None

class InvoiceCreate(InvoiceBase):
    """Schema for creating a new Invoice record directly (client -> server). Starts with zero line items. Not used for quote-to-invoice conversion -- see quote_service.convert_to_invoice() for that path."""
    pass

class InvoiceUpdate(BaseModel):
    """Schema for partially updating an existing Invoice record. All fields optional. Changing discount_id/tax_rate_id triggers a totals recalculation."""
    discount_id: int | None = None
    tax_rate_id: int | None = None
    details: str | None = None
    is_paid: bool | None = None

class Invoice(InvoiceBase):
    """Schema returned to the client for an Invoice record (server -> client)."""
    id: int
    invoice_number: int
    subtotal: Decimal
    discount_name: str | None = None
    discount_amount: Decimal
    tax_rate_name: str | None = None
    tax_amount: Decimal
    total: Decimal
    is_paid: bool
    source_quote_id: int | None = None
    invoice_sent_at: datetime | None = None
    line_items: list[InvoiceLineItemSchema] = []
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
