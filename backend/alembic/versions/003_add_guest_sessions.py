"""Add guest_sessions table and guest_session_id to projects

Revision ID: 003
Revises: 002
Create Date: 2024-01-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create guest_sessions table
    op.create_table('guest_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_token', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_activity', sa.DateTime(), nullable=False),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('user_agent', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_token')
    )
    op.create_index(op.f('ix_guest_sessions_id'), 'guest_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_guest_sessions_session_token'), 'guest_sessions', ['session_token'], unique=False)

    # Add guest_session_id column to projects table
    op.add_column('projects', sa.Column('guest_session_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_projects_guest_session',
        'projects', 'guest_sessions',
        ['guest_session_id'], ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    # Remove foreign key first
    op.drop_constraint('fk_projects_guest_session', 'projects', type_='foreignkey')
    # Remove guest_session_id column
    op.drop_column('projects', 'guest_session_id')
    # Drop guest_sessions table
    op.drop_index(op.f('ix_guest_sessions_session_token'), table_name='guest_sessions')
    op.drop_index(op.f('ix_guest_sessions_id'), table_name='guest_sessions')
    op.drop_table('guest_sessions')
