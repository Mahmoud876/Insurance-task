"""add member_id_encryption to insurance_policy

Revision ID: 4867fb7c0ede
Revises: c924c4882b54
Create Date: 2026-09-13 21:23:12.660164

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '4867fb7c0ede'
down_revision: Union[str, Sequence[str], None] = 'c924c4882b54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('insurance_policy', sa.Column('member_id_enc', sa.LargeBinary(), nullable=True))
    op.add_column('insurance_policy', sa.Column('member_id_last4', sa.String(length=10), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('insurance_policy', 'member_id_last4')
    op.drop_column('insurance_policy', 'member_id_enc')