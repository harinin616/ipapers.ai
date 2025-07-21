"""add selected flag to user_files

Revision ID: 1e74cbe6aa38
Revises: 732cb6bc8b69
Create Date: 2025-07-17 01:58:49.812518

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1e74cbe6aa38'
down_revision = '732cb6bc8b69'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_files",
        sa.Column(
            "selected",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),  # 现有行 = false
        ),
    )


def downgrade() -> None:
    op.drop_column("user_files", "selected")