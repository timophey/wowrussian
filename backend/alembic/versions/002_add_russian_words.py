"""Add russian_words table with source tracking

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create russian_words table
    op.create_table('russian_words',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('page_id', sa.Integer(), nullable=False),
        sa.Column('word', sa.String(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['page_id'], ['pages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('page_id', 'word', name='uq_page_russian_word')
    )
    op.create_index(op.f('ix_russian_words_id'), 'russian_words', ['id'], unique=False)
    op.create_index(op.f('ix_russian_words_word'), 'russian_words', ['word'], unique=False)


def downgrade() -> None:
    op.drop_table('russian_words')
