"""candidate calibration metadata

Revision ID: 20260704_0003
Revises: 20260704_0002
Create Date: 2026-07-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260704_0003"
down_revision: str | None = "20260704_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_incident_candidate_run_site_start_category",
        "incident_candidates",
        type_="unique",
    )
    op.add_column(
        "incident_candidates",
        sa.Column(
            "candidate_stage",
            sa.String(length=32),
            nullable=False,
            server_default="consolidated",
        ),
    )
    op.add_column(
        "incident_candidates",
        sa.Column("source_candidate_count", sa.Integer(), nullable=False, server_default="1"),
    )
    op.create_index(
        "ix_incident_candidates_candidate_stage",
        "incident_candidates",
        ["candidate_stage"],
    )
    op.create_unique_constraint(
        "uq_incident_candidate_run_stage_site_start_category",
        "incident_candidates",
        [
            "analysis_run_id",
            "candidate_stage",
            "site_id",
            "start_timestamp",
            "provisional_category",
        ],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_incident_candidate_run_stage_site_start_category",
        "incident_candidates",
        type_="unique",
    )
    op.drop_index("ix_incident_candidates_candidate_stage", table_name="incident_candidates")
    op.drop_column("incident_candidates", "source_candidate_count")
    op.drop_column("incident_candidates", "candidate_stage")
    op.create_unique_constraint(
        "uq_incident_candidate_run_site_start_category",
        "incident_candidates",
        ["analysis_run_id", "site_id", "start_timestamp", "provisional_category"],
    )
