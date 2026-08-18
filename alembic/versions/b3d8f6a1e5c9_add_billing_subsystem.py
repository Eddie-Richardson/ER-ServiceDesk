# ER-ServiceDesk/alembic/versions/b3d8f6a1e5c9_add_billing_subsystem.py
"""add billing subsystem: services, discounts, tax rates, line items

Revision ID: b3d8f6a1e5c9
Revises: a7f3e91c4d28
Create Date: 2026-08-11

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b3d8f6a1e5c9"
down_revision = "a7f3e91c4d28"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- New catalogs, no dependencies -----------------------------------
    # is_active is a picker convenience only (temporarily/seasonally
    # hiding an option for NEW bills) -- NOT a data-integrity
    # requirement. Every historical quote/invoice/line item snapshots
    # its own name and dollar amount below, so deactivating -- or even
    # deleting -- a catalog entry here never breaks anything already
    # billed.
    op.create_table(
        "services",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "discounts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("percentage", sa.Numeric(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "tax_rates",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("percentage", sa.Numeric(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- Alter existing quotes/invoices/payments --------------------------
    # amount is dropped in favor of a real subtotal/discount/tax/total
    # breakdown -- amount was never actually used anywhere, so there's
    # no real data to migrate or preserve here.
    #
    # discount_id/tax_rate_id use ondelete="SET NULL" -- along with the
    # *_name snapshot columns below, this means deleting a Discount or
    # TaxRate never breaks or blocks anything on an already-issued
    # quote/invoice; the snapshotted name and dollar amount stay
    # correct regardless.
    op.drop_column("quotes", "amount")
    op.add_column("quotes", sa.Column("subtotal", sa.Numeric(), nullable=False, server_default="0"))
    op.add_column("quotes", sa.Column("discount_id", sa.Integer(), sa.ForeignKey("discounts.id", ondelete="SET NULL"), nullable=True))
    op.add_column("quotes", sa.Column("discount_name", sa.String(), nullable=True))
    op.add_column("quotes", sa.Column("discount_amount", sa.Numeric(), nullable=False, server_default="0"))
    op.add_column("quotes", sa.Column("tax_rate_id", sa.Integer(), sa.ForeignKey("tax_rates.id", ondelete="SET NULL"), nullable=True))
    op.add_column("quotes", sa.Column("tax_rate_name", sa.String(), nullable=True))
    op.add_column("quotes", sa.Column("tax_amount", sa.Numeric(), nullable=False, server_default="0"))
    op.add_column("quotes", sa.Column("total", sa.Numeric(), nullable=False, server_default="0"))
    op.add_column("quotes", sa.Column("converted_invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=True))

    op.drop_column("invoices", "amount")
    op.add_column("invoices", sa.Column("subtotal", sa.Numeric(), nullable=False, server_default="0"))
    op.add_column("invoices", sa.Column("discount_id", sa.Integer(), sa.ForeignKey("discounts.id", ondelete="SET NULL"), nullable=True))
    op.add_column("invoices", sa.Column("discount_name", sa.String(), nullable=True))
    op.add_column("invoices", sa.Column("discount_amount", sa.Numeric(), nullable=False, server_default="0"))
    op.add_column("invoices", sa.Column("tax_rate_id", sa.Integer(), sa.ForeignKey("tax_rates.id", ondelete="SET NULL"), nullable=True))
    op.add_column("invoices", sa.Column("tax_rate_name", sa.String(), nullable=True))
    op.add_column("invoices", sa.Column("tax_amount", sa.Numeric(), nullable=False, server_default="0"))
    op.add_column("invoices", sa.Column("total", sa.Numeric(), nullable=False, server_default="0"))
    op.add_column("invoices", sa.Column("source_quote_id", sa.Integer(), sa.ForeignKey("quotes.id"), nullable=True))

    # Float -> Numeric for real decimal precision, now that this gets
    # compared against the new Numeric total fields for payment-status
    # logic -- floating point is a real correctness risk for money.
    op.alter_column("payments", "amount", type_=sa.Numeric(), postgresql_using="amount::numeric")

    # --- New line item tables, depend on quotes/invoices/services already existing ---
    # service_id uses ondelete="SET NULL" -- along with service_name
    # below, deleting a Service never breaks or blocks anything on an
    # already-issued quote/invoice.
    op.create_table(
        "quote_line_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("quote_id", sa.Integer(), sa.ForeignKey("quotes.id"), nullable=False),
        sa.Column("service_id", sa.Integer(), sa.ForeignKey("services.id", ondelete="SET NULL"), nullable=True),
        sa.Column("service_name", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(), nullable=False),
    )

    op.create_table(
        "invoice_line_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("service_id", sa.Integer(), sa.ForeignKey("services.id", ondelete="SET NULL"), nullable=True),
        sa.Column("service_name", sa.String(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("invoice_line_items")
    op.drop_table("quote_line_items")

    op.alter_column("payments", "amount", type_=sa.Float(), postgresql_using="amount::double precision")

    op.drop_column("invoices", "source_quote_id")
    op.drop_column("invoices", "total")
    op.drop_column("invoices", "tax_amount")
    op.drop_column("invoices", "tax_rate_name")
    op.drop_column("invoices", "tax_rate_id")
    op.drop_column("invoices", "discount_amount")
    op.drop_column("invoices", "discount_name")
    op.drop_column("invoices", "discount_id")
    op.drop_column("invoices", "subtotal")
    op.add_column("invoices", sa.Column("amount", sa.Float(), nullable=False, server_default="0"))

    op.drop_column("quotes", "converted_invoice_id")
    op.drop_column("quotes", "total")
    op.drop_column("quotes", "tax_amount")
    op.drop_column("quotes", "tax_rate_name")
    op.drop_column("quotes", "tax_rate_id")
    op.drop_column("quotes", "discount_amount")
    op.drop_column("quotes", "discount_name")
    op.drop_column("quotes", "discount_id")
    op.drop_column("quotes", "subtotal")
    op.add_column("quotes", sa.Column("amount", sa.Float(), nullable=False, server_default="0"))

    op.drop_table("tax_rates")
    op.drop_table("discounts")
    op.drop_table("services")
