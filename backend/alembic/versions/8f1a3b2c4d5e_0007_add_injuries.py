"""0007 add injuries table

Revision ID: 8f1a3b2c4d5e
Revises: c86a34d1f657
Create Date: 2026-04-25 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import Text  # noqa: F401 (referenced by JSONB variants)
import sqlmodel  # noqa: F401 (AutoString type lives here)
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '8f1a3b2c4d5e'
down_revision: Union[str, None] = 'c86a34d1f657'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'injuries',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('body_part', sqlmodel.sql.sqltypes.AutoString(length=50), nullable=False),
        sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column(
            'restriction_tags',
            sa.JSON().with_variant(postgresql.JSONB(astext_type=Text()), 'postgresql'),
            nullable=True,
        ),
        sa.Column('severity', sqlmodel.sql.sqltypes.AutoString(length=20), nullable=False),
        sa.Column('started_at', sa.Date(), nullable=False),
        sa.Column('resolved_at', sa.Date(), nullable=True),
        sa.Column('notes', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_injuries_user_id'), 'injuries', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_injuries_user_id'), table_name='injuries')
    op.drop_table('injuries')
