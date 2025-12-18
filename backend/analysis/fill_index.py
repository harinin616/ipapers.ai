# fill_index.py
#
# 离线分批回填 papers.search_text = title || ' ' || abstract
# 同步版本，用 psycopg2 驱动即可，适合 900w+ 行，随时停随时续。

import os
from sqlalchemy import create_engine, text

# TODO：换成你实际用的数据库 URL，或者从你的 config / settings 里 import
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:yourpass@localhost:5432/dlmonitor",
)

BATCH_SIZE = 2000  # 每批 2w 行，可按机器性能调


def main():
    print("Using DATABASE_URL:", DATABASE_URL)

    # future=True 用的是 2.0 style，跟你项目其它部分兼容
    engine = create_engine(DATABASE_URL, future=True)

    # 先看一下还有多少是 NULL（可选）
    with engine.connect() as conn:
        res = conn.execute(
            text("SELECT COUNT(*) FROM papers WHERE search_text IS NULL")
        )
        remaining = res.scalar_one()
        print("Initial remaining rows with search_text IS NULL:", remaining)

    total_updated = 0

    while True:
        # 每一批用一个小事务：begin() 语义等价于 "with engine.begin() as conn:"
        with engine.begin() as conn:
            res = conn.execute(
                text(
                    """
                    WITH to_update AS (
                        SELECT paper_id, platform
                        FROM papers
                        WHERE search_text IS NULL
                        ORDER BY paper_id
                        LIMIT :batch
                    )
                    UPDATE papers p
                    SET search_text =
                        COALESCE(p.title, '') || ' ' || COALESCE(p.abstract, '')
                    FROM to_update u
                    WHERE p.paper_id = u.paper_id
                      AND p.platform = u.platform
                    RETURNING 1
                    """
                ),
                {"batch": BATCH_SIZE},
            )

            updated = res.rowcount or 0

        if updated == 0:
            print("No more rows to update. Backfill finished.")
            break

        total_updated += updated
        remaining -= updated
        print(
            f"Updated {updated} rows in this batch, "
            f"total_updated={total_updated}, approx remaining={max(remaining, 0)}"
        )

    # 关掉连接池（可选）
    engine.dispose()
    print("Done.")


if __name__ == "__main__":
    main()
