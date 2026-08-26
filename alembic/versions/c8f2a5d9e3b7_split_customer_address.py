# ER-ServiceDesk/alembic/versions/c8f2a5d9e3b7_split_customer_address.py
"""split customers.address into street/state/zip_code

Revision ID: c8f2a5d9e3b7
Revises: b6d9e3a8c1f4
Create Date: 2026-08-25

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c8f2a5d9e3b7"
down_revision = "b6d9e3a8c1f4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("customers", "address")
    op.add_column("customers", sa.Column("street", sa.String(), nullable=True))
    op.add_column("customers", sa.Column("state", sa.String(), nullable=True))
    op.add_column("customers", sa.Column("zip_code", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "zip_code")
    op.drop_column("customers", "state")
    op.drop_column("customers", "street")
    op.add_column("customers", sa.Column("address", sa.String(), nullable=True))
