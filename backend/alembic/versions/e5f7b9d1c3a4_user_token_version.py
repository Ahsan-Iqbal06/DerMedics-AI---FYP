"""add user token_version

Revision ID: e5f7b9d1c3a4
Revises: d4e6a8c0b2f3
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op

revision = "e5f7b9d1c3a4"
down_revision = "d4e6a8c0b2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("token_version", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("token_version")
