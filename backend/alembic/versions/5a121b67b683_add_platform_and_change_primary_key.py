"""add_platform_and_change_primary_key

Revision ID: 5a121b67b683
Revises: 0e5555f6f75f
Create Date: 2025-08-02 14:21:53.869391

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a121b67b683'
down_revision = '0e5555f6f75f'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. 首先添加platform列，设置默认值为"arxiv"
    op.add_column('papers', sa.Column('platform', sa.String(), nullable=False, server_default='arxiv'))
    
    # 2. 先删除外键约束
    # paper_categories表的外键
    op.drop_constraint('paper_categories_paper_id_fkey', 'paper_categories', type_='foreignkey')
    # paper_authors表的外键
    op.drop_constraint('paper_authors_paper_id_fkey', 'paper_authors', type_='foreignkey')
    # user_files表的外键
    op.drop_constraint('user_files_paper_id_fkey', 'user_files', type_='foreignkey')
    
    # 3. 删除现有的主键约束
    op.drop_constraint('papers_pkey', 'papers', type_='primary')
    
    # 4. 创建新的复合主键
    op.create_primary_key('papers_pkey', 'papers', ['paper_id', 'platform'])
    
    # 5. 在关联表中添加platform列
    op.add_column('paper_categories', sa.Column('platform', sa.String(), nullable=False, server_default='arxiv'))
    op.add_column('paper_authors', sa.Column('platform', sa.String(), nullable=False, server_default='arxiv'))
    op.add_column('user_files', sa.Column('platform', sa.String(), nullable=False, server_default='arxiv'))
    
    # 6. 重新创建外键约束，指向新的复合主键
    # paper_categories表的外键
    op.create_foreign_key(
        'paper_categories_paper_id_platform_fkey', 'paper_categories', 'papers',
        ['paper_id', 'platform'], ['paper_id', 'platform'],
        ondelete='CASCADE'
    )
    # paper_authors表的外键
    op.create_foreign_key(
        'paper_authors_paper_id_platform_fkey', 'paper_authors', 'papers',
        ['paper_id', 'platform'], ['paper_id', 'platform'],
        ondelete='CASCADE'
    )
    # user_files表的外键
    op.create_foreign_key(
        'user_files_paper_id_platform_fkey', 'user_files', 'papers',
        ['paper_id', 'platform'], ['paper_id', 'platform'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    # 1. 删除外键约束
    op.drop_constraint('paper_categories_paper_id_platform_fkey', 'paper_categories', type_='foreignkey')
    op.drop_constraint('paper_authors_paper_id_platform_fkey', 'paper_authors', type_='foreignkey')
    op.drop_constraint('user_files_paper_id_platform_fkey', 'user_files', type_='foreignkey')
    
    # 2. 删除复合主键约束
    op.drop_constraint('papers_pkey', 'papers', type_='primary')
    
    # 3. 删除关联表中的platform列
    op.drop_column('paper_categories', 'platform')
    op.drop_column('paper_authors', 'platform')
    op.drop_column('user_files', 'platform')
    
    # 4. 恢复原来的单列主键约束
    op.create_primary_key('papers_pkey', 'papers', ['paper_id'])
    
    # 5. 重新创建原来的外键约束
    op.create_foreign_key(
        'paper_categories_paper_id_fkey', 'paper_categories', 'papers',
        ['paper_id'], ['paper_id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'paper_authors_paper_id_fkey', 'paper_authors', 'papers',
        ['paper_id'], ['paper_id'],
        ondelete='CASCADE'
    )
    op.create_foreign_key(
        'user_files_paper_id_fkey', 'user_files', 'papers',
        ['paper_id'], ['paper_id'],
        ondelete='CASCADE'
    )
    
    # 6. 删除platform列
    op.drop_column('papers', 'platform') 