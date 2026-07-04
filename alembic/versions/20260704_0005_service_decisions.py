"""explainable service decisions

Revision ID: 20260704_0005
Revises: 20260704_0004
Create Date: 2026-07-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260704_0005"
down_revision: str | None = "20260704_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "service_decisions",
        sa.Column("decision_id", sa.String(length=96), primary_key=True),
        sa.Column(
            "analysis_run_id",
            sa.String(length=64),
            sa.ForeignKey("analysis_runs.analysis_run_id"),
            nullable=False,
        ),
        sa.Column(
            "incident_candidate_id",
            sa.String(length=96),
            sa.ForeignKey("incident_candidates.incident_candidate_id"),
            nullable=False,
        ),
        sa.Column("site_id", sa.String(length=16), sa.ForeignKey("sites.site_id"), nullable=False),
        sa.Column("probable_issue", sa.String(length=128), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("confidence_label", sa.String(length=32), nullable=False),
        sa.Column("supporting_evidence", sa.JSON(), nullable=False),
        sa.Column("contradictory_evidence", sa.JSON(), nullable=False),
        sa.Column("confidence_components", sa.JSON(), nullable=False),
        sa.Column("expected_energy_kwh", sa.Float(), nullable=False),
        sa.Column("actual_energy_kwh", sa.Float(), nullable=True),
        sa.Column("estimated_energy_loss_kwh", sa.Float(), nullable=False),
        sa.Column("estimated_value_at_risk_inr", sa.Float(), nullable=False),
        sa.Column("projected_seven_day_loss_kwh", sa.Float(), nullable=False),
        sa.Column("estimated_recoverable_energy_kwh", sa.Float(), nullable=False),
        sa.Column("estimated_recoverable_value_inr", sa.Float(), nullable=False),
        sa.Column("tariff_per_kwh", sa.Float(), nullable=False),
        sa.Column("visit_cost_inr", sa.Float(), nullable=False),
        sa.Column("cleaning_cost_inr", sa.Float(), nullable=False),
        sa.Column("cleaning_decision", sa.String(length=32), nullable=False),
        sa.Column("cleaning_reason", sa.Text(), nullable=False),
        sa.Column("recommended_action", sa.String(length=64), nullable=False),
        sa.Column("action_reason", sa.Text(), nullable=False),
        sa.Column("prerequisite_remote_checks", sa.JSON(), nullable=False),
        sa.Column("escalation_condition", sa.Text(), nullable=False),
        sa.Column("remote_action_available", sa.Boolean(), nullable=False),
        sa.Column("visit_required", sa.Boolean(), nullable=False),
        sa.Column("actionable", sa.Boolean(), nullable=False),
        sa.Column("complaint_severity", sa.String(length=32), nullable=False),
        sa.Column("sla_status", sa.String(length=32), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=False),
        sa.Column("priority_label", sa.String(length=32), nullable=False),
        sa.Column("priority_components", sa.JSON(), nullable=False),
        sa.Column("queue_rank", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "analysis_run_id",
            "incident_candidate_id",
            name="uq_service_decision_run_candidate",
        ),
    )
    op.create_index("ix_service_decisions_run", "service_decisions", ["analysis_run_id"])
    op.create_index("ix_service_decisions_site", "service_decisions", ["site_id"])
    op.create_index("ix_service_decisions_priority", "service_decisions", ["priority_score"])
    op.create_index("ix_service_decisions_actionable", "service_decisions", ["actionable"])


def downgrade() -> None:
    op.drop_table("service_decisions")
