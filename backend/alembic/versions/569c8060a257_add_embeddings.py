"""add embeddings

Revision ID: 569c8060a257
Revises: 058d14be02dc
Create Date: 2025-07-21 18:51:44.117490

"""
from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '569c8060a257'
down_revision = '058d14be02dc'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'papers',
        sa.Column('embedding', Vector(768), nullable=True)
    )



def downgrade() -> None:
    op.drop_column('papers', 'embedding')