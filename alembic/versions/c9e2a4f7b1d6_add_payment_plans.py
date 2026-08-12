# ER-ServiceDesk/alembic/versions/c9e2a4f7b1d6_add_payment_plans.py
"""add payment plans

Revision ID: c9e2a4f7b1d6
Revises: b3d8f6a1e5c9
Create Date: 2026-08-11

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c9e2a4f7b1d6"
down_revision = "b3d8f6a1e5c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "payment_plans",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("invoice_id", sa.Integer(), sa.ForeignKey("invoices.id"), nullable=False),
        sa.Column("installment_amount", sa.Numeric(), nullable=False),
        sa.Column("frequency", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    op.create_table(
        "payment_plan_installments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("payment_plan_id", sa.Integer(), sa.ForeignKey("payment_plans.id"), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("planned_amount", sa.Numeric(), nullable=False),
        sa.Column("payment_id", sa.Integer(), sa.ForeignKey("payments.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("payment_plan_installments")
    op.drop_table("payment_plans")
