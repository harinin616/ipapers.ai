#!/usr/bin/env python3
import os
import sys
from typing import Optional

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
import random

DEFAULT_URL = "postgresql://postgres:1@localhost:5432/dlmonitor"

PAPERS_TABLE = "papers"
REQUIRED_EXTENSIONS = ["pg_trgm", "unaccent"]          # 如有向量，下面 OPTIONAL_EXT 中也会查
OPTIONAL_EXTENSIONS = ["vector"]

REQUIRED_INDEXES = [
    # name, table, note
    ("ix_papers_tsv", PAPERS_TABLE, "GIN(tsv) for keyword search"),
    ("ix_papers_title_trgm", PAPERS_TABLE, "GIN(title gin_trgm_ops) for prefix/fuzzy"),
]

OPTIONAL_INDEXES = [
    ("ix_papers_embedding_ivfflat", PAPERS_TABLE, "pgvector ANN (ivfflat)"),
]

TRIGGER_NAME = "trg_papers_tsv_update"
TRIGGER_FUNC = "papers_tsv_update"


def connect() -> Engine:
    url = os.getenv("DATABASE_URL", DEFAULT_URL)
    engine = create_engine(url, echo=False, future=True)
    return engine


def one(engine: Engine, sql: str, **params) -> Optional[tuple]:
    with engine.connect() as conn:
        row = conn.execute(text(sql), params).fetchone()
        return row


def exists_extension(engine: Engine, ext: str) -> bool:
    row = one(engine, "SELECT 1 FROM pg_extension WHERE extname=:e", e=ext)
    return bool(row)


def papers_has_tsvector(engine: Engine) -> bool:
    row = one(
        engine,
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = :t
          AND column_name = 'tsv'
          AND udt_name = 'tsvector'
        """,
        t=PAPERS_TABLE,
    )
    return bool(row)


def exists_trigger(engine: Engine, table: str, trigger: str) -> bool:
    row = one(
        engine,
        """
        SELECT 1
        FROM pg_trigger tg
        JOIN pg_class c ON c.oid = tg.tgrelid
        WHERE NOT tg.tgisinternal
          AND c.relname = :t
          AND tg.tgname = :g
        """,
        t=table, g=trigger
    )
    return bool(row)


def exists_func(engine: Engine, func: str) -> bool:
    # 函数可能有 schema，这里不限定参数签名，只按名字匹配
    row = one(
        engine,
        """
        SELECT 1
        FROM pg_proc p
        JOIN pg_namespace n ON n.oid = p.pronamespace
        WHERE p.proname = :f
        """,
        f=func
    )
    return bool(row)


def index_info(engine: Engine, index_name: str) -> Optional[dict]:
    sql = """
    SELECT
      c.relname AS index_name,
      i.indisvalid,
      i.indisready,
      pg_size_pretty(pg_relation_size(c.oid)) AS idx_size,
      s.idx_scan,
      s.idx_tup_read,
      s.idx_tup_fetch
    FROM pg_class c
    JOIN pg_index i ON i.indexrelid = c.oid
    LEFT JOIN pg_stat_user_indexes s ON s.indexrelname = c.relname
    WHERE c.relname = :n
    """
    with engine.connect() as conn:
        row = conn.execute(text(sql), {"n": index_name}).mappings().fetchone()
        return dict(row) if row else None


def print_status(ok: bool, label: str, extra: str = ""):
    mark = "✅" if ok else "❌"
    if extra:
        print(f"{mark} {label} — {extra}")
    else:
        print(f"{mark} {label}")


def main():
    engine = connect()

    print("== Extensions ==")
    for ext in REQUIRED_EXTENSIONS:
        print_status(exists_extension(engine, ext), f"{ext} (required)")
    for ext in OPTIONAL_EXTENSIONS:
        print_status(exists_extension(engine, ext), f"{ext} (optional)")

    print("\n== Column ==")
    print_status(papers_has_tsvector(engine), f"{PAPERS_TABLE}.tsv :: tsvector")

    print("\n== Trigger & Function ==")
    print_status(exists_func(engine, TRIGGER_FUNC), f"function {TRIGGER_FUNC}()")
    print_status(exists_trigger(engine, PAPERS_TABLE, TRIGGER_NAME), f"trigger {TRIGGER_NAME} on {PAPERS_TABLE}")

    print("\n== Indexes ==")
    all_ok = True
    for name, table, note in REQUIRED_INDEXES:
        info = index_info(engine, name)
        if info:
            ok = bool(info["indisvalid"]) and bool(info["indisready"])
            all_ok = all_ok and ok
            extra = f"{note}; size={info['idx_size']}; scans={info['idx_scan']}"
            print_status(ok, f"{name} on {table}", extra)
        else:
            all_ok = False
            print_status(False, f"{name} on {table}")

    # 可选的向量索引
    for name, table, note in OPTIONAL_INDEXES:
        info = index_info(engine, name)
        if info:
            ok = bool(info["indisvalid"]) and bool(info["indisready"])
            extra = f"{note}; size={info['idx_size']}; scans={info['idx_scan']}"
            print_status(ok, f"{name} on {table}", extra)
        else:
            print_status(False, f"{name} on {table} (optional)")

    # 额外：跑一条 EXPLAIN 看看查询是否能用上 GIN(tsv)
    print("\n== Explain (should use GIN on tsv) ==")
    explain_sql = text("""
        EXPLAIN (COSTS false)
        SELECT paper_id
        FROM papers
        WHERE tsv @@ websearch_to_tsquery('simple', :q)
        LIMIT 10
    """)
    with engine.connect() as conn:
        plan = [r[0] for r in conn.execute(explain_sql, {"q": "graph ranking"}).fetchall()]
        for line in plan:
            print("  ", line)

    # 退出码：所有必需对象都 OK 才返回 0
    if not (papers_has_tsvector(engine)
            and all(exists_extension(engine, e) for e in REQUIRED_EXTENSIONS)
            and exists_func(engine, TRIGGER_FUNC)
            and exists_trigger(engine, PAPERS_TABLE, TRIGGER_NAME)
            and all(index_info(engine, n) and index_info(engine, n)["indisvalid"] and index_info(engine, n)["indisready"]
                    for n, _, _ in REQUIRED_INDEXES)
            ):
        print("\nSome required objects are missing or not ready.", file=sys.stderr)
        sys.exit(2)

    print("\nAll required FTS objects are present and ready. 🎉")
    print("\n== Sample Query Test (20 random keywords) ==")
# 从 papers 表里随机取 20 条 title 作为查询词  
    with engine.connect() as conn:
        titles = [r[0] for r in conn.execute(text(f"""
            SELECT title FROM {PAPERS_TABLE}
            TABLESAMPLE SYSTEM (1) -- 随机取样1%的数据
            LIMIT 20
        """))]

        for q in titles:
            plan = [r[0] for r in conn.execute(
                text(f"""
                    EXPLAIN (COSTS false)
                    SELECT paper_id
                    FROM {PAPERS_TABLE}
                    WHERE tsv @@ websearch_to_tsquery('simple', :q)
                    LIMIT 10
                """),
                {"q": q}
            )]
            hit_index = any("Bitmap Index Scan" in line or "Index Scan" in line for line in plan)
            mark = "✅" if hit_index else "❌"
            print(f"{mark} Query: {q!r} -> Index used? {hit_index}")


if __name__ == "__main__":
    main()