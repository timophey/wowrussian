"""make user_id nullable in projects

Revision ID: 010
Revises: 009
Create Date: 2026-04-03 18:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Make user_id nullable in projects table to support guest sessions."""
    op.alter_column('projects', 'user_id',
               existing_type=sa.Integer(),
               nullable=True)


def downgrade() -> None:
    """Revert user_id to non-nullable."""
    op.alter_column('projects', 'user_id',
               existing_type=sa.Integer(),
               nullable=False)
