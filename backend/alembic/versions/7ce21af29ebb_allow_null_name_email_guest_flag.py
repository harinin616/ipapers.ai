"""allow null name/email + guest flag

Revision ID: 7ce21af29ebb
Revises: 8e7d478e86d9
Create Date: 2025-07-16 20:59:34.934973

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7ce21af29ebb'
down_revision = '8e7d478e86d9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass 