"""add whitelist words table

Revision ID: 013
Revises: 012
Create Date: 2026-04-06 08:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '013'
down_revision = '012'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'whitelist_words',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('word', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('project_id', 'word', name='uq_project_word')
    )
    op.create_index(op.f('ix_whitelist_words_id'), 'whitelist_words', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_whitelist_words_id'), table_name='whitelist_words')
    op.drop_table('whitelist_words')
