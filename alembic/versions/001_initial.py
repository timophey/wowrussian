"""Initial migration - create all tables

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Create projects table
    op.create_table('projects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('domain', sa.String(), nullable=False),
        sa.Column('base_url', sa.String(), nullable=False),
        sa.Column('status', sqlite.Enum('pending', 'crawling', 'parsing', 'analyzing', 'completed', 'stopped', 'failed', name='projectstatus'), nullable=False),
        sa.Column('stats', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_projects_id'), 'projects', ['id'], unique=False)
    op.create_index(op.f('ix_projects_domain'), 'projects', ['domain'], unique=False)

    # Create pages table
    op.create_table('pages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('html_file_path', sa.String(), nullable=True),
        sa.Column('text_file_path', sa.String(), nullable=True),
        sa.Column('status', sqlite.Enum('queued', 'crawling', 'parsed', 'analyzed', 'failed', name='pagestatus'), nullable=False),
        sa.Column('words_count', sa.Integer(), nullable=True),
        sa.Column('foreign_words_count', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_pages_id'), 'pages', ['id'], unique=False)
    op.create_index(op.f('ix_pages_url'), 'pages', ['url'], unique=False)

    # Create foreign_words table
    op.create_table('foreign_words',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('page_id', sa.Integer(), nullable=False),
        sa.Column('word', sa.String(), nullable=False),
        sa.Column('count', sa.Integer(), nullable=False),
        sa.Column('language_guess', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['page_id'], ['pages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('page_id', 'word', name='uq_page_word')
    )
    op.create_index(op.f('ix_foreign_words_id'), 'foreign_words', ['id'], unique=False)
    op.create_index(op.f('ix_foreign_words_word'), 'foreign_words', ['word'], unique=False)

    # Create crawl_queue table
    op.create_table('crawl_queue',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('url', sa.String(), nullable=False),
        sa.Column('status', sqlite.Enum('pending', 'processing', 'completed', 'failed', name='queuestatus'), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('last_attempt_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_crawl_queue_id'), 'crawl_queue', ['id'], unique=False)
    op.create_index(op.f('ix_crawl_queue_project_status'), 'crawl_queue', ['project_id', 'status'], unique=False)


def downgrade() -> None:
    op.drop_table('crawl_queue')
    op.drop_table('foreign_words')
    op.drop_table('pages')
    op.drop_table('projects')
    op.drop_table('users')
    
    # Drop enums
    op.execute('DROP TYPE IF EXISTS queuestatus')
    op.execute('DROP TYPE IF EXISTS pagestatus')
    op.execute('DROP TYPE IF EXISTS projectstatus')