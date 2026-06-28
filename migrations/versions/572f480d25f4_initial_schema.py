"""initial schema

Revision ID: 572f480d25f4
Revises: 
Create Date: 2026-06-28 19:21:30.265509

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '572f480d25f4'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('transactions') as batch_op:
        batch_op.alter_column('ingested_at',
            existing_type=sa.DATE(),
            type_=sa.DateTime(),
            existing_nullable=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    with op.batch_alter_table('transactions') as batch_op:
        batch_op.alter_column('ingested_at',
            existing_type=sa.DateTime(),
            type_=sa.DATE(),
            existing_nullable=False)
    # ### end Alembic commands ###
