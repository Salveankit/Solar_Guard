"""candidate quality output contract

Revision ID: 20260704_0004
Revises: 20260704_0003
Create Date: 2026-07-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260704_0004"
down_revision: str | None = "20260704_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "incident_candidates",
        sa.Column("secondary_evidence", sa.JSON(), nullable=True),
    )
    op.add_column(
        "incident_candidates",
        sa.Column(
            "operational_qualification_status",
            sa.String(length=32),
            nullable=False,
            server_default="qualified",
        ),
    )
    op.add_column(
        "incident_candidates",
        sa.Column("actionable", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index(
        "ix_incident_candidates_actionable",
        "incident_candidates",
        ["actionable"],
    )


def downgrade() -> None:
    op.drop_index("ix_incident_candidates_actionable", table_name="incident_candidates")
    op.drop_column("incident_candidates", "actionable")
    op.drop_column("incident_candidates", "operational_qualification_status")
    op.drop_column("incident_candidates", "secondary_evidence")
