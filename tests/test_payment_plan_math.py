# ER-ServiceDesk/tests/test_payment_plan_math.py
"""
Covers PaymentPlanService's real, exact dollar-amount math: creating a
plan (splitting a balance into even installments plus a remainder),
rejecting a second plan on the same invoice, rejecting a non-positive
installment amount, paying exactly as scheduled, overpaying (several
distinct shapes: reduces remaining, covers the next installment
outright, covers it with a partial leftover), underpaying (increases
remaining, or appends a new installment if it's the last one),
completing early when paid to zero, and a specific regression test for
the documented Jan 31 date-extension bug class (incremental
month-by-month math silently loses the original day-of-month once a
shorter month clamps it down).
"""

from tests.factories import make_full_ticket, make_invoice

def _make_invoice_with_total(db, total):
    """Sets a real, known total directly via the DB session, bypassing line-item calculation -- that's a separate concern from the payment-plan math these tests exercise."""
    from decimal import Decimal
    ticket = make_full_ticket(db)
    invoice = make_invoice(db, ticket.id)
    invoice.total = Decimal(str(total))
    db.commit()
    db.refresh(invoice)
    return invoice


def test_payment_plan_create_splits_balance_correctly(client, agent_headers, db):
    """A $250 balance at $100/installment produces two full $100 installments plus a $50 remainder installment -- the last one gets whatever's left, never more than the entered amount."""
    invoice = _make_invoice_with_total(db, "250.00")

    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "100.00", "frequency": "monthly", "start_date": "2026-01-31"},
        headers=agent_headers,
    )
    assert create_resp.status_code == 200, create_resp.text
    plan = create_resp.json()
    installments = plan["installments"]
    assert len(installments) == 3
    assert [i["planned_amount"] for i in installments] == ["100.00", "100.00", "50.00"]


def test_payment_plan_rejects_second_plan_on_same_invoice(client, agent_headers, db):
    invoice = _make_invoice_with_total(db, "100.00")
    first_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "50.00", "frequency": "monthly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    assert first_resp.status_code == 200, first_resp.text

    second_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "25.00", "frequency": "weekly", "start_date": "2026-02-01"},
        headers=agent_headers,
    )
    assert second_resp.status_code == 400


def test_payment_plan_rejects_nonpositive_installment_amount(client, agent_headers, db):
    invoice = _make_invoice_with_total(db, "100.00")
    resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "0.00", "frequency": "monthly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    assert resp.status_code == 400


def test_payment_plan_paying_exactly_as_scheduled_leaves_remaining_amounts_unchanged(client, agent_headers, db):
    """Paying the first installment for exactly its planned amount shouldn't change the remaining installments' amounts -- a sanity check that the rebalancing math is a no-op when there's no actual deviation."""
    invoice = _make_invoice_with_total(db, "300.00")
    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "100.00", "frequency": "monthly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    installments = create_resp.json()["installments"]
    first_id = installments[0]["id"]

    pay_resp = client.post(f"/payment_plans/installments/{first_id}/pay", json={"method": "cash"}, headers=agent_headers)
    assert pay_resp.status_code == 200, pay_resp.text

    plan_resp = client.get(f"/payment_plans/{create_resp.json()['id']}", headers=agent_headers)
    remaining = [i for i in plan_resp.json()["installments"] if i["payment_id"] is None]
    assert len(remaining) == 2
    assert [i["planned_amount"] for i in remaining] == ["100.00", "100.00"]


def test_payment_plan_overpaying_reduces_remaining_installments(client, agent_headers, db):
    """Overpaying one installment reduces what's redistributed across the rest, rather than leaving them at their original planned amount."""
    invoice = _make_invoice_with_total(db, "300.00")
    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "100.00", "frequency": "monthly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    installments = create_resp.json()["installments"]
    first_id = installments[0]["id"]

    pay_resp = client.post(f"/payment_plans/installments/{first_id}/pay", json={"amount": "150.00", "method": "cash"}, headers=agent_headers)
    assert pay_resp.status_code == 200, pay_resp.text

    plan_resp = client.get(f"/payment_plans/{create_resp.json()['id']}", headers=agent_headers)
    remaining = [i for i in plan_resp.json()["installments"] if i["payment_id"] is None]
    assert len(remaining) == 2
    # $300 total - $150 paid = $150 remaining, split evenly across 2 installments
    assert [i["planned_amount"] for i in remaining] == ["75.00", "75.00"]


def test_payment_plan_underpaying_increases_remaining_installments(client, agent_headers, db):
    """Underpaying one installment (not the last) increases what's redistributed across the rest."""
    invoice = _make_invoice_with_total(db, "300.00")
    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "100.00", "frequency": "monthly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    installments = create_resp.json()["installments"]
    first_id = installments[0]["id"]

    pay_resp = client.post(f"/payment_plans/installments/{first_id}/pay", json={"amount": "50.00", "method": "cash"}, headers=agent_headers)
    assert pay_resp.status_code == 200, pay_resp.text

    plan_resp = client.get(f"/payment_plans/{create_resp.json()['id']}", headers=agent_headers)
    remaining = [i for i in plan_resp.json()["installments"] if i["payment_id"] is None]
    assert len(remaining) == 2
    # $300 total - $50 paid = $250 remaining, split evenly across 2 installments
    assert [i["planned_amount"] for i in remaining] == ["125.00", "125.00"]


