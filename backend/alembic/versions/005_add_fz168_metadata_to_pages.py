"""Add fz168 metadata columns to pages table

Revision ID: 005
Revises: 004
Create Date: 2024-01-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add fz168 metadata columns to pages table."""
    # Add JSONB columns for storing 168fz analysis metadata
    op.add_column('pages', sa.Column('fz168_statistics', sa.JSON(), nullable=True))
    op.add_column('pages', sa.Column('fz168_summary', sa.JSON(), nullable=True))
    op.add_column('pages', sa.Column('fz168_checks', sa.JSON(), nullable=True))
    op.add_column('pages', sa.Column('fz168_dictionaries', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove fz168 metadata columns from pages table."""
    op.drop_column('pages', 'fz168_dictionaries')
    op.drop_column('pages', 'fz168_checks')
    op.drop_column('pages', 'fz168_summary')
    op.drop_column('pages', 'fz168_statistics')
