"""drop share_id from shared_folders

Revision ID: f47ed5932b52
Revises: c51ddebcd104
Create Date: 2025-07-17 19:55:38.719041

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f47ed5932b52'
down_revision = 'c51ddebcd104'
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    insp = sa.inspect(conn)

    # ❶ 唯一约束
    uniq = {uc["name"] for uc in insp.get_unique_constraints("shared_folders")}
    if "uq_shared_folders_share_id" in uniq:
        op.drop_constraint(
            "uq_shared_folders_share_id",
            "shared_folders",
            type_="unique"
        )

    # ❷ 列
    cols = {col["name"] for col in insp.get_columns("shared_folders")}
    with op.batch_alter_table("shared_folders") as batch:
        if "share_id" in cols:
            batch.drop_column("share_id")


def downgrade() -> None:
    with op.batch_alter_table("shared_folders") as batch:
        batch.add_column(sa.Column("share_id", sa.String(16), nullable=True))

    op.create_unique_constraint(
        "uq_shared_folders_share_id",
        "shared_folders",
        ["share_id"]
    )