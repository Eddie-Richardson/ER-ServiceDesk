# ER-ServiceDesk/app/schemas/invoice_line_item.py
# Pydantic schemas for InvoiceLineItem entities
"""
Request/response schemas for a single line on an invoice -- either a
service or a real inventory part.
"""

from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class InvoiceLineItemCreate(BaseModel):
    """
    Schema for adding a new line item to an invoice (client -> server).
    Exactly one of service_id/part_id must be set -- enforced at the
    service layer, not here. unit_price is never client-supplied --
    it's snapshotted server-side from the Service's current price or
    the Part's current selling_price at the moment of creation. Adding
    a part line item is what triggers real inventory deduction -- see
    invoice_service.py's add_line_item().
    """
    invoice_id: int
    service_id: int | None = None
    part_id: int | None = None
    quantity: int = 1

class InvoiceLineItemUpdate(BaseModel):
    """Schema for partially updating an existing line item. Only quantity is editable, same reasoning as QuoteLineItemUpdate."""
    quantity: int | None = None

class InvoiceLineItem(BaseModel):
    """Schema returned to the client for an InvoiceLineItem record (server -> client)."""
    id: int
    invoice_id: int
    service_id: int | None = None
    service_name: str | None = None
    part_id: int | None = None
    part_name: str | None = None
    quantity: int
    unit_price: Decimal
    model_config = ConfigDict(from_attributes=True)
