# ER-ServiceDesk/alembic/versions/b6d9e3a8c1f4_drop_message_template_subject.py
"""drop message_templates.subject

Revision ID: b6d9e3a8c1f4
Revises: a1c4e7f2b9d3
Create Date: 2026-08-24

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "b6d9e3a8c1f4"
down_revision = "a1c4e7f2b9d3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("message_templates", "subject")


def downgrade() -> None:
    # Restored nullable, not NOT NULL -- a real downgrade can't know
    # what subject text to backfill for rows created after the column
    # was dropped.
    op.add_column("message_templates", sa.Column("subject", sa.String(), nullable=True))
