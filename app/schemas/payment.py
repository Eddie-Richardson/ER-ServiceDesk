# ER-ServiceDesk/app/schemas/payment.py
"""
Request/response schemas for a payment applied against an invoice.
"""

from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class PaymentBase(BaseModel):
    """Shared fields for Payment across create/read/update."""
    invoice_id: int
    amount: Decimal
    method: str
    transaction_id: str | None = None

class PaymentCreate(PaymentBase):
    """Schema for creating a new Payment record (client -> server)."""
    pass

class PaymentUpdate(BaseModel):
    """Schema for partially updating an existing Payment record. All fields optional."""
    amount: Decimal | None = None
    method: str | None = None
    transaction_id: str | None = None

class Payment(PaymentBase):
    """Schema returned to the client for a Payment record (server -> client)."""
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
