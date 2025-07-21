"""fixed bugs

Revision ID: b7d707677a2c
Revises: 5f925f43672f
Create Date: 2025-07-17 16:56:47.704000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7d707677a2c'
down_revision = '5f925f43672f'
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