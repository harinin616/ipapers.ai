"""fixed bugs

Revision ID: a2c18246d03b
Revises: b7d707677a2c
Create Date: 2025-07-17 16:57:13.431342

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a2c18246d03b'
down_revision = 'b7d707677a2c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
  DO $$
  DECLARE
    max_id int;
  BEGIN
    SELECT COALESCE(MAX(legacy_user_id), 0) + 1 INTO max_id FROM users;
    EXECUTE format(
      'ALTER TABLE users ALTER COLUMN legacy_user_id RESTART WITH %s',
      max_id
    );
  END $$;
""")


def downgrade() -> None:
    pass 