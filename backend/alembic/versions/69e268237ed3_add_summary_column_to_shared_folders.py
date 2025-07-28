"""add summary column to shared_folders

Revision ID: 69e268237ed3
Revises: f3e5bfb7a3ac
Create Date: 2025-07-26 02:49:17.907048

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '69e268237ed3'
down_revision = 'f3e5bfb7a3ac'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "shared_folders",
        sa.Column("summary", sa.Text(), nullable=True)
    )

def downgrade():
    op.drop_column("shared_folders", "summary")