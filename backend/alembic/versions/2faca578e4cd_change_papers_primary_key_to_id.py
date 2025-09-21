"""change_papers_primary_key_to_id

Revision ID: 2faca578e4cd
Revises: 61c3f4490cfa
Create Date: 2025-08-02 12:11:16.392556

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision = '2faca578e4cd'
down_revision = '61c3f4490cfa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Step 1: 在 papers 表中添加新的自增主键列 id
    op.execute('ALTER TABLE papers ADD COLUMN id SERIAL')
    
    # Step 2: 为新的id列创建唯一索引，以便其他表可以引用它作为外键
    op.create_index(op.f('ix_papers_id'), 'papers', ['id'], unique=True)
    
    # Step 3: 在引用表中添加新的外键列
    op.add_column('paper_categories', sa.Column('paper_id_new', sa.Integer, nullable=True))
    op.add_column('paper_authors', sa.Column('paper_id_new', sa.Integer, nullable=True))
    op.add_column('user_files', sa.Column('paper_id_new', sa.Integer, nullable=True))
    
    # Step 4: 更新引用表中的新外键列值
    op.execute('''
        UPDATE paper_categories pc
        SET paper_id_new = p.id
        FROM papers p
        WHERE pc.paper_id = p.paper_id
    ''')
    
    op.execute('''
        UPDATE paper_authors pa
        SET paper_id_new = p.id
        FROM papers p
        WHERE pa.paper_id = p.paper_id
    ''')
    
    op.execute('''
        UPDATE user_files uf
        SET paper_id_new = p.id
        FROM papers p
        WHERE uf.paper_id = p.paper_id
    ''')
    
    # Step 5: 删除旧的外键约束和主键约束
    # 先删除外键约束
    op.drop_constraint('paper_categories_paper_id_fkey', 'paper_categories', type_='foreignkey')
    op.drop_constraint('paper_authors_paper_id_fkey', 'paper_authors', type_='foreignkey')
    op.drop_constraint('user_files_paper_id_fkey', 'user_files', type_='foreignkey')
    
    # 删除联合主键
    op.drop_constraint('paper_categories_pkey', 'paper_categories', type_='primary')
    op.drop_constraint('paper_authors_pkey', 'paper_authors', type_='primary')
    
    # Step 6: 创建新的主键
    op.create_primary_key('paper_categories_pkey', 'paper_categories', ['paper_id_new', 'category'])
    op.create_primary_key('paper_authors_pkey', 'paper_authors', ['paper_id_new', 'author'])
    
    # Step 7: 添加新的外键约束
    op.create_foreign_key(
        'paper_categories_paper_id_new_fkey', 
        'paper_categories', 'papers', 
        ['paper_id_new'], ['id'], 
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'paper_authors_paper_id_new_fkey', 
        'paper_authors', 'papers', 
        ['paper_id_new'], ['id'], 
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'user_files_paper_id_new_fkey', 
        'user_files', 'papers', 
        ['paper_id_new'], ['id'], 
        ondelete='CASCADE'
    )
    
    # Step 8: 设置新列为NOT NULL
    op.alter_column('paper_categories', 'paper_id_new', nullable=False)
    op.alter_column('paper_authors', 'paper_id_new', nullable=False)
    op.alter_column('user_files', 'paper_id_new', nullable=False)
    
    # Step 9: 删除旧的列
    op.drop_column('paper_categories', 'paper_id')
    op.drop_column('paper_authors', 'paper_id')
    
    # Step 10: 重命名新列为paper_id (user_files表)
    op.drop_column('user_files', 'paper_id')
    op.alter_column('user_files', 'paper_id_new', new_column_name='paper_id')
    
    # Step 11: 重命名新列为paper_id (关联表)
    op.alter_column('paper_categories', 'paper_id_new', new_column_name='paper_id')
    op.alter_column('paper_authors', 'paper_id_new', new_column_name='paper_id')
    
    # Step 12: 删除papers表的主键，保留paper_id列作为普通列
    op.drop_constraint('papers_pkey', 'papers', type_='primary')
    
    # Step 13: 设置id为新主键
    op.create_primary_key('papers_pkey', 'papers', ['id'])
    
    # 保留paper_id作为非唯一索引
    op.create_index(op.f('ix_papers_paper_id_2'), 'papers', ['paper_id'], unique=False)
    op.drop_index('ix_papers_paper_id', table_name='papers')
    op.create_index(op.f('ix_papers_paper_id'), 'papers', ['paper_id'], unique=False)


def downgrade() -> None:
    # 恢复索引
    op.drop_index(op.f('ix_papers_id'), table_name='papers')
    op.drop_index(op.f('ix_papers_paper_id_2'), table_name='papers')
    
    # 恢复paper_id为主键
    op.drop_constraint('papers_pkey', 'papers', type_='primary')
    op.create_primary_key('papers_pkey', 'papers', ['paper_id'])
    op.create_index(op.f('ix_papers_paper_id'), 'papers', ['paper_id'], unique=True)
    
    # 在子表中添加paper_id字符串列
    op.add_column('paper_categories', sa.Column('paper_id_old', sa.String(), nullable=True))
    op.add_column('paper_authors', sa.Column('paper_id_old', sa.String(), nullable=True))
    op.add_column('user_files', sa.Column('paper_id_old', sa.String(), nullable=True))
    
    # 更新子表中的paper_id_old列值
    op.execute('''
        UPDATE paper_categories pc
        SET paper_id_old = p.paper_id
        FROM papers p
        WHERE pc.paper_id = p.id
    ''')
    
    op.execute('''
        UPDATE paper_authors pa
        SET paper_id_old = p.paper_id
        FROM papers p
        WHERE pa.paper_id = p.id
    ''')
    
    op.execute('''
        UPDATE user_files uf
        SET paper_id_old = p.paper_id
        FROM papers p
        WHERE uf.paper_id = p.id
    ''')
    
    # 删除新的外键约束
    op.drop_constraint('paper_categories_paper_id_fkey', 'paper_categories', type_='foreignkey')
    op.drop_constraint('paper_authors_paper_id_fkey', 'paper_authors', type_='foreignkey')
    op.drop_constraint('user_files_paper_id_fkey', 'user_files', type_='foreignkey')
    
    # 删除联合主键
    op.drop_constraint('paper_categories_pkey', 'paper_categories', type_='primary')
    op.drop_constraint('paper_authors_pkey', 'paper_authors', type_='primary')
    
    # 重命名新列并设置NOT NULL
    op.drop_column('paper_categories', 'paper_id')
    op.alter_column('paper_categories', 'paper_id_old', new_column_name='paper_id', nullable=False)
    
    op.drop_column('paper_authors', 'paper_id')
    op.alter_column('paper_authors', 'paper_id_old', new_column_name='paper_id', nullable=False)
    
    op.drop_column('user_files', 'paper_id')
    op.alter_column('user_files', 'paper_id_old', new_column_name='paper_id', nullable=False)
    
    # 创建新的联合主键
    op.create_primary_key('paper_categories_pkey', 'paper_categories', ['paper_id', 'category'])
    op.create_primary_key('paper_authors_pkey', 'paper_authors', ['paper_id', 'author'])
    
    # 添加新的外键约束
    op.create_foreign_key(
        'paper_categories_paper_id_fkey', 
        'paper_categories', 'papers', 
        ['paper_id'], ['paper_id'], 
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'paper_authors_paper_id_fkey', 
        'paper_authors', 'papers', 
        ['paper_id'], ['paper_id'], 
        ondelete='CASCADE'
    )
    
    op.create_foreign_key(
        'user_files_paper_id_fkey', 
        'user_files', 'papers', 
        ['paper_id'], ['paper_id'], 
        ondelete='CASCADE'
    )
    
    # 删除 id 列
    op.drop_column('papers', 'id') 