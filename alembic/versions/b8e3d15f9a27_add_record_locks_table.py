"""add record_locks table for check-out style editing locks

Revision ID: b8e3d15f9a27
Revises: a4d7f9e2c815
Create Date: 2026-07-24 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b8e3d15f9a27'
down_revision: Union[str, Sequence[str], None] = 'a4d7f9e2c815'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.

    Adds one generic record_locks table covering every editable entity
    type (tickets, customers, assets, parts, users, roles, and every
    lookup table), rather than a separate lock column per table -- the
    same reasoning already used for the lookup-table CRUD pattern.
    """
    op.create_table(
        'record_locks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('locked_by_user_id', sa.Integer(), nullable=False),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['locked_by_user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_type', 'entity_id', name='uq_record_lock_entity'),
    )
    op.create_index(op.f('ix_record_locks_id'), 'record_locks', ['id'], unique=False)
    op.create_index(op.f('ix_record_locks_entity_type'), 'record_locks', ['entity_type'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_record_locks_entity_type'), table_name='record_locks')
    op.drop_index(op.f('ix_record_locks_id'), table_name='record_locks')
    op.drop_table('record_locks')
