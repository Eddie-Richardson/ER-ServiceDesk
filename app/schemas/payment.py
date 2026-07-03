# ER-ServiceDesk/app/schemas/payment.py
# Pydantic schemas for Payment entities used to validate and structure a payment applied against an invoice
"""
Pydantic schemas for Payment entities used to validate and structure a payment applied against an invoice.
"""

from datetime import datetime
from pydantic import BaseModel

class PaymentBase(BaseModel):
    """Shared fields for Payment across create/read/update."""
    invoice_id: int
    amount: float
    method: str
    transaction_id: str | None = None

class PaymentCreate(PaymentBase):
    """Schema for creating a new Payment record (client -> server)."""
    pass

class PaymentUpdate(BaseModel):
    """Schema for partially updating an existing Payment record. All fields optional."""
    invoice_id: int | None = None
    amount: float | None = None
    method: str | None = None
    transaction_id: str | None = None
    updated_at: datetime | None = None

class Payment(PaymentBase):
    """Schema returned to the client for a Payment record (server -> client)."""
    id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        orm_mode = True
