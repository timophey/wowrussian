"""Add fz168_raw_response column to pages table

Revision ID: 006
Revises: 005
Create Date: 2024-01-01 00:00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add fz168_raw_response column to pages table."""
    op.add_column('pages', sa.Column('fz168_raw_response', sa.JSON(), nullable=True))


def downgrade() -> None:
    """Remove fz168_raw_response column from pages table."""
    op.drop_column('pages', 'fz168_raw_response')
