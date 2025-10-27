"""add partial covering index for homepage

Revision ID: 7bddccfa1b95
Revises: 20250922_add_grants
Create Date: 2025-10-27 05:52:43.603637

"""

"""add partial btree index for recent homepage listing"""
from alembic import op

revision = '7bddccfa1b95'
down_revision = "da9f1541b952"
branch_labels = None
depends_on = None

IDX = "ix_papers_recent_desc_nonupload"

def upgrade():
    # CONCURRENTLY 需要跳出事务
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