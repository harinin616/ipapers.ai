"""allow null name/email

Revision ID: 732cb6bc8b69
Revises: 7ce21af29ebb
Create Date: 2025-07-16 21:00:28.353396

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '732cb6bc8b69'
down_revision = '7ce21af29ebb'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('users', 'name',  existing_type=sa.String(), nullable=True)
    op.alter_column('users', 'email', existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    op.alter_column('users', 'name',  existing_type=sa.String(), nullable=False)
    op.alter_column('users', 'email', existing_type=sa.String(), nullable=False)