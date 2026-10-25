"""add user avatar

Revision ID: b2c4e6a8d0f1
Revises: f807e0679a68
Create Date: 2026-10-25
"""

import sqlalchemy as sa
from alembic import op

revision = "b2c4e6a8d0f1"
down_revision = "f807e0679a68"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("avatar_path", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("avatar_path")
