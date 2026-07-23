"""add part_locations table, remove single-location columns from parts

Revision ID: d7e2b9c4f108
Revises: c3f8a1e5b2d4
Create Date: 2026-07-23 05:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7e2b9c4f108'
down_revision: Union[str, Sequence[str], None] = 'c3f8a1e5b2d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.

    Creates the part_locations table (one row per part-per-location,
    with its own quantity), then drops parts.quantity_on_hand and
    parts.location_id -- a Part no longer tracks a single quantity/place
    directly; that detail moves to part_locations so a part can be
    split across several locations at once. No data migration: the
    parts table has no real production rows yet (only test-seed data
    from this same development cycle), so the old columns are dropped
    outright rather than backfilled into part_locations rows.
    """
    op.create_table(
        'part_locations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('part_id', sa.Integer(), nullable=False),
        sa.Column('location_id', sa.Integer(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['part_id'], ['parts.id']),
        sa.ForeignKeyConstraint(['location_id'], ['locations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('part_id', 'location_id', name='uq_part_location'),
    )
    op.create_index(op.f('ix_part_locations_id'), 'part_locations', ['id'], unique=False)

    op.drop_constraint('parts_location_id_fkey', 'parts', type_='foreignkey')
    op.drop_column('parts', 'location_id')
    op.drop_column('parts', 'quantity_on_hand')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('parts', sa.Column('quantity_on_hand', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('parts', sa.Column('location_id', sa.Integer(), nullable=True))
    op.create_foreign_key('parts_location_id_fkey', 'parts', 'locations', ['location_id'], ['id'])

    op.drop_index(op.f('ix_part_locations_id'), table_name='part_locations')
    op.drop_table('part_locations')
