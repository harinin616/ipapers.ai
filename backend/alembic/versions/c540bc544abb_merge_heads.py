"""merge heads

Revision ID: c540bc544abb
Revises: 805d031e0c75, 9a1be55b95ad
Create Date: 2025-07-09 19:17:53.203168

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c540bc544abb'
down_revision = ('805d031e0c75', '9a1be55b95ad')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass 