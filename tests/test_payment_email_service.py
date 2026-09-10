# ER-ServiceDesk/tests/test_payment_email_service.py
"""
Covers PaymentEmailService.send_receipt() -- the three genuinely
distinct receipt shapes it chooses automatically based on real state
(paid in full, first payment on a plan showing the full schedule, a
later/partial payment showing just the remaining balance), and the
one property that matters most here: a send failure is logged and
swallowed, never raised -- a real, already-recorded payment must never
be undone or blocked by an email problem.
"""

from datetime import date

from app.services.payment_email_service import payment_email_service
from app.models.payment import Payment
from app.models.payment_plan import PaymentPlan
from app.models.payment_plan_installment import PaymentPlanInstallment
from tests.factories import make_full_ticket, make_invoice


def _make_payment(db, invoice_id, amount):
    payment = Payment(invoice_id=invoice_id, amount=amount, method="cash")
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


def test_a_payment_that_pays_off_the_invoice_gets_the_paid_in_full_shape(db, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "app.services.payment_email_service.send_email",
        lambda db, to_address, subject, body: captured.update(body=body),
    )
    ticket = make_full_ticket(db)
    invoice = make_invoice(db, ticket.id)
    invoice.total = 100
    db.commit()
    payment = _make_payment(db, invoice.id, 100)

    payment_email_service.send_receipt(db, payment)

    assert "paid in full" in captured["body"]
    assert "Remaining balance" not in captured["body"]


def test_a_partial_payment_with_no_plan_shows_the_remaining_balance(db, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "app.services.payment_email_service.send_email",
        lambda db, to_address, subject, body: captured.update(body=body),
    )
    ticket = make_full_ticket(db)
    invoice = make_invoice(db, ticket.id)
    invoice.total = 100
    db.commit()
    payment = _make_payment(db, invoice.id, 40)

    payment_email_service.send_receipt(db, payment)

    assert "Remaining balance: $60" in captured["body"]
    assert "paid in full" not in captured["body"]
    assert "Next payment due" not in captured["body"]


def test_the_first_payment_on_a_new_plan_shows_the_full_schedule(db, monkeypatch):
    """A real, non-obvious property: the plan's first payment shows every installment, not just the next due date -- confirming the plan itself was set up correctly."""
    captured = {}
    monkeypatch.setattr(
        "app.services.payment_email_service.send_email",
        lambda db, to_address, subject, body: captured.update(body=body),
    )
    ticket = make_full_ticket(db)
    invoice = make_invoice(db, ticket.id)
    invoice.total = 300
    db.commit()

    plan = PaymentPlan(invoice_id=invoice.id, installment_amount=100, frequency="monthly")
    db.add(plan)
    db.commit()
    db.refresh(plan)

    payment = _make_payment(db, invoice.id, 100)

    installment_1 = PaymentPlanInstallment(payment_plan_id=plan.id, sequence_number=1, due_date=date(2026, 1, 1), planned_amount=100, payment_id=payment.id)
    installment_2 = PaymentPlanInstallment(payment_plan_id=plan.id, sequence_number=2, due_date=date(2026, 2, 1), planned_amount=100)
    installment_3 = PaymentPlanInstallment(payment_plan_id=plan.id, sequence_number=3, due_date=date(2026, 3, 1), planned_amount=100)
    db.add_all([installment_1, installment_2, installment_3])
    db.commit()

    payment_email_service.send_receipt(db, payment)

    assert "payment plan has been set up as follows" in captured["body"]
    assert "Installment 1: $100 due 2026-01-01 [PAID]" in captured["body"]
    assert "Installment 2: $100 due 2026-02-01" in captured["body"]
    assert "[PAID]" not in captured["body"].split("Installment 2")[1].split("Installment 3")[0]


def test_a_later_installment_on_an_existing_plan_shows_only_the_next_due_date(db, monkeypatch):
    """The second (or later) payment on an already-set-up plan is NOT treated as the first -- no full schedule dump, just the plain next-due-date line."""
    captured = {}
    monkeypatch.setattr(
        "app.services.payment_email_service.send_email",
        lambda db, to_address, subject, body: captured.update(body=body),
    )
    ticket = make_full_ticket(db)
    invoice = make_invoice(db, ticket.id)
    invoice.total = 300
    db.commit()

    plan = PaymentPlan(invoice_id=invoice.id, installment_amount=100, frequency="monthly")
    db.add(plan)
    db.commit()
    db.refresh(plan)

    first_payment = _make_payment(db, invoice.id, 100)
    installment_1 = PaymentPlanInstallment(payment_plan_id=plan.id, sequence_number=1, due_date=date(2026, 1, 1), planned_amount=100, payment_id=first_payment.id)
    db.add(installment_1)
    db.commit()

    second_payment = _make_payment(db, invoice.id, 100)
    installment_2 = PaymentPlanInstallment(payment_plan_id=plan.id, sequence_number=2, due_date=date(2026, 2, 1), planned_amount=100, payment_id=second_payment.id)
    installment_3 = PaymentPlanInstallment(payment_plan_id=plan.id, sequence_number=3, due_date=date(2026, 3, 1), planned_amount=100)
    db.add_all([installment_2, installment_3])
    db.commit()

    payment_email_service.send_receipt(db, second_payment)

    assert "payment plan has been set up as follows" not in captured["body"]
    assert "Next payment due: 2026-03-01" in captured["body"]


def test_a_real_send_failure_is_swallowed_not_raised(db, monkeypatch):
    """The core, deliberate property: the payment already happened -- an email problem must never surface as an exception to the caller."""
    monkeypatch.setattr(
        "app.services.payment_email_service.send_email",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("SMTP is down")),
    )
    ticket = make_full_ticket(db)
    invoice = make_invoice(db, ticket.id)
    invoice.total = 100
    db.commit()
    payment = _make_payment(db, invoice.id, 100)

    payment_email_service.send_receipt(db, payment)  # must not raise


def test_a_missing_customer_email_is_logged_and_swallowed_not_raised(db, monkeypatch):
    ticket = make_full_ticket(db)
    ticket.customer.email = ""
    db.commit()
    invoice = make_invoice(db, ticket.id)
    invoice.total = 100
    db.commit()
    payment = _make_payment(db, invoice.id, 100)

    payment_email_service.send_receipt(db, payment)  # must not raise
