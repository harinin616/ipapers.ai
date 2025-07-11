#!/usr/bin/env python3
# print_users_folders_files.py
"""
列出数据库中全部用户 → 文件夹 → 文件（论文）层级信息
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, selectinload
from app.models.db_models import DBUser, DBFolder, DBUserFile, DBPaper

# ---------- 1. 你的数据库连接 ----------
DATABASE_URL = "postgresql://postgres:1@localhost:5432/dlmonitor"

def main():
    # ---------- 2. 建立会话 ----------
    engine  = create_engine(DATABASE_URL, echo=False, future=True)
    Session = sessionmaker(bind=engine)
    session = Session()

    # ---------- 3. 查询用户及其 folders -> files -> papers ----------
    users = (
        session.query(DBUser)
        .options(
            selectinload(DBUser.folders)            # 预加载 folders
            .selectinload(DBFolder.files)           # 预加载 files
            .selectinload(DBUserFile.paper)         # 再预加载 paper
        )
        .order_by(DBUser.user_id)
        .all()
    )

    for u in users:
        print(f"=== User {u.user_id} | {u.name} <{u.email}> ===")

        if not u.folders:
            print("  (no folders)")
            continue

        # 按创建时间 / 名称排序即可
        for f in sorted(u.folders, key=lambda x: (x.created_at, x.name)):
            print(f"  └─ Folder {f.id} | {f.name!r} | created_at={f.created_at}")

            if not f.files:
                print("      (empty)")
                continue

            for uf in sorted(f.files, key=lambda x: x.added_at):
                p: DBPaper = uf.paper
                print(f"      • {p.paper_id} | {p.title[:70]}… | added_at={uf.added_at}")

    session.close()

if __name__ == "__main__":
    main()
