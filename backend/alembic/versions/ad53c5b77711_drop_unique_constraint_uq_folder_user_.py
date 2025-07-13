"""drop unique constraint uq_folder_user_name on folders

Revision ID: ad53c5b77711
Revises: eb485b98f27c
Create Date: 2025-07-13 05:19:15.921004

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ad53c5b77711'
down_revision = 'eb485b98f27c'
branch_labels = None
depends_on = None


def upgrade():
    # 把数据库里的唯一约束给扔了
    op.drop_constraint(
        constraint_name='uq_folder_user_name',
        table_name='folders',
        type_='unique'
    )

def downgrade():
    # 如果要回滚，就再建回去
    op.create_unique_constraint(
        constraint_name='uq_folder_user_name',
        table_name='folders',
        columns=['user_id', 'name']
    )