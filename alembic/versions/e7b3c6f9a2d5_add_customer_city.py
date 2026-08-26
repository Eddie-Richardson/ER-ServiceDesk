# ER-ServiceDesk/alembic/versions/e7b3c6f9a2d5_add_customer_city.py
"""add customers.city

Revision ID: e7b3c6f9a2d5
Revises: d4e8f1a6c9b3
Create Date: 2026-08-26

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e7b3c6f9a2d5"
down_revision = "d4e8f1a6c9b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("city", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "city")
