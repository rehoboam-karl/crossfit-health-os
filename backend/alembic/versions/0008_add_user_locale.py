"""0008 add user.locale

Revision ID: 0008add_user_locale
Revises: 8f1a3b2c4d5e
Create Date: 2026-04-25 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008add_user_locale"
down_revision: Union[str, None] = "8f1a3b2c4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("locale", sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "locale")
