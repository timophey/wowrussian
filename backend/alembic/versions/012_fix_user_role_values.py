"""fix user role values to uppercase

Revision ID: 012
Revises: 011
Create Date: 2026-04-06 00:01:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '012'
down_revision = '011'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    
    if conn.dialect.name == 'postgresql':
        # Create new enum type with uppercase values
        op.execute("CREATE TYPE userrole_new AS ENUM ('USER', 'ADMIN')")
        
        # Convert existing column to text first
        op.execute("""
            ALTER TABLE users 
            ALTER COLUMN role TYPE TEXT
            USING role::TEXT
        """)
        
        # Drop old enum type
        op.execute("DROP TYPE userrole")
        
        # Update values to uppercase
        op.execute("UPDATE users SET role = 'USER' WHERE role = 'user'")
        op.execute("UPDATE users SET role = 'ADMIN' WHERE role = 'admin'")
        
        # Convert to new enum type
        op.execute("""
            ALTER TABLE users 
            ALTER COLUMN role TYPE userrole_new 
            USING role::userrole_new
        """)
        
        # Rename the type
        op.execute("ALTER TYPE userrole_new RENAME TO userrole")
    else:
        # For non-PostgreSQL, just update the values
        op.execute("UPDATE users SET role = 'USER' WHERE role = 'user'")
        op.execute("UPDATE users SET role = 'ADMIN' WHERE role = 'admin'")


def downgrade() -> None:
    conn = op.get_bind()
    
    if conn.dialect.name == 'postgresql':
        # Create old enum type
        op.execute("CREATE TYPE userrole_old AS ENUM ('user', 'admin')")
        
        # Convert to text
        op.execute("""
            ALTER TABLE users 
            ALTER COLUMN role TYPE TEXT
            USING role::TEXT
        """)
        
        # Drop new enum type
        op.execute("DROP TYPE userrole")
        
        # Update values to lowercase
        op.execute("UPDATE users SET role = 'user' WHERE role = 'USER'")
        op.execute("UPDATE users SET role = 'admin' WHERE role = 'ADMIN'")
        
        # Convert to old enum type
        op.execute("""
            ALTER TABLE users 
            ALTER COLUMN role TYPE userrole_old 
            USING role::userrole_old
        """)
        
        # Rename the type
        op.execute("ALTER TYPE userrole_old RENAME TO userrole")
    else:
        op.execute("UPDATE users SET role = 'user' WHERE role = 'USER'")
        op.execute("UPDATE users SET role = 'admin' WHERE role = 'ADMIN'")
