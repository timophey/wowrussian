"""add_cancelled_to_export_jobs

Revision ID: 008
Revises: 007_add_export_jobs_table
Create Date: 2026-04-02 07:36:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add cancelled column to export_jobs table
    op.add_column('export_jobs', sa.Column('cancelled', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    # Remove cancelled column
    op.drop_column('export_jobs', 'cancelled')
