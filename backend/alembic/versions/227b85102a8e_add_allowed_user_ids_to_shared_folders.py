"""add allowed_user_ids to shared_folders

Revision ID: 227b85102a8e
Revises: 69e268237ed3
Create Date: 2025-07-28 03:15:47.238433

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '227b85102a8e'
down_revision = '69e268237ed3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
    "shared_folders",
    sa.Column("allowed_user_ids",
              postgresql.ARRAY(sa.dialects.postgresql.UUID(as_uuid=True)),
              nullable=False,
              server_default="{}"  # 或 ARRAY[]::uuid[]
     )
)


def downgrade() -> None:
    pass 