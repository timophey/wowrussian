"""add_timezone_to_export_jobs

Revision ID: 009
Revises: 008
Create Date: 2026-04-03 09:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add timezone column to export_jobs table
    op.add_column('export_jobs', sa.Column('timezone', sa.String(), nullable=False, server_default='UTC'))


def downgrade() -> None:
    # Remove timezone column
    op.drop_column('export_jobs', 'timezone')
