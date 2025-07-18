"""add shared_folders table

Revision ID: 38d284a58e51
Revises: a2c18246d03b
Create Date: 2025-07-17 17:37:36.616551

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '38d284a58e51'
down_revision = 'a2c18246d03b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shared_folders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("share_id", sa.String(length=16), nullable=False),
        sa.Column("folder_id", sa.Integer(),
                  sa.ForeignKey("folders.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("owner_id", postgresql.UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"),
                  nullable=False),
        sa.Column("is_public", sa.Boolean(),
                  server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_shared_folders_share_id",
                    "shared_folders", ["share_id"], unique=True)
    op.create_index("ix_shared_folders_owner_created",
                    "shared_folders", ["owner_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_shared_folders_owner_created",
                  table_name="shared_folders")
    op.drop_index("ix_shared_folders_share_id",
                  table_name="shared_folders")
    op.drop_table("shared_folders")
