"""email verification: users.email_verified, password_resets.purpose

Revision ID: f6a8c0e2d4b5
Revises: e5f7b9d1c3a4
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op

revision = "f6a8c0e2d4b5"
down_revision = "e5f7b9d1c3a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Accounts created before verification existed count as verified.
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("email_verified", sa.Boolean(), nullable=False, server_default=sa.true()))
    with op.batch_alter_table("password_resets") as batch:
        batch.add_column(sa.Column("purpose", sa.String(length=10), nullable=False, server_default="reset"))


def downgrade() -> None:
    with op.batch_alter_table("password_resets") as batch:
        batch.drop_column("purpose")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("email_verified")
