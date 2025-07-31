#!/usr/bin/env python3
# print_allowed_users.py
#
# 打印 shared_folders.allowed_user_ids
# 可选：解析为邮箱一起展示

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.models.db_models import DBSharedFolder, DBUser   # 根据你的项目路径调整
from uuid import UUID

# 1) 数据库连接 URL（改成你的）
DATABASE_URL = "postgresql://postgres:1@localhost:5432/dlmonitor"

def main():
    # 2) 建立会话
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 3) 查询所有共享文件夹
    folders = session.query(DBSharedFolder).all()

    print(f"共有 {len(folders)} 个 shared_folders\n" + "-" * 60)
    for sf in folders:
        # ① 基本信息
        folder_line = (
            f"folder_id={sf.folder_id:<4} | is_public={sf.is_public:<5} | "
            f"allowed_user_ids={sf.allowed_user_ids}"
        )
        print(folder_line)

        # ② 如果想把 UUID → email，再查一次用户表
        if sf.allowed_user_ids:
            users = (
                session.query(DBUser)
                .filter(DBUser.id.in_(sf.allowed_user_ids))
                .all()
            )
            emails = [u.email for u in users]
            print(f"     ↳ emails={emails}")

    print("-" * 60)

if __name__ == "__main__":
    main()
