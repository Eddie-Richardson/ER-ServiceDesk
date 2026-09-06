# ER-ServiceDesk/app/routes/payment_plans.py
"""
REST endpoints for a structured installment payment schedule on an
invoice.

Gated on billing.manage, same reasoning as routes/quotes.py.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_permission, get_current_user
from app.models.user import User
from app.services.payment_plan_service import payment_plan_service
from app.schemas.payment_plan import (
    PaymentPlan, PaymentPlanCreate, PaymentPlanInstallment,
    RecordInstallmentPayment, ExtendInstallmentDate,
)

router = APIRouter(prefix="/payment_plans", tags=["payment_plans"], dependencies=[Depends(require_permission("billing.manage"))])


@router.get("/{id}", response_model=PaymentPlan)
def get_payment_plan(id: int, db: Session = Depends(get_db)):
    """Fetch a single PaymentPlan by ID, including its installments."""
    return payment_plan_service.get(db, id)


@router.get("/by-invoice/{invoice_id}", response_model=PaymentPlan | None)
def get_payment_plan_by_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Fetch the payment plan for a given invoice, if any."""
    return payment_plan_service.get_by_invoice(db, invoice_id)


@router.post("/", response_model=PaymentPlan)
def create_payment_plan(
    obj_in: PaymentPlanCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sets up a new payment plan -- works out the number of installments
    and their due dates from the invoice's remaining balance, the
    entered per-installment amount, and the chosen frequency.
    """
    return payment_plan_service.create_plan(db, obj_in, current_user.id)


@router.post("/installments/{installment_id}/pay", response_model=PaymentPlanInstallment)
def record_installment_payment(
    installment_id: int,
    obj_in: RecordInstallmentPayment,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Records a payment against a specific installment -- uses the
    installment's own planned amount if none is given, or a different
    amount if the customer paid more or less. Automatically
    rebalances the remaining schedule to match.
    """
    return payment_plan_service.record_installment_payment(db, installment_id, obj_in.amount, obj_in.method, current_user.id)


@router.put("/installments/{installment_id}/extend", response_model=PaymentPlanInstallment)
def extend_installment_date(
    installment_id: int,
    obj_in: ExtendInstallmentDate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manually pushes back a specific installment's due date, recalculating every later installment's date from it."""
    return payment_plan_service.extend_installment_date(db, installment_id, obj_in.new_due_date, current_user.id)
