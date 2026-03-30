"""Add source column to foreign_words table

Revision ID: 004
Revises: 003
Create Date: 2024-01-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add source column to foreign_words table."""
    op.add_column('foreign_words', sa.Column('source', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove source column from foreign_words table."""
    op.drop_column('foreign_words', 'source')
