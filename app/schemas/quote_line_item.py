# ER-ServiceDesk/app/schemas/quote_line_item.py
# Pydantic schemas for QuoteLineItem entities
"""
Request/response schemas for a single service line on a quote.
"""

from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class QuoteLineItemCreate(BaseModel):
    """Schema for adding a new line item to a quote (client -> server). unit_price is never client-supplied -- it's snapshotted server-side from the Service's current price at the moment of creation."""
    quote_id: int
    service_id: int
    quantity: int = 1

class QuoteLineItemUpdate(BaseModel):
    """Schema for partially updating an existing line item. Only quantity is editable -- changing which service a line item represents is unusual in practice; remove it and add a new one instead."""
    quantity: int | None = None

class QuoteLineItem(BaseModel):
    """Schema returned to the client for a QuoteLineItem record (server -> client)."""
    id: int
    quote_id: int
    service_id: int | None = None
    service_name: str
    quantity: int
    unit_price: Decimal
    model_config = ConfigDict(from_attributes=True)
