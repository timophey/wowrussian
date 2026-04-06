"""add user role column

Revision ID: 011
Revises: 010
Create Date: 2026-04-06 00:00:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum type for PostgreSQL with uppercase values matching Python enum
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute("CREATE TYPE userrole AS ENUM ('USER', 'ADMIN')")
    
    # Add role column with default value 'USER'
    op.add_column('users', sa.Column('role', sa.String(), nullable=True))
    
    # Set default value for existing users
    op.execute("UPDATE users SET role = 'USER' WHERE role IS NULL")
    
    # Make column not nullable after setting defaults
    op.alter_column('users', 'role', nullable=False)
    
    # For PostgreSQL, convert to proper enum type
    if conn.dialect.name == 'postgresql':
        op.execute("""
            ALTER TABLE users 
            ALTER COLUMN role TYPE userrole 
            USING role::userrole
        """)


def downgrade() -> None:
    conn = op.get_bind()
    
    if conn.dialect.name == 'postgresql':
        # Drop the column first
        op.drop_column('users', 'role')
        # Then drop the enum type
        op.execute('DROP TYPE IF EXISTS userrole')
    else:
        op.drop_column('users', 'role')
