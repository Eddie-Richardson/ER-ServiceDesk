# ER-ServiceDesk/app/schemas/payment.py
# Pydantic schemas for Payment entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning payment records within the ER‑ServiceDesk system.
# They support invoice billing workflows, including cash and
# processor‑based transactions with optional external references.

from datetime import datetime
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class PaymentBase(BaseModel):
    invoice_id: int
    amount: float
    method: str
    transaction_id: str | None = None

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class PaymentCreate(PaymentBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class PaymentUpdate(BaseModel):
    invoice_id: int | None = None
    amount: float | None = None
    method: str | None = None
    transaction_id: str | None = None
    updated_at: datetime | None = None

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class Payment(PaymentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True