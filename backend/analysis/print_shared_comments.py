# print_shared_folders.py
import asyncio
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import sessionmaker, selectinload

# ---- 0. 你的模型 ----
# 假设全部模型都在 models.py
#   Base,
#   DBSharedFolder, DBComment
from app.models.db_models import (
    DBUser, DBPaper, DBAuthor, DBCategory, DBFolder, DBUserFile,
    DBUserTopic, DBSession, DBMessage, PageViewDaily, DBFeedback,
    DBEmailList, DBSharedFolder, Base
)

DATABASE_URL = "postgresql+asyncpg://postgres:1@localhost:5432/dlmonitor"

# ---- 1. 建立异步 Engine / Session ----
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ---- 2. 主逻辑 ----
async def main() -> None:
    async with AsyncSessionLocal() as session:
        # 预加载 comments，避免懒加载触发 MissingGreenletError
        stmt = (
            select(DBSharedFolder)
            .options(selectinload(DBSharedFolder.comments))
            .order_by(DBSharedFolder.id)
        )
        result = await session.execute(stmt)
        shared_folders = result.scalars().all()

        if not shared_folders:
            print("⚠️  数据库里暂时没有 shared_folders 记录")
            return

        for sf in shared_folders:
            print(f"\nShare#{sf.id}  =>  Folder {sf.folder_id}")
            print(f"  Owner: {sf.owner_id}   Public: {sf.is_public}")
            print(f"  Created at: {sf.created_at.isoformat()}")

            if not sf.comments:
                print("  (No comments)")
                continue

            for c in sf.comments:
                preview = (c.content[:60] + "…") if len(c.content) > 60 else c.content
                print(
                    f"    • Comment#{c.id}  by {c.commenter_name or '(anonymous)'}"
                    f"  @ {c.created_at.isoformat()}\n"
                    f"      {preview}"
                )

# ---- 3. 入口 ----
if __name__ == "__main__":
    asyncio.run(main())