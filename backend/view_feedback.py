#!/usr/bin/env python3
# scripts/print_feedback.py

from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from textwrap import shorten

from app.models.db_models import DBFeedback  # 确保路径与项目一致

# 1) 数据库连接 URL
DATABASE_URL = "postgresql://postgres:1@localhost:5432/dlmonitor"

def main() -> None:
    # 2) 创建 Engine 与 Session
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 3) 查询并打印全部反馈
    feedbacks = (
        session.query(DBFeedback)
        .order_by(DBFeedback.created_at.desc())
        .all()
    )

    if not feedbacks:
        print("No feedback records found.")
        return

    print(f"Total feedback: {len(feedbacks)}\n")
    for fb in feedbacks:
        created = fb.created_at.strftime("%Y-%m-%d %H:%M:%S") if isinstance(fb.created_at, datetime) else fb.created_at
        question_preview = shorten(fb.question, width=60, placeholder="…")
        print(
            f"id={fb.id:<4} | time={created} | "
            f"email={fb.email or '-':<25} | "
            f"question=\"{question_preview}\""
        )

if __name__ == "__main__":
    main()