#!/usr/bin/env python3
# update_user.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
from app.models.db_models import DBUser  # 你项目里的用户模型

# 修改为你的数据库连接串
DATABASE_URL = "postgresql://postgres:yourpass@localhost:5432/dlmonitor"

TARGET_LEGACY_ID = 1
NEW_NAME = "Pinhuan Wang"
NEW_EMAIL = "ph.joey.wong@gmail.com"


def main():
    engine = create_engine(DATABASE_URL, echo=False, future=True)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = Session()

    try:
        user = session.query(DBUser).filter(DBUser.legacy_user_id == TARGET_LEGACY_ID).one_or_none()
        if user is None:
            print(f"[WARN] 没找到 legacy_user_id={TARGET_LEGACY_ID} 的用户。")
            return

        print(f"[BEFORE] id={user.id} | legacy_user_id={user.legacy_user_id} | "
              f"name={user.name!r} | email={user.email!r}")

        user.name = NEW_NAME
        user.email = NEW_EMAIL

        session.commit()
        session.refresh(user)

        print(f"[AFTER ] id={user.id} | legacy_user_id={user.legacy_user_id} | "
              f"name={user.name!r} | email={user.email!r}")
        print("[OK] 更新完成。")

    except IntegrityError as e:
        session.rollback()
        print("[ERROR] 提交失败，可能撞到唯一键（例如 email 已被占用）。具体：")
        print(e.orig)
    except Exception as e:
        session.rollback()
        print("[ERROR] 未预期的异常：", repr(e))
    finally:
        session.close()


if __name__ == "__main__":
    main()
