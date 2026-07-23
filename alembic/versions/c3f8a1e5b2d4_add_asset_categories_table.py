"""add asset_categories table, convert assets.category to a foreign key

Revision ID: c3f8a1e5b2d4
Revises: 107e4b857700
Create Date: 2026-07-23 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3f8a1e5b2d4'
down_revision: Union[str, Sequence[str], None] = '107e4b857700'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.

    Creates the asset_categories lookup table, then converts
    assets.category from a free-text String column to a category_id
    foreign key against it -- same pattern as ticket_categories. No data
    migration needed: the assets table has no real production rows yet
    (the desktop Inventory window that would populate it doesn't exist
    until this same change lands), so the old string column is dropped
    outright rather than backfilled.
    """
    op.create_table(
        'asset_categories',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index(op.f('ix_asset_categories_id'), 'asset_categories', ['id'], unique=False)

    op.drop_column('assets', 'category')
    op.add_column('assets', sa.Column('category_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_assets_category_id_asset_categories',
        'assets', 'asset_categories',
        ['category_id'], ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_assets_category_id_asset_categories', 'assets', type_='foreignkey')
    op.drop_column('assets', 'category_id')
    op.add_column('assets', sa.Column('category', sa.String(), nullable=True))

    op.drop_index(op.f('ix_asset_categories_id'), table_name='asset_categories')
    op.drop_table('asset_categories')
