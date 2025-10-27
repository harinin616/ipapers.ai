"""add homepage recent partial index (post-merge)"""
from alembic import op

revision = 'f1c2e2c3e061'
# 生成器里已有 revision，保留即可
down_revision = "20251027_merge_heads"  # ← 改成你的合并head

IDX = "ix_papers_recent_desc_nonupload"

def upgrade():
    # CONCURRENTLY 需要非事务
    with op.get_context().autocommit_block():
        op.execute(f"""
            CREATE INDEX CONCURRENTLY IF NOT EXISTS {IDX}
            ON papers USING btree (published_date DESC, paper_id DESC)
            WHERE platform <> 'upload' AND published_date IS NOT NULL
        """)
        op.execute("ANALYZE papers")

def downgrade():
    with op.get_context().autocommit_block():
        op.execute(f"DROP INDEX CONCURRENTLY IF EXISTS {IDX}")
