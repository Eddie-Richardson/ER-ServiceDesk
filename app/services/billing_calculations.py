# ER-ServiceDesk/app/services/billing_calculations.py
"""
Shared billing math used identically by quote_service.py and
invoice_service.py -- kept in one place rather than duplicated across
both, since the calculation itself (subtotal -> discount -> tax ->
total) doesn't differ between the two.

Tax is calculated on the amount AFTER discount is applied (the more
common convention -- a discount reduces the taxable amount). All
money math uses Decimal throughout and rounds to 2 decimal places at
the end, never float, to avoid real precision issues with money.
"""

from decimal import Decimal, ROUND_HALF_UP


def calculate_totals(
    line_items: list,
    discount_percentage: Decimal | None,
    tax_percentage: Decimal | None,
) -> dict:
    """
    Computes subtotal, discount_amount, tax_amount, and total from a
    set of line items and optional discount/tax percentages.

    Args:
        line_items: Objects with .quantity and .unit_price attributes
            (a QuoteLineItem or InvoiceLineItem list).
        discount_percentage: The discount's percentage (e.g. Decimal("10")
            for 10% off), or None if no discount applied.
        tax_percentage: The tax rate's percentage (e.g. Decimal("8.25")),
            or None if no tax applied. Calculated on the amount AFTER
            discount, not the raw subtotal.

    Returns:
        {"subtotal": Decimal, "discount_amount": Decimal,
         "tax_amount": Decimal, "total": Decimal}, each rounded to 2
        decimal places.
    """
    subtotal = sum((Decimal(item.quantity) * Decimal(item.unit_price) for item in line_items), Decimal("0"))

    discount_amount = Decimal("0")
    if discount_percentage is not None:
        discount_amount = subtotal * (Decimal(discount_percentage) / Decimal("100"))

    taxable_amount = subtotal - discount_amount

    tax_amount = Decimal("0")
    if tax_percentage is not None:
        tax_amount = taxable_amount * (Decimal(tax_percentage) / Decimal("100"))

    total = taxable_amount + tax_amount

    cents = Decimal("0.01")
    return {
        "subtotal": subtotal.quantize(cents, rounding=ROUND_HALF_UP),
        "discount_amount": discount_amount.quantize(cents, rounding=ROUND_HALF_UP),
        "tax_amount": tax_amount.quantize(cents, rounding=ROUND_HALF_UP),
        "total": total.quantize(cents, rounding=ROUND_HALF_UP),
    }
