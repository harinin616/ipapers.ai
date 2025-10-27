"""paper counters (O(1) exact count)

Revision ID: 61643ad622c3
Revises: f1c2e2c3e061
Create Date: 2025-10-27 18:33:14.331431

"""

"""paper counters (O(1) exact total_count)"""
from alembic import op

revision = '61643ad622c3'
down_revision = 'f1c2e2c3e061'


branch_labels = None
depends_on = None

def upgrade():
    op.execute("""
    -- 1) 计数表
    CREATE TABLE IF NOT EXISTS public.paper_counters (
      id           integer PRIMARY KEY DEFAULT 1,
      total_count  bigint  NOT NULL DEFAULT 0
    );

    -- 2) 初始化
    INSERT INTO public.paper_counters(id, total_count)
    VALUES (1, (SELECT COUNT(*)::bigint FROM public.papers))
    ON CONFLICT (id) DO UPDATE
      SET total_count = EXCLUDED.total_count;

    -- 3) 触发器函数（行级 + truncate 语义）
    CREATE OR REPLACE FUNCTION public._papers_total_count_trg()
    RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF TG_OP = 'INSERT' THEN
        UPDATE public.paper_counters SET total_count = total_count + 1 WHERE id = 1;
        RETURN NEW;
      ELSIF TG_OP = 'DELETE' THEN
        UPDATE public.paper_counters SET total_count = total_count - 1 WHERE id = 1;
        RETURN OLD;
      ELSIF TG_OP = 'TRUNCATE' THEN
        UPDATE public.paper_counters SET total_count = 0 WHERE id = 1;
        RETURN NULL;
      ELSE
        RETURN NEW;
      END IF;
    END$$;

    -- 4) 行级触发器（插入/删除）
    DROP TRIGGER IF EXISTS papers_total_count_aiud ON public.papers;
    CREATE TRIGGER papers_total_count_aiud
      AFTER INSERT OR DELETE ON public.papers
      FOR EACH ROW
      EXECUTE FUNCTION public._papers_total_count_trg();

    -- 5) 语句级 TRUNCATE 触发器
    DROP TRIGGER IF EXISTS papers_total_count_truncate ON public.papers;
    CREATE TRIGGER papers_total_count_truncate
      AFTER TRUNCATE ON public.papers
      FOR EACH STATEMENT
      EXECUTE FUNCTION public._papers_total_count_trg();
    """)

def downgrade():
    op.execute("""
    DROP TRIGGER IF EXISTS papers_total_count_truncate ON public.papers;
    DROP TRIGGER IF EXISTS papers_total_count_aiud ON public.papers;
    DROP FUNCTION IF EXISTS public._papers_total_count_trg();
    DROP TABLE IF EXISTS public.paper_counters;
    """)
