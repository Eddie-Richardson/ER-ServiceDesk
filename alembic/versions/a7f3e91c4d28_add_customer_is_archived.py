# ER-ServiceDesk/alembic/versions/a7f3e91c4d28_add_customer_is_archived.py
"""add customer is_archived

Revision ID: a7f3e91c4d28
Revises: ec97585605a1
Create Date: 2026-08-11

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a7f3e91c4d28"
down_revision = "ec97585605a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "customers",
        sa.Column("is_archived", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("customers", "is_archived")
