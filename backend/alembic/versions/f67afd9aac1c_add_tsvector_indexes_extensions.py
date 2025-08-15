"""add tsvector+indexes+extensions

Revision ID: f67afd9aac1c
Revises: 4ae140ce641e
Create Date: 2025-08-15 18:33:34.408608

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = 'f67afd9aac1c'
down_revision = '4ae140ce641e'
branch_labels = None
depends_on = None


def upgrade():
    # 1) 扩展（幂等）
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")

    # 2) 加列（先允许 NULL，回填后再改为 NOT NULL，避免阻塞）
    op.add_column("papers", sa.Column("tsv", pg.TSVECTOR(), nullable=True))

    # 3) 回填历史数据（权重：A=title，B=abstract）
    op.execute("""
    UPDATE papers
    SET tsv =
      setweight(to_tsvector('simple', coalesce(unaccent(title),'')),'A') ||
      setweight(to_tsvector('simple', coalesce(unaccent(abstract),'')),'B');
    """)

    # 4) 触发器函数：INSERT/UPDATE 自动维护 tsv
    op.execute("""
    CREATE OR REPLACE FUNCTION papers_tsv_update() RETURNS trigger AS $$
    BEGIN
      NEW.tsv :=
        setweight(to_tsvector('simple', coalesce(unaccent(NEW.title),'')),'A') ||
        setweight(to_tsvector('simple', coalesce(unaccent(NEW.abstract),'')),'B');
      RETURN NEW;
    END
    $$ LANGUAGE plpgsql;
    """)

    op.execute("""
    DROP TRIGGER IF EXISTS trg_papers_tsv_update ON papers;
    CREATE TRIGGER trg_papers_tsv_update
    BEFORE INSERT OR UPDATE OF title, abstract ON papers
    FOR EACH ROW EXECUTE FUNCTION papers_tsv_update();
    """)

    # 5) 设为 NOT NULL（已回填、已有触发器保障后续写入）
    op.alter_column("papers", "tsv", nullable=False)

    # 6) 索引（关键词检索 & 前缀/模糊）
    op.execute("CREATE INDEX IF NOT EXISTS ix_papers_tsv ON papers USING gin (tsv);")
    op.execute("""
    CREATE INDEX IF NOT EXISTS ix_papers_title_trgm
    ON papers USING gin (title gin_trgm_ops);
    """)

def downgrade():
    op.execute("DROP INDEX IF EXISTS ix_papers_title_trgm;")
    op.execute("DROP INDEX IF EXISTS ix_papers_tsv;")
    op.execute("DROP TRIGGER IF EXISTS trg_papers_tsv_update ON papers;")
    op.execute("DROP FUNCTION IF EXISTS papers_tsv_update();")
    op.drop_column("papers", "tsv")
    # 扩展一般不回滚删除