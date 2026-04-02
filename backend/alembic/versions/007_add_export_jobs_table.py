"""add export_jobs table

Revision ID: 007
Revises: 006
Create Date: 2024-01-01 00:00:00

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create export_jobs table."""
    op.create_table('export_jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.Enum('pending', 'processing', 'completed', 'failed', name='exportjobstatus'), nullable=False),
        sa.Column('language', sa.String(), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('total_words', sa.Integer(), nullable=True),
        sa.Column('processed_words', sa.Integer(), nullable=True),
        sa.Column('file_path', sa.String(), nullable=True),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('celery_task_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_export_jobs_id'), 'export_jobs', ['id'], unique=False)
    op.create_index(op.f('ix_export_jobs_project_id'), 'export_jobs', ['project_id'], unique=False)


def downgrade() -> None:
    """Remove export_jobs table."""
    op.drop_index(op.f('ix_export_jobs_project_id'), table_name='export_jobs')
    op.drop_index(op.f('ix_export_jobs_id'), table_name='export_jobs')
    op.drop_table('export_jobs')
    
    # Drop enum type for PostgreSQL
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute('DROP TYPE IF EXISTS exportjobstatus')
