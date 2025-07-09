#!/usr/bin/env python3
# print_users.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.db_models import DBUser

# 1) 用字符串保存你的数据库连接 URL
DATABASE_URL = 'postgresql://postgres:1@localhost:5432/dlmonitor'

def main():
    # 2) 用字符串创建 Engine
    engine = create_engine(DATABASE_URL, echo=False)
    Session = sessionmaker(bind=engine)
    session = Session()

    # 3) 查询并打印所有用户
    users = session.query(DBUser).all()
    for u in users:
        print(f"user_id={u.user_id} | name={u.name!r} | email={u.email!r}| subscribed={u.subscribed}")

if __name__ == "__main__":
    main()
