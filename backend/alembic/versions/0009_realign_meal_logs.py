"""0009 realign meal_logs to match SQLModel schema

Production DB had meal_logs from a legacy raw-SQL bootstrap (food_name,
serving_size, user_id TEXT) that diverged from the alembic 0004 schema.
Migration 0004 was stamped as applied even though the live table never
matched it, so the columns described in app.db.models.MealLog (description,
fiber_g, foods JSONB, photo_url, ai_estimation, user_id INTEGER FK to users)
do not exist.

This migration reconciles the table: it drops the old shape and recreates
it identically to what 0004 intended. Safe because the table is empty in
production at the time this runs (verified manually before authoring).

Revision ID: 0009realign_mealogs
Revises: 0008add_user_locale
Create Date: 2026-04-25 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Text  # noqa: F401 (referenced by JSONB variant)
import sqlmodel  # noqa: F401 (AutoString lives here)
from sqlalchemy.dialects import postgresql


revision: str = "0009realign_mealogs"
down_revision: Union[str, None] = "0008add_user_locale"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLite (test env) created the table from SQLModel.metadata.create_all in
    # the conftest fixtures — drop_table fails there because the table also
    # has no FK in the test schema. checkfirst makes this idempotent.
    op.execute("DROP TABLE IF EXISTS meal_logs CASCADE")

    op.create_table(
        "meal_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("logged_at", sa.DateTime(), nullable=False),
        sa.Column("meal_type", sqlmodel.sql.sqltypes.AutoString(length=20), nullable=True),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("protein_g", sa.Float(), nullable=True),
        sa.Column("carbs_g", sa.Float(), nullable=True),
        sa.Column("fat_g", sa.Float(), nullable=True),
        sa.Column("fiber_g", sa.Float(), nullable=True),
        sa.Column(
            "foods",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=Text()), "postgresql"),
            nullable=True,
        ),
        sa.Column("photo_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("ai_estimation", sa.Boolean(), nullable=False),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_meal_logs_logged_at"), "meal_logs", ["logged_at"], unique=False)
    op.create_index(op.f("ix_meal_logs_user_id"), "meal_logs", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_meal_logs_user_id"), table_name="meal_logs")
    op.drop_index(op.f("ix_meal_logs_logged_at"), table_name="meal_logs")
    op.drop_table("meal_logs")
