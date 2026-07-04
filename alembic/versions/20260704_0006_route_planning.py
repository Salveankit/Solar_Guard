"""technician route planning contract

Revision ID: 20260704_0006
Revises: 20260704_0005
Create Date: 2026-07-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260704_0006"
down_revision: str | None = "20260704_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "service_jobs",
        sa.Column(
            "decision_id",
            sa.String(length=96),
            sa.ForeignKey("service_decisions.decision_id"),
            nullable=True,
        ),
    )
    op.add_column("service_jobs", sa.Column("candidate_id", sa.String(length=96)))
    op.add_column("service_jobs", sa.Column("latitude", sa.Float()))
    op.add_column("service_jobs", sa.Column("longitude", sa.Float()))
    op.add_column("service_jobs", sa.Column("priority_label", sa.String(length=32)))
    op.add_column("service_jobs", sa.Column("probable_issue", sa.String(length=128)))
    op.add_column("service_jobs", sa.Column("recommended_action", sa.String(length=64)))
    op.add_column("service_jobs", sa.Column("required_skills", sa.JSON()))
    op.add_column("service_jobs", sa.Column("recoverable_energy_kwh", sa.Float()))
    op.add_column("service_jobs", sa.Column("recoverable_value_inr", sa.Float()))
    op.create_unique_constraint("uq_service_jobs_decision", "service_jobs", ["decision_id"])

    for name, column in [
        ("optimisation_status", sa.String(length=32)),
        ("failure_reason", sa.Text()),
        ("total_eligible_jobs", sa.Integer()),
        ("assigned_jobs", sa.Integer()),
        ("unassigned_jobs", sa.Integer()),
        ("naive_distance_km", sa.Float()),
        ("optimised_distance_km", sa.Float()),
        ("distance_avoided_km", sa.Float()),
        ("total_travel_duration_min", sa.Integer()),
        ("total_job_duration_min", sa.Integer()),
        ("total_recoverable_energy_kwh", sa.Float()),
        ("total_recoverable_value_inr", sa.Float()),
        ("naive_routes", sa.JSON()),
        ("unassigned_job_details", sa.JSON()),
    ]:
        op.add_column("route_plans", sa.Column(name, column))
    op.create_unique_constraint(
        "uq_route_plan_analysis_date", "route_plans", ["analysis_run_id", "plan_date"]
    )

    op.add_column(
        "route_stops",
        sa.Column(
            "decision_id",
            sa.String(length=96),
            sa.ForeignKey("service_decisions.decision_id"),
        ),
    )
    op.add_column("route_stops", sa.Column("estimated_departure", sa.DateTime(timezone=True)))
    op.add_column("route_stops", sa.Column("travel_duration_min", sa.Integer()))
    op.add_column("route_stops", sa.Column("job_duration_min", sa.Integer()))
    op.add_column("route_stops", sa.Column("probable_issue", sa.String(length=128)))
    op.add_column("route_stops", sa.Column("recommended_action", sa.String(length=64)))
    op.add_column("route_stops", sa.Column("priority_score", sa.Float()))
    op.add_column("route_stops", sa.Column("priority_label", sa.String(length=32)))
    op.add_column("route_stops", sa.Column("required_skills", sa.JSON()))
    op.create_unique_constraint(
        "uq_route_stop_plan_decision", "route_stops", ["route_plan_id", "decision_id"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_route_stop_plan_decision", "route_stops", type_="unique")
    for name in [
        "required_skills",
        "priority_label",
        "priority_score",
        "recommended_action",
        "probable_issue",
        "job_duration_min",
        "travel_duration_min",
        "estimated_departure",
        "decision_id",
    ]:
        op.drop_column("route_stops", name)
    op.drop_constraint("uq_route_plan_analysis_date", "route_plans", type_="unique")
    for name in [
        "unassigned_job_details",
        "naive_routes",
        "total_recoverable_value_inr",
        "total_recoverable_energy_kwh",
        "total_job_duration_min",
        "total_travel_duration_min",
        "distance_avoided_km",
        "optimised_distance_km",
        "naive_distance_km",
        "unassigned_jobs",
        "assigned_jobs",
        "total_eligible_jobs",
        "failure_reason",
        "optimisation_status",
    ]:
        op.drop_column("route_plans", name)
    op.drop_constraint("uq_service_jobs_decision", "service_jobs", type_="unique")
    for name in [
        "recoverable_value_inr",
        "recoverable_energy_kwh",
        "required_skills",
        "recommended_action",
        "probable_issue",
        "priority_label",
        "longitude",
        "latitude",
        "candidate_id",
        "decision_id",
    ]:
        op.drop_column("service_jobs", name)
