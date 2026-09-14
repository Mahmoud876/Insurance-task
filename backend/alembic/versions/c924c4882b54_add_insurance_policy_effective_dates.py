"""add_insurance_policy_effective_dates

Revision ID: c924c4882b54
Revises: a5b5d79f04a3
Create Date: 2026-09-13 16:55:28.361617

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c924c4882b54'
down_revision: Union[str, Sequence[str], None] = 'a5b5d79f04a3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add policy effective/termination dates required by InsurancePolicy model."""
    op.add_column(
        "insurance_policy",
        sa.Column("effective_date", sa.Date(), nullable=True),
    )
    op.add_column(
        "insurance_policy",
        sa.Column("termination_date", sa.Date(), nullable=True),
    )
    op.execute(
        "UPDATE insurance_policy SET effective_date = created_at::date "
        "WHERE effective_date IS NULL;"
    )
    op.alter_column("insurance_policy", "effective_date", nullable=False)
    op.create_index(
        op.f("ix_insurance_policy_effective_date"),
        "insurance_policy",
        ["effective_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_insurance_policy_termination_date"),
        "insurance_policy",
        ["termination_date"],
        unique=False,
    )


def downgrade() -> None:
    """Drop policy effective/termination date columns."""
    op.drop_index(op.f("ix_insurance_policy_termination_date"), table_name="insurance_policy")
    op.drop_index(op.f("ix_insurance_policy_effective_date"), table_name="insurance_policy")
    op.drop_column("insurance_policy", "termination_date")
    op.drop_column("insurance_policy", "effective_date")
