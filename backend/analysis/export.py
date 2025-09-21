#!/usr/bin/env python3
# export_papers_stream.py
#
#   ▶ python export_papers_stream.py \
#         --db-url postgresql://user:pwd@host:5432/dbname \
#         --out ~/papers.jsonl \
#         --public-only \
#         --since 2023-01-01
# ----------------------------------------------------------

import json
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker, selectinload

# ⇩⇩ 换成你真实的 models 路径
from app.models.db_models import DBPaper

DEFAULT_DB_URL = "postgresql://postgres:1@localhost:5432/dlmonitor"
BATCH_SIZE     = 2_000                   # 每批导出的行数

# ----------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Incrementally dump papers (authors/categories) to JSONL"
    )
    p.add_argument("--db-url", default=DEFAULT_DB_URL,
                   help=f"SQLAlchemy DSN (default {DEFAULT_DB_URL!r})")
    p.add_argument("-o", "--out", default="papers_export.jsonl",
                   help="输出文件，默认 ./papers_export.jsonl")
    p.add_argument("--public-only", action="store_true",
                   help="仅导出 is_public = true 的记录")
    p.add_argument("--since", metavar="YYYY-MM-DD",
                   help="仅导出 updated_date ≥ since 的记录")
    return p

# ----------------------------------------------------------
def page_query(base_stmt, pk_field, last_pk: Optional[str]):
    """给定基础 stmt + 上一批最后一个主键，返回下一页 stmt"""
    stmt = base_stmt
    if last_pk is not None:
        stmt = stmt.where(pk_field > last_pk)
    return stmt.order_by(pk_field).limit(BATCH_SIZE)

# ----------------------------------------------------------
def main() -> None:
    args   = build_parser().parse_args()
    engine = create_engine(args.db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 基础查询（不带分页）
    base_stmt = (
        select(DBPaper)
        .options(
            selectinload(DBPaper.authors),
            selectinload(DBPaper.categories)
        )
    )
    if args.public_only:
        base_stmt = base_stmt.where(DBPaper.is_public.is_(True))
    if args.since:
        since_dt = datetime.strptime(args.since, "%Y-%m-%d")
        base_stmt = base_stmt.where(DBPaper.updated_date >= since_dt)

    out_path = Path(args.out).expanduser().resolve()
    total    = 0
    last_pk  = None            # 记录“上一批最后一条”的主键

    with out_path.open("w", encoding="utf-8") as fw:
        while True:
            stmt = page_query(base_stmt, DBPaper.paper_id, last_pk)
            rows = session.execute(stmt).scalars().all()   # 最多 BATCH_SIZE 行

            if not rows:       # 没有更多数据 ➜ 结束
                break

            for paper in rows:
                total += 1
                rec = {
                    "paper_id"  : paper.paper_id,
                    "title"     : paper.title,
                    "abstract"  : paper.abstract,
                    "pdf_url"   : paper.pdf_url,
                    "published" : paper.published_date.isoformat() if paper.published_date else None,
                    "updated"   : paper.updated_date.isoformat()   if paper.updated_date   else None,
                    "is_public" : paper.is_public,
                    "authors"   : [a.name for a in paper.authors],
                    "categories": [c.name for c in paper.categories],
                }
                fw.write(json.dumps(rec, ensure_ascii=False) + "\n")

            # 记住这批最后一条的主键，下次 > 它 继续
            last_pk = rows[-1].paper_id

            # 清空 identity-map，释放内存
            session.expunge_all()

    print(f"✅ 导出完成：{total} 条 → {out_path}")

# ----------------------------------------------------------
if __name__ == "__main__":
    main()
