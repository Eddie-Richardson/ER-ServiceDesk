# ER-ServiceDesk/app/schemas/invoice_line_item.py
# Pydantic schemas for InvoiceLineItem entities
"""
Request/response schemas for a single service line on an invoice.
"""

from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class InvoiceLineItemCreate(BaseModel):
    """Schema for adding a new line item to an invoice (client -> server). unit_price is never client-supplied -- it's snapshotted server-side from the Service's current price at the moment of creation."""
    invoice_id: int
    service_id: int
    quantity: int = 1

class InvoiceLineItemUpdate(BaseModel):
    """Schema for partially updating an existing line item. Only quantity is editable, same reasoning as QuoteLineItemUpdate."""
    quantity: int | None = None

class InvoiceLineItem(BaseModel):
    """Schema returned to the client for an InvoiceLineItem record (server -> client)."""
    id: int
    invoice_id: int
    service_id: int | None = None
    service_name: str
    quantity: int
    unit_price: Decimal
    model_config = ConfigDict(from_attributes=True)
