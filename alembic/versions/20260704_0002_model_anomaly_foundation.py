"""model evaluation and anomaly candidate foundation

Revision ID: 20260704_0002
Revises: 20260704_0001
Create Date: 2026-07-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260704_0002"
down_revision: str | None = "20260704_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "expected_generation_results",
        sa.Column("model_run_id", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "expected_generation_results",
        sa.Column(
            "predictor_type",
            sa.String(length=32),
            nullable=False,
            server_default="baseline",
        ),
    )
    op.add_column(
        "expected_generation_results",
        sa.Column("signed_residual_kwh", sa.Float(), nullable=True),
    )
    op.add_column(
        "expected_generation_results",
        sa.Column("energy_loss_kwh", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "expected_generation_results",
        sa.Column("performance_ratio", sa.Float(), nullable=True),
    )
    op.add_column(
        "expected_generation_results",
        sa.Column("solar_elevation_degree", sa.Float(), nullable=True),
    )
    op.add_column(
        "expected_generation_results",
        sa.Column(
            "data_quality_status",
            sa.String(length=32),
            nullable=False,
            server_default="GOOD",
        ),
    )
    op.add_column(
        "expected_generation_results",
        sa.Column("anomaly_eligible", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "expected_generation_results",
        sa.Column(
            "anomaly_state",
            sa.String(length=64),
            nullable=False,
            server_default="ineligible",
        ),
    )
    op.create_index(
        "ix_expected_generation_results_model_run_id",
        "expected_generation_results",
        ["model_run_id"],
    )
    op.create_index(
        "ix_expected_generation_results_anomaly_state",
        "expected_generation_results",
        ["anomaly_state"],
    )

    op.create_table(
        "expected_model_runs",
        sa.Column("model_run_id", sa.String(length=64), primary_key=True),
        sa.Column("predictor_type", sa.String(length=32), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("promotion_decision", sa.String(length=64), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
    )
    op.create_index(
        "ix_expected_model_runs_predictor_type",
        "expected_model_runs",
        ["predictor_type"],
    )
    op.create_index(
        "ix_expected_model_runs_model_version",
        "expected_model_runs",
        ["model_version"],
    )

    op.create_table(
        "incident_candidates",
        sa.Column("incident_candidate_id", sa.String(length=96), primary_key=True),
        sa.Column(
            "analysis_run_id",
            sa.String(length=64),
            sa.ForeignKey("analysis_runs.analysis_run_id"),
            nullable=False,
        ),
        sa.Column("site_id", sa.String(length=16), sa.ForeignKey("sites.site_id"), nullable=False),
        sa.Column("start_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval_count", sa.Integer(), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("expected_energy_kwh", sa.Float(), nullable=False),
        sa.Column("actual_energy_kwh", sa.Float(), nullable=True),
        sa.Column("total_energy_loss_kwh", sa.Float(), nullable=False),
        sa.Column("average_performance_ratio", sa.Float(), nullable=True),
        sa.Column("minimum_performance_ratio", sa.Float(), nullable=True),
        sa.Column("anomaly_state", sa.String(length=64), nullable=False),
        sa.Column("dominant_evidence", sa.JSON(), nullable=True),
        sa.Column("data_completeness", sa.Float(), nullable=False),
        sa.Column("provisional_category", sa.String(length=96), nullable=False),
        sa.Column("preliminary_recommendation", sa.String(length=128), nullable=True),
        sa.UniqueConstraint(
            "analysis_run_id",
            "site_id",
            "start_timestamp",
            "provisional_category",
            name="uq_incident_candidate_run_site_start_category",
        ),
    )
    op.create_index(
        "ix_incident_candidates_analysis_run_id",
        "incident_candidates",
        ["analysis_run_id"],
    )
    op.create_index("ix_incident_candidates_site_id", "incident_candidates", ["site_id"])
    op.create_index(
        "ix_incident_candidates_start_timestamp",
        "incident_candidates",
        ["start_timestamp"],
    )
    op.create_index(
        "ix_incident_candidates_end_timestamp",
        "incident_candidates",
        ["end_timestamp"],
    )
    op.create_index(
        "ix_incident_candidates_provisional_category",
        "incident_candidates",
        ["provisional_category"],
    )


def downgrade() -> None:
    op.drop_table("incident_candidates")
    op.drop_index("ix_expected_model_runs_model_version", table_name="expected_model_runs")
    op.drop_index("ix_expected_model_runs_predictor_type", table_name="expected_model_runs")
    op.drop_table("expected_model_runs")
    op.drop_index(
        "ix_expected_generation_results_anomaly_state",
        table_name="expected_generation_results",
    )
    op.drop_index(
        "ix_expected_generation_results_model_run_id",
        table_name="expected_generation_results",
    )
    for column_name in [
        "anomaly_state",
        "anomaly_eligible",
        "data_quality_status",
        "solar_elevation_degree",
        "performance_ratio",
        "energy_loss_kwh",
        "signed_residual_kwh",
        "predictor_type",
        "model_run_id",
    ]:
        op.drop_column("expected_generation_results", column_name)
