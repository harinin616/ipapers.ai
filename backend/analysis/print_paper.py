#!/usr/bin/env python3
import os

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker

# 导入你定义的 model
from app.models.db_models import DBPaper, Base

def main():
    # 优先从环境变量读取，否则使用默认值
    # 格式示例（Postgres）：postgresql://user:password@localhost:5432/your_db_name
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:1@localhost:5432/dlmonitor"
    )

    # 同步 engine
    engine = create_engine(DATABASE_URL, echo=False)
    # 如果你用 async engine，请改用 create_async_engine 并适配 AsyncSession

    # 确保模型都已经被 metadata 注册（可选，如果你做过 Alembic 迁移，这里无需）
    # Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)

    session = SessionLocal()
    try:
        # 执行 COUNT 查询
        total = session.query(func.count(DBPaper.paper_id)).scalar()
        print(f"📚 Database contains {total} papers")
    finally:
        session.close()


if __name__ == "__main__":
    main()
