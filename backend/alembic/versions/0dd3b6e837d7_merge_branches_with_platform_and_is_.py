"""merge branches with platform and is_public

Revision ID: 0dd3b6e837d7
Revises: 5a121b67b683, 6f10c1c42a0e
Create Date: 2025-08-03 09:46:17.690570

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0dd3b6e837d7'
down_revision = ('5a121b67b683', '6f10c1c42a0e')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass 