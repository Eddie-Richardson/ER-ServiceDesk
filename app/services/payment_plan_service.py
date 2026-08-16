# ER-ServiceDesk/app/services/payment_plan_service.py
# Service layer for PaymentPlan.
"""
Business logic for a structured installment payment schedule on an
invoice.

Setup takes a per-installment amount and frequency -- the number of
installments and their due dates are worked out from the invoice's
remaining balance, not entered directly. Recording a payment against
an installment (via the existing, already-tested payment_service, so
an invoice's own is_paid logic keeps working unchanged) automatically
rebalances the remaining schedule if the actual amount paid differs
from what was planned: reaching a zero balance completes the plan
early (no leftover zero-dollar installments); overpaying reduces what
remains; underpaying increases it, redistributed evenly across
whatever installments are still outstanding. If the very last
installment is underpaid, a new one is appended rather than leaving a
balance with nowhere to go.
"""

from datetime import timedelta, date
from decimal import Decimal, ROUND_HALF_UP

from dateutil.relativedelta import relativedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.crud.payment_plan import crud_payment_plan, crud_payment_plan_installment
from app.crud.invoice import crud_invoice
from app.crud.payment import crud_payment
from app.schemas.payment_plan import PaymentPlanCreate
from app.schemas.payment import PaymentCreate
from app.services.payment_service import payment_service
from app.services.payment_email_service import payment_email_service
from app.services.audit_log_service import audit_log_service

VALID_FREQUENCIES = ("weekly", "biweekly", "monthly")