def test_payment_plan_overpaying_by_a_full_installment_marks_the_next_one_paid(client, agent_headers, db):
    """
    Eddie's own example: a $20/week plan, paying $40 against the first
    installment should mark the next installment paid too (fully
    covered by the extra $20), not just reduce what's owed on it.
    """
    invoice = _make_invoice_with_total(db, "80.00")
    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "20.00", "frequency": "weekly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    installments = create_resp.json()["installments"]
    assert len(installments) == 4
    first_id = installments[0]["id"]
    second_id = installments[1]["id"]

    pay_resp = client.post(f"/payment_plans/installments/{first_id}/pay", json={"amount": "40.00", "method": "cash"}, headers=agent_headers)
    assert pay_resp.status_code == 200, pay_resp.text

    plan_resp = client.get(f"/payment_plans/{create_resp.json()['id']}", headers=agent_headers)
    plan_installments = plan_resp.json()["installments"]

    first = next(i for i in plan_installments if i["id"] == first_id)
    second = next(i for i in plan_installments if i["id"] == second_id)
    assert first["payment_id"] is not None
    assert second["payment_id"] is not None
    assert second["payment_id"] == first["payment_id"]  # one real $40 transaction, not two fabricated $20 ones

    remaining = [i for i in plan_installments if i["payment_id"] is None]
    assert len(remaining) == 2
    assert [i["planned_amount"] for i in remaining] == ["20.00", "20.00"]  # untouched -- no leftover to redistribute


def test_payment_plan_overpaying_partway_into_the_next_installment_covers_it_then_redistributes(client, agent_headers, db):
    """
    A partial overpayment into the next installment -- enough to fully
    cover it, with some left over that's not enough for the one after
    that -- marks the covered one paid, then redistributes only the
    genuine leftover across what's still actually remaining.
    """
    invoice = _make_invoice_with_total(db, "80.00")
    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "20.00", "frequency": "weekly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    installments = create_resp.json()["installments"]
    first_id = installments[0]["id"]
    second_id = installments[1]["id"]

    # $50 paid: $20 covers the first installment, $20 more fully
    # covers the second, $10 left over redistributes across the
    # remaining 2 installments.
    pay_resp = client.post(f"/payment_plans/installments/{first_id}/pay", json={"amount": "50.00", "method": "cash"}, headers=agent_headers)
    assert pay_resp.status_code == 200, pay_resp.text

    plan_resp = client.get(f"/payment_plans/{create_resp.json()['id']}", headers=agent_headers)
    plan_installments = plan_resp.json()["installments"]

    second = next(i for i in plan_installments if i["id"] == second_id)
    assert second["payment_id"] is not None

    remaining = [i for i in plan_installments if i["payment_id"] is None]
    assert len(remaining) == 2
    # $80 total - $50 paid = $30 remaining, split evenly across 2 installments
    assert [i["planned_amount"] for i in remaining] == ["15.00", "15.00"]


def test_payment_plan_overpaying_to_zero_completes_early(client, agent_headers, db):
    """Paying enough to reach a zero remaining balance deletes the leftover installments and marks the plan completed, rather than leaving zero-dollar installments behind."""
    invoice = _make_invoice_with_total(db, "300.00")
    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "100.00", "frequency": "monthly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    installments = create_resp.json()["installments"]
    first_id = installments[0]["id"]

    pay_resp = client.post(f"/payment_plans/installments/{first_id}/pay", json={"amount": "300.00", "method": "cash"}, headers=agent_headers)
    assert pay_resp.status_code == 200, pay_resp.text

    plan_resp = client.get(f"/payment_plans/{create_resp.json()['id']}", headers=agent_headers)
    plan = plan_resp.json()
    assert plan["status"] == "completed"
    remaining = [i for i in plan["installments"] if i["payment_id"] is None]
    assert len(remaining) == 0


def test_payment_plan_underpaying_last_installment_appends_a_new_one(client, agent_headers, db):
    """Underpaying the final installment appends a new installment for what's left, since there's no other installment to redistribute onto."""
    invoice = _make_invoice_with_total(db, "100.00")
    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "100.00", "frequency": "monthly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    installments = create_resp.json()["installments"]
    assert len(installments) == 1
    only_id = installments[0]["id"]

    pay_resp = client.post(f"/payment_plans/installments/{only_id}/pay", json={"amount": "60.00", "method": "cash"}, headers=agent_headers)
    assert pay_resp.status_code == 200, pay_resp.text

    plan_resp = client.get(f"/payment_plans/{create_resp.json()['id']}", headers=agent_headers)
    remaining = [i for i in plan_resp.json()["installments"] if i["payment_id"] is None]
    assert len(remaining) == 1
    assert remaining[0]["planned_amount"] == "40.00"
    assert remaining[0]["sequence_number"] == 2


def test_payment_plan_extend_date_uses_direct_offset_not_incremental(client, agent_headers, db):
    """
    Regression test for the documented Jan 31 date-extension bug class:
    extending an installment to Jan 31 and recalculating a later monthly
    installment must land on Mar 31, not Mar 28 -- incremental month-by-
    month math (Jan 31 -> Feb 28 -> Mar 28) silently loses the original
    day-of-month once a shorter month clamps it down.
    """
    invoice = _make_invoice_with_total(db, "300.00")
    create_resp = client.post(
        "/payment_plans/",
        json={"invoice_id": invoice.id, "installment_amount": "100.00", "frequency": "monthly", "start_date": "2026-01-01"},
        headers=agent_headers,
    )
    installments = create_resp.json()["installments"]
    first_id = installments[0]["id"]
    third_id = installments[2]["id"]

    extend_resp = client.put(f"/payment_plans/installments/{first_id}/extend", json={"new_due_date": "2026-01-31"}, headers=agent_headers)
    assert extend_resp.status_code == 200, extend_resp.text

    plan_resp = client.get(f"/payment_plans/{create_resp.json()['id']}", headers=agent_headers)
    third_installment = next(i for i in plan_resp.json()["installments"] if i["id"] == third_id)
    assert third_installment["due_date"] == "2026-03-31"


