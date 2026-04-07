"""add static pages table

Revision ID: 014
Revises: 013
Create Date: 2026-04-07 12:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '014'
down_revision = '013'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'static_pages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('lang', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('content_md', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('url', 'lang', name='uq_static_page_url_lang')
    )
    op.create_index(op.f('ix_static_pages_id'), 'static_pages', ['id'], unique=False)
    op.create_index(op.f('ix_static_pages_url'), 'static_pages', ['url'], unique=False)
    op.create_index(op.f('ix_static_pages_lang'), 'static_pages', ['lang'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_static_pages_lang'), table_name='static_pages')
    op.drop_index(op.f('ix_static_pages_url'), table_name='static_pages')
    op.drop_index(op.f('ix_static_pages_id'), table_name='static_pages')
    op.drop_table('static_pages')
