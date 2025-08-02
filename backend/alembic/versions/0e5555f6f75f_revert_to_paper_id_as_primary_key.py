"""revert_to_paper_id_as_primary_key

Revision ID: 0e5555f6f75f
Revises: 2faca578e4cd
Create Date: 2025-08-02 14:03:58.239399

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text


# revision identifiers, used by Alembic.
revision = '0e5555f6f75f'
down_revision = '2faca578e4cd'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 获取当前数据库连接
    connection = op.get_bind()

    # 1. 在引用表中添加临时列paper_id_old用于存储原始paper_id
    op.add_column('paper_categories', sa.Column('paper_id_old', sa.String(), nullable=True))
    op.add_column('paper_authors', sa.Column('paper_id_old', sa.String(), nullable=True))
    op.add_column('user_files', sa.Column('paper_id_old', sa.String(), nullable=True))
    
    # 2. 更新临时列，存储原始paper_id
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
    
    # 3. 查询并删除外键约束
    # 使用通用方法删除所有外键约束，而不依赖特定名称
    # paper_categories
    op.execute('''
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            SELECT conname INTO constraint_name
            FROM pg_constraint pc
            JOIN pg_class pc1 ON pc.conrelid = pc1.oid
            JOIN pg_class pc2 ON pc.confrelid = pc2.oid
            WHERE pc1.relname = 'paper_categories' 
            AND pc2.relname = 'papers'
            AND pc.contype = 'f';

            IF constraint_name IS NOT NULL THEN
                EXECUTE 'ALTER TABLE paper_categories DROP CONSTRAINT ' || constraint_name;
            END IF;
        END;
        $$;
    ''')
    
    # paper_authors
    op.execute('''
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            SELECT conname INTO constraint_name
            FROM pg_constraint pc
            JOIN pg_class pc1 ON pc.conrelid = pc1.oid
            JOIN pg_class pc2 ON pc.confrelid = pc2.oid
            WHERE pc1.relname = 'paper_authors' 
            AND pc2.relname = 'papers'
            AND pc.contype = 'f';

            IF constraint_name IS NOT NULL THEN
                EXECUTE 'ALTER TABLE paper_authors DROP CONSTRAINT ' || constraint_name;
            END IF;
        END;
        $$;
    ''')
    
    # user_files
    op.execute('''
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            SELECT conname INTO constraint_name
            FROM pg_constraint pc
            JOIN pg_class pc1 ON pc.conrelid = pc1.oid
            JOIN pg_class pc2 ON pc.confrelid = pc2.oid
            WHERE pc1.relname = 'user_files' 
            AND pc2.relname = 'papers'
            AND pc.contype = 'f';

            IF constraint_name IS NOT NULL THEN
                EXECUTE 'ALTER TABLE user_files DROP CONSTRAINT ' || constraint_name;
            END IF;
        END;
        $$;
    ''')
    
    # 4. 删除现有主键约束 (使用通用方式)
    op.execute('''
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            SELECT conname INTO constraint_name
            FROM pg_constraint pc
            JOIN pg_class pc1 ON pc.conrelid = pc1.oid
            WHERE pc1.relname = 'paper_categories' 
            AND pc.contype = 'p';

            IF constraint_name IS NOT NULL THEN
                EXECUTE 'ALTER TABLE paper_categories DROP CONSTRAINT ' || constraint_name;
            END IF;
        END;
        $$;
    ''')
    
    op.execute('''
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            SELECT conname INTO constraint_name
            FROM pg_constraint pc
            JOIN pg_class pc1 ON pc.conrelid = pc1.oid
            WHERE pc1.relname = 'paper_authors' 
            AND pc.contype = 'p';

            IF constraint_name IS NOT NULL THEN
                EXECUTE 'ALTER TABLE paper_authors DROP CONSTRAINT ' || constraint_name;
            END IF;
        END;
        $$;
    ''')
    
    # 5. 删除旧的paper_id列
    op.drop_column('paper_categories', 'paper_id')
    op.drop_column('paper_authors', 'paper_id')
    op.drop_column('user_files', 'paper_id')
    
    # 6. 重命名临时列为paper_id
    op.alter_column('paper_categories', 'paper_id_old', new_column_name='paper_id', nullable=False)
    op.alter_column('paper_authors', 'paper_id_old', new_column_name='paper_id', nullable=False)
    op.alter_column('user_files', 'paper_id_old', new_column_name='paper_id', nullable=False)
    
    # 7. 在papers表中删除id列作为主键，恢复paper_id为主键
    # 删除索引 (如果存在)
    try:
        op.drop_index('ix_papers_id', table_name='papers')
    except:
        pass
        
    try:
        op.drop_index('ix_papers_paper_id_2', table_name='papers')
    except:
        pass
        
    try:
        op.drop_index('ix_papers_paper_id', table_name='papers')
    except:
        pass
    
    # 删除主键约束
    op.execute('''
        DO $$
        DECLARE
            constraint_name text;
        BEGIN
            SELECT conname INTO constraint_name
            FROM pg_constraint pc
            JOIN pg_class pc1 ON pc.conrelid = pc1.oid
            WHERE pc1.relname = 'papers' 
            AND pc.contype = 'p';

            IF constraint_name IS NOT NULL THEN
                EXECUTE 'ALTER TABLE papers DROP CONSTRAINT ' || constraint_name;
            END IF;
        END;
        $$;
    ''')
    
    # 创建新主键和索引
    op.create_primary_key('papers_pkey', 'papers', ['paper_id'])
    
    # 检查索引是否已存在，如果不存在则创建
    op.execute('''
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE tablename = 'papers' AND indexname = 'ix_papers_paper_id'
            ) THEN
                CREATE UNIQUE INDEX ix_papers_paper_id ON papers (paper_id);
            END IF;
        END;
        $$;
    ''')
    
    # 8. 创建新的主键和外键约束
    op.create_primary_key('paper_categories_pkey', 'paper_categories', ['paper_id', 'category'])
    op.create_primary_key('paper_authors_pkey', 'paper_authors', ['paper_id', 'author'])
    
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
    
    # 9. 删除id列
    op.drop_column('papers', 'id')


def downgrade() -> None:
    # 如果需要回滚到使用id作为主键的状态，此处省略
    pass 