from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
revision = 'fda6f0203a07'
down_revision = '46f308c4a498'

# --------- 需要同步修改的依赖表 ----------
DEPENDENT_TABLES = [
    ("folders",      "CASCADE"),   # ondelete
    ("sessions",     "CASCADE"),
    ("user_topics",  "CASCADE"),
    ("feedback",     "SET NULL"),  # feedback.user_id 允许为空
]

def upgrade():
    # 0) uuid extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # 1) users.id
    op.add_column('users', sa.Column('id', postgresql.UUID(as_uuid=True)))
    op.execute('UPDATE users SET id = uuid_generate_v4() WHERE id IS NULL')
    op.alter_column('users', 'id', nullable=False)

    # 2) 换主键（CASCADE 会自动删掉旧的 *_user_id_fkey 外键）
    op.execute('ALTER TABLE users DROP CONSTRAINT users_pkey CASCADE')
    op.create_primary_key('users_pkey', 'users', ['id'])

    # 3) 依赖表加列并回填
    dependents = ['folders', 'sessions', 'user_topics', 'feedback']
    for t in dependents:
        op.add_column(t, sa.Column('user_uuid', postgresql.UUID(as_uuid=True)))

    op.execute("""UPDATE folders   f SET user_uuid = u.id FROM users u WHERE f.user_id = u.user_id""")
    op.execute("""UPDATE sessions  s SET user_uuid = u.id FROM users u WHERE s.user_id = u.user_id""")
    op.execute("""UPDATE user_topics ut SET user_uuid = u.id FROM users u WHERE ut.user_id = u.user_id""")
    op.execute("""UPDATE feedback  fb SET user_uuid = u.id FROM users u WHERE fb.user_id = u.user_id""")

    # 4) 建新外键
    op.alter_column('folders',      'user_uuid', nullable=False)
    op.create_foreign_key('folders_user_uuid_fkey',  'folders',      'users', ['user_uuid'], ['id'], ondelete='CASCADE')

    op.alter_column('sessions',     'user_uuid', nullable=False)
    op.create_foreign_key('sessions_user_uuid_fkey', 'sessions',     'users', ['user_uuid'], ['id'], ondelete='CASCADE')

    op.alter_column('user_topics',  'user_uuid', nullable=False)
    op.create_foreign_key('user_topics_user_uuid_fkey', 'user_topics', 'users', ['user_uuid'], ['id'], ondelete='CASCADE')

    # feedback 可以 NULL
    op.create_foreign_key('feedback_user_uuid_fkey', 'feedback', 'users', ['user_uuid'], ['id'], ondelete='SET NULL')

    # 5) 删旧列
    for t in dependents:
        op.drop_column(t, 'user_id')
        op.alter_column(t, 'user_uuid', new_column_name='user_id')


def downgrade() -> None:
    """简易回滚：**只**恢复结构，不再拆回旧外键"""
    # 如果需要完整降级，可反向写 1 → 5 的逆操作
    raise NotImplementedError("Downgrade not supported for UUID PK migration")
