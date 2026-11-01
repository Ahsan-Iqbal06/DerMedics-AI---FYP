"""add user phone

Revision ID: d4e6a8c0b2f3
Revises: c3d5f7a9b1e2
Create Date: 2026-10-31
"""

import sqlalchemy as sa
from alembic import op

revision = "d4e6a8c0b2f3"
down_revision = "c3d5f7a9b1e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("phone", sa.String(length=20), nullable=False, server_default=""))


def downgrade() -> None:
    with op.batch_alter_table("users") as batch:
        batch.drop_column("phone")