class PaymentPlanService:
    """Business logic for setting up and running a structured installment payment plan."""

    def get(self, db: Session, id: int):
        """
        Fetch a single PaymentPlan by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching PaymentPlan instance, or None if not found.
        """
        return crud_payment_plan.get(db, id)

    def get_by_invoice(self, db: Session, invoice_id: int):
        """
        Fetch the payment plan for a given invoice, if any.

        Args:
            db: Active database session.
            invoice_id: The invoice to look up a plan for.

        Returns:
            The matching PaymentPlan instance, or None.
        """
        return crud_payment_plan.get_by_invoice(db, invoice_id)

    def create_plan(self, db: Session, obj_in: PaymentPlanCreate, current_user_id: int):
        """
        Sets up a new payment plan on an invoice -- works out the
        number of installments and their due dates from the invoice's
        remaining balance (total minus any payments already made),
        the entered per-installment amount, and the chosen frequency.
        Installments are the full entered amount except the last,
        which gets whatever remains (never more than the entered
        amount, may be less).

        Args:
            db: Active database session.
            obj_in: The invoice, installment amount, frequency, and
                start date to set the plan up with.
            current_user_id: The user setting up this plan -- recorded
                in the audit trail.

        Returns:
            The newly created PaymentPlan instance, with its installments.

        Raises:
            HTTPException: 404 if the invoice doesn't exist. 400 if
                this invoice already has a payment plan, is already
                fully paid, or the installment amount isn't positive.
        """
        invoice = crud_invoice.get(db, obj_in.invoice_id)
        if not invoice:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

        if crud_payment_plan.get_by_invoice(db, obj_in.invoice_id):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invoice already has a payment plan.")

        if obj_in.installment_amount <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Installment amount must be positive.")

        if obj_in.frequency not in VALID_FREQUENCIES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Frequency must be one of {VALID_FREQUENCIES}.")

        already_paid = sum((p.amount for p in crud_payment.get_by_invoice(db, obj_in.invoice_id)), Decimal("0"))
        remaining_balance = invoice.total - already_paid
        if remaining_balance <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invoice is already fully paid; no payment plan needed.")

        plan = crud_payment_plan.create(db, obj_in.invoice_id, obj_in.installment_amount, obj_in.frequency)

        num_full_installments = int(remaining_balance // obj_in.installment_amount)
        remainder = (remaining_balance - (num_full_installments * obj_in.installment_amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        sequence = 1
        for i in range(num_full_installments):
            due_date = self._date_at_offset(obj_in.start_date, obj_in.frequency, i)
            crud_payment_plan_installment.create(db, plan.id, sequence, due_date, obj_in.installment_amount)
            sequence += 1

        if remainder > 0:
            due_date = self._date_at_offset(obj_in.start_date, obj_in.frequency, num_full_installments)
            crud_payment_plan_installment.create(db, plan.id, sequence, due_date, remainder)

        audit_log_service.log(
            db, "payment_plan_created", "ticket", invoice.ticket_id, user_id=current_user_id,
            details=f"Payment plan created for Invoice #{invoice.id}: ${obj_in.installment_amount}/{obj_in.frequency}",
        )

        return plan

    def record_installment_payment(self, db: Session, installment_id: int, amount: Decimal | None, method: str, current_user_id: int):
        """
        Records a payment against a specific installment -- uses the
        installment's own planned_amount if no amount is given
        (paid exactly as scheduled), or a different amount if the
        customer paid more or less. Automatically rebalances the
        remaining schedule to match.

        Args:
            db: Active database session.
            installment_id: The installment being paid.
            amount: The actual amount paid, or None to use planned_amount.
            method: Payment method (e.g. "cash", "credit_card").
            current_user_id: The user recording this payment -- recorded
                in the audit trail.

        Returns:
            The updated PaymentPlanInstallment instance.

        Raises:
            HTTPException: 404 if the installment doesn't exist. 400
                if it's already been paid.
        """
        installment = crud_payment_plan_installment.get(db, installment_id)
        if not installment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Installment not found")
        if installment.payment_id is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This installment has already been paid.")

        plan = crud_payment_plan.get(db, installment.payment_plan_id)
        invoice = crud_invoice.get(db, plan.invoice_id)

        actual_amount = amount if amount is not None else installment.planned_amount

        new_payment = payment_service.create(
            db, PaymentCreate(invoice_id=invoice.id, amount=actual_amount, method=method), current_user_id,
        )

        installment.payment_id = new_payment.id
        db.commit()

        total_paid = sum((p.amount for p in crud_payment.get_by_invoice(db, invoice.id)), Decimal("0"))
        remaining_balance = invoice.total - total_paid

        remaining_installments = [
            i for i in crud_payment_plan_installment.get_by_plan(db, plan.id)
            if i.payment_id is None
        ]

        if remaining_balance <= 0:
            for remaining in remaining_installments:
                crud_payment_plan_installment.delete(db, remaining.id)
            plan.status = "completed"
            db.commit()
        elif remaining_installments:
            self._redistribute(db, remaining_installments, remaining_balance)
        else:
            next_date = self._date_at_offset(installment.due_date, plan.frequency, 1)
            crud_payment_plan_installment.create(db, plan.id, installment.sequence_number + 1, next_date, remaining_balance)

        audit_log_service.log(
            db, "payment_plan_installment_paid", "ticket", invoice.ticket_id, user_id=current_user_id,
            details=f"Paid ${actual_amount} on installment #{installment.sequence_number} of Payment Plan #{plan.id}",
        )

        # Sent here, not from payment_service.create() or the /payments/
        # route, deliberately -- everything above (installment linking,
        # redistribution or plan completion) must be fully settled
        # first, or the receipt's "next payment due" lookup would still
        # see the installment just paid as unpaid and report the wrong
        # date. Never raises, so a receipt-email problem can never
        # undo or block the payment already, genuinely recorded above.
        payment_email_service.send_receipt(db, new_payment)

        db.refresh(installment)
        return installment

    def extend_installment_date(self, db: Session, installment_id: int, new_due_date: date, current_user_id: int):
        """
        Manually pushes back a specific installment's due date, then
        recalculates every later, still-unpaid installment's date
        from this new date forward, using the plan's own frequency.

        Args:
            db: Active database session.
            installment_id: The installment whose date is changing.
            new_due_date: The new due date for this installment.
            current_user_id: The user making this change -- recorded
                in the audit trail.

        Returns:
            The updated PaymentPlanInstallment instance.

        Raises:
            HTTPException: 404 if the installment doesn't exist. 400
                if it's already been paid.
        """
        installment = crud_payment_plan_installment.get(db, installment_id)
        if not installment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Installment not found")
        if installment.payment_id is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Can't change the date of an already-paid installment.")

        plan = crud_payment_plan.get(db, installment.payment_plan_id)
        invoice = crud_invoice.get(db, plan.invoice_id)

        installment.due_date = new_due_date
        db.commit()

        later_installments = [
            i for i in crud_payment_plan_installment.get_by_plan(db, plan.id)
            if i.sequence_number > installment.sequence_number and i.payment_id is None
        ]

        for offset, later in enumerate(later_installments, start=1):
            later.due_date = self._date_at_offset(new_due_date, plan.frequency, offset)
        db.commit()

        audit_log_service.log(
            db, "payment_plan_installment_date_extended", "ticket", invoice.ticket_id, user_id=current_user_id,
            details=f"Extended installment #{installment.sequence_number} of Payment Plan #{plan.id} to {new_due_date}",
        )

        db.refresh(installment)
        return installment

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------
    def _date_at_offset(self, base_date: date, frequency: str, offset: int) -> date:
        """
        Args:
            base_date: The date to calculate from.
            frequency: "weekly", "biweekly", or "monthly".
            offset: How many periods after base_date.

        Returns:
            base_date advanced by offset periods, computed directly
            from base_date every time -- never incrementally from a
            previous result. This matters specifically for monthly:
            incrementally adding one month at a time loses the
            original day-of-month once a shorter month clamps it down
            (Jan 31 + 1 month = Feb 28, but Feb 28 + 1 month = Mar 28,
            not the Mar 31 a real calendar-correct schedule should
            land on). Computing every offset directly from base_date
            avoids that entirely.
        """
        if frequency == "weekly":
            return base_date + timedelta(weeks=offset)
        if frequency == "biweekly":
            return base_date + timedelta(weeks=2 * offset)
        if frequency == "monthly":
            return base_date + relativedelta(months=offset)
        raise ValueError(f"Unknown frequency: {frequency}")

    def _redistribute(self, db: Session, installments: list, total_remaining: Decimal):
        """
        Evenly splits total_remaining across the given installments,
        updating their planned_amount. Any leftover cent from rounding
        goes to the last installment, so the sum always matches
        total_remaining exactly rather than drifting from repeated
        rounding.

        Args:
            db: Active database session.
            installments: The still-unpaid installments to redistribute
                across.
            total_remaining: The new total to split between them.
        """
        count = len(installments)
        base_amount = (total_remaining / count).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        running_total = Decimal("0")
        for i, installment in enumerate(installments):
            if i == count - 1:
                amount = total_remaining - running_total
            else:
                amount = base_amount
                running_total += amount
            installment.planned_amount = amount

        db.commit()

payment_plan_service = PaymentPlanService()
