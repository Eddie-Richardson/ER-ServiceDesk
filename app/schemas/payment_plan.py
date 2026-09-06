# ER-ServiceDesk/app/schemas/payment_plan.py
"""
Request/response schemas for a structured installment payment schedule.
"""

from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel, ConfigDict


class PaymentPlanCreate(BaseModel):
    """
    Schema for setting up a new payment plan on an invoice.

    installment_amount and frequency are what's actually entered --
    the number of installments and their due dates are worked out
    server-side from these, not supplied directly. See
    payment_plan_service.create_plan().
    """
    invoice_id: int
    installment_amount: Decimal
    frequency: str  # "weekly", "biweekly", or "monthly"
    start_date: date


class PaymentPlanInstallment(BaseModel):
    """Schema returned to the client for a single installment (server -> client)."""
    id: int
    payment_plan_id: int
    sequence_number: int
    due_date: date
    planned_amount: Decimal
    payment_id: int | None = None
    model_config = ConfigDict(from_attributes=True)


class PaymentPlan(BaseModel):
    """Schema returned to the client for a PaymentPlan record (server -> client)."""
    id: int
    invoice_id: int
    installment_amount: Decimal
    frequency: str
    status: str
    created_at: datetime
    updated_at: datetime
    installments: list[PaymentPlanInstallment] = []
    model_config = ConfigDict(from_attributes=True)


class RecordInstallmentPayment(BaseModel):
    """
    Schema for recording a payment against a specific installment.

    amount is optional -- if omitted, the installment's own
    planned_amount is used (the common "paid exactly as scheduled"
    case). Supplying a different amount is what triggers rebalancing
    the remaining installments.
    """
    amount: Decimal | None = None
    method: str


class ExtendInstallmentDate(BaseModel):
    """Schema for manually pushing back a specific installment's due date, recalculating every later installment's date from it."""
    new_due_date: date
