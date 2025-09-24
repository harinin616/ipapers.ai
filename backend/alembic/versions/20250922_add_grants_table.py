"""create grants table with embedding vector

Revision ID: 20250922_add_grants
Revises: 9367b15308cd
Create Date: 2025-09-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = '20250922_add_grants'
down_revision = '9367b15308cd'
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        'grants',
        sa.Column('grant_id', sa.String(), primary_key=True, index=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('agency', sa.String(), nullable=True),
        sa.Column('synopsis', sa.Text(), nullable=True),
        sa.Column('detail_url', sa.String(), nullable=True),
        sa.Column('posted_date', sa.DateTime(), nullable=True),
        sa.Column('updated_date', sa.DateTime(), nullable=True),
        sa.Column('close_date', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('embedding', Vector(768), nullable=True),
    )


def downgrade():
    op.drop_table('grants')
