# ER-ServiceDesk/tests/test_payment_plan_crud.py
"""
Covers PaymentPlanCRUD.delete() and PaymentPlanInstallmentCRUD.delete().
"""

from app.crud.payment_plan import crud_payment_plan, crud_payment_plan_installment
from tests.factories import make_full_ticket


def test_payment_plan_delete_genuinely_removes_the_record(db):
    ticket = make_full_ticket(db)
    from app.models.invoice import Invoice
    invoice = Invoice(ticket_id=ticket.id, invoice_number=1, total=300)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    plan = crud_payment_plan.create(db, invoice_id=invoice.id, installment_amount=100, frequency="monthly")
    plan_id = plan.id

    crud_payment_plan.delete(db, plan_id)

    assert crud_payment_plan.get(db, plan_id) is None


def test_payment_plan_installment_delete_genuinely_removes_the_record(db):
    ticket = make_full_ticket(db)
    from app.models.invoice import Invoice
    invoice = Invoice(ticket_id=ticket.id, invoice_number=1, total=300)
    db.add(invoice)
    db.commit()
    db.refresh(invoice)

    plan = crud_payment_plan.create(db, invoice_id=invoice.id, installment_amount=100, frequency="monthly")

    from app.models.payment_plan_installment import PaymentPlanInstallment
    from datetime import date
    installment = PaymentPlanInstallment(payment_plan_id=plan.id, sequence_number=1, due_date=date(2026, 1, 1), planned_amount=100)
    db.add(installment)
    db.commit()
    db.refresh(installment)
    installment_id = installment.id

    crud_payment_plan_installment.delete(db, installment_id)

    assert crud_payment_plan_installment.get(db, installment_id) is None
