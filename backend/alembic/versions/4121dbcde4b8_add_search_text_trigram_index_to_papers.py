"""add search_text trigram index to papers

Revision ID: 4121dbcde4b8
Revises: 61643ad622c3
Create Date: 2025-11-20 20:31:12.960832

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4121dbcde4b8'
down_revision = '61643ad622c3'
branch_labels = None
depends_on = None



def upgrade():
    # 1) 确保扩展存在
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # 2) 确保 search_text 列存在
    #   这里用原始 SQL 带 IF NOT EXISTS，避免你刚刚手动 ALTER TABLE 导致冲突
    op.execute("""
        ALTER TABLE papers
        ADD COLUMN IF NOT EXISTS search_text TEXT
    """)


def downgrade():
    # 回滚时可以不删扩展（安全起见）
    # 如果你想干净，可以：op.execute("DROP EXTENSION IF EXISTS pg_trgm")
    op.execute("""
        ALTER TABLE papers
        DROP COLUMN IF EXISTS search_text
    """)