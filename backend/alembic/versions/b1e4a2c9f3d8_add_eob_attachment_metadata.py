"""add_eob_attachment_metadata

Adds OCR support columns to claim_attachment and the COB coordination flag to
claim so the scrub pipeline can surface primary-EOB existence.

Revision ID: b1e4a2c9f3d8
Revises: 4867fb7c0ede
Create Date: 2026-09-14 10:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1e4a2c9f3d8"
down_revision: str | Sequence[str] | None = "4867fb7c0ede"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add doc_type/ocr_text to claim_attachment and is_secondary_claim to claim."""
    op.add_column(
        "claim_attachment",
        sa.Column("doc_type", sa.String(length=50), server_default="attachment", nullable=False),
    )
    op.add_column(
        "claim_attachment",
        sa.Column("ocr_text", sa.Text(), nullable=True),
    )
    op.add_column(
        "claim",
        sa.Column(
            "is_secondary_claim",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Drop the attachment OCR and claim COB columns."""
    op.drop_column("claim", "is_secondary_claim")
    op.drop_column("claim_attachment", "ocr_text")
    op.drop_column("claim_attachment", "doc_type")
