"""remove unused attachments table and feature

Revision ID: a4d7f9e2c815
Revises: f2c8b6a91d34
Create Date: 2026-07-24 07:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a4d7f9e2c815'
down_revision: Union[str, Sequence[str], None] = 'f2c8b6a91d34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.

    Drops the attachments table entirely. The feature was scaffolded
    early in the project (model, schema, CRUD, routes) but never had a
    desktop UI built for it, and nothing in the backend ever actually
    wrote a file to disk for it -- confirmed before this migration was
    written, not assumed. Removed outright rather than left dormant,
    same reasoning as the earlier removal of the unused Status.color
    column.
    """
    op.drop_table('attachments')


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        'attachments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('file_path', sa.String(), nullable=False),
        sa.Column('file_name', sa.String(), nullable=False),
        sa.Column('uploaded_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id']),
        sa.PrimaryKeyConstraint('id'),
    )
