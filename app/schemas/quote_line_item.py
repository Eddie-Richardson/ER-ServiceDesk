# ER-ServiceDesk/app/schemas/quote_line_item.py
# Pydantic schemas for QuoteLineItem entities
"""
Request/response schemas for a single line on a quote -- either a
service or a real inventory part.
"""

from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class QuoteLineItemCreate(BaseModel):
    """
    Schema for adding a new line item to a quote (client -> server).
    Exactly one of service_id/part_id must be set -- enforced at the
    service layer, not here. unit_price is never client-supplied --
    it's snapshotted server-side from the Service's current price or
    the Part's current selling_price at the moment of creation.
    """
    quote_id: int
    service_id: int | None = None
    part_id: int | None = None
    quantity: int = 1

class QuoteLineItemUpdate(BaseModel):
    """Schema for partially updating an existing line item. Only quantity is editable -- changing which service/part a line item represents is unusual in practice; remove it and add a new one instead."""
    quantity: int | None = None

class QuoteLineItem(BaseModel):
    """Schema returned to the client for a QuoteLineItem record (server -> client)."""
    id: int
    quote_id: int
    service_id: int | None = None
    service_name: str | None = None
    part_id: int | None = None
    part_name: str | None = None
    quantity: int
    unit_price: Decimal
    model_config = ConfigDict(from_attributes=True)
