"""initial SolarGuard schema

Revision ID: 20260704_0001
Revises:
Create Date: 2026-07-04
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260704_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sites",
        sa.Column("site_id", sa.String(length=16), primary_key=True),
        sa.Column("site_name", sa.String(length=128), nullable=False),
        sa.Column("capacity_kw", sa.Float(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("weather_zone", sa.String(length=64), nullable=False),
        sa.Column("commissioning_date", sa.Date(), nullable=False),
        sa.Column("inverter_vendor", sa.String(length=64), nullable=False),
        sa.Column("inverter_model", sa.String(length=64), nullable=False),
        sa.Column("panel_capacity_w", sa.Integer(), nullable=True),
        sa.Column("panel_count", sa.Integer(), nullable=True),
        sa.Column("tilt_degree", sa.Float(), nullable=False),
        sa.Column("azimuth_degree", sa.Float(), nullable=False),
        sa.Column("site_efficiency_factor", sa.Float(), nullable=False),
        sa.Column("tariff_per_kwh", sa.Float(), nullable=False),
        sa.Column("service_region", sa.String(length=64), nullable=False),
        sa.Column("customer_type", sa.String(length=32), nullable=False),
        sa.Column("warranty_end_date", sa.Date(), nullable=True),
        sa.Column("cleaning_cost_inr", sa.Float(), nullable=False),
        sa.Column("visit_cost_inr", sa.Float(), nullable=False),
    )
    op.create_index("ix_sites_service_region", "sites", ["service_region"])
    op.create_index("ix_sites_weather_zone", "sites", ["weather_zone"])

    op.create_table(
        "technicians",
        sa.Column("technician_id", sa.String(length=16), primary_key=True),
        sa.Column("technician_name", sa.String(length=128), nullable=False),
        sa.Column("start_latitude", sa.Float(), nullable=False),
        sa.Column("start_longitude", sa.Float(), nullable=False),
        sa.Column("shift_start", sa.Time(), nullable=False),
        sa.Column("shift_end", sa.Time(), nullable=False),
        sa.Column("maximum_visits", sa.Integer(), nullable=False),
        sa.Column("skill_set", sa.Text(), nullable=False),
        sa.Column("region", sa.String(length=128), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
    )

    op.create_table(
        "analysis_runs",
        sa.Column("analysis_run_id", sa.String(length=64), primary_key=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("analysis_date", sa.Date(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("configuration_version", sa.String(length=64), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("summary_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_analysis_runs_status", "analysis_runs", ["status"])

    op.create_table(
        "weather_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("weather_zone", sa.String(length=64), nullable=False),
        sa.Column("ghi_wm2", sa.Float(), nullable=False),
        sa.Column("dni_wm2", sa.Float(), nullable=True),
        sa.Column("dhi_wm2", sa.Float(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=False),
        sa.Column("cloud_cover_pct", sa.Float(), nullable=False),
        sa.Column("rainfall_mm", sa.Float(), nullable=False),
        sa.Column("wind_speed_ms", sa.Float(), nullable=False),
        sa.Column("weather_quality_flag", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("weather_zone", "timestamp", name="uq_weather_zone_time"),
    )
    op.create_index("ix_weather_history_timestamp", "weather_history", ["timestamp"])
    op.create_index("ix_weather_history_weather_zone", "weather_history", ["weather_zone"])

    op.create_table(
        "weather_forecast",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("forecast_generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("forecast_horizon_hours", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("weather_zone", sa.String(length=64), nullable=False),
        sa.Column("ghi_wm2", sa.Float(), nullable=False),
        sa.Column("dni_wm2", sa.Float(), nullable=True),
        sa.Column("dhi_wm2", sa.Float(), nullable=True),
        sa.Column("temperature_c", sa.Float(), nullable=False),
        sa.Column("cloud_cover_pct", sa.Float(), nullable=False),
        sa.Column("rainfall_mm", sa.Float(), nullable=False),
        sa.Column("wind_speed_ms", sa.Float(), nullable=False),
        sa.Column("weather_quality_flag", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("weather_zone", "timestamp", name="uq_weather_forecast_zone_time"),
    )
    op.create_index("ix_weather_forecast_timestamp", "weather_forecast", ["timestamp"])
    op.create_index("ix_weather_forecast_weather_zone", "weather_forecast", ["weather_zone"])

    op.create_table(
        "telemetry",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("site_id", sa.String(length=16), sa.ForeignKey("sites.site_id"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generation_kwh", sa.Float(), nullable=True),
        sa.Column("ac_power_kw", sa.Float(), nullable=True),
        sa.Column("dc_voltage", sa.Float(), nullable=True),
        sa.Column("dc_current", sa.Float(), nullable=True),
        sa.Column("ac_voltage", sa.Float(), nullable=True),
        sa.Column("grid_frequency_hz", sa.Float(), nullable=True),
        sa.Column("inverter_temperature_c", sa.Float(), nullable=True),
        sa.Column("inverter_status", sa.String(length=32), nullable=True),
        sa.Column("fault_code", sa.String(length=128), nullable=True),
        sa.Column("data_received", sa.Boolean(), nullable=False),
        sa.Column("source_quality_flag", sa.String(length=32), nullable=False),
        sa.UniqueConstraint("site_id", "timestamp", name="uq_telemetry_site_time"),
    )
    op.create_index("ix_telemetry_site_id", "telemetry", ["site_id"])
    op.create_index("ix_telemetry_timestamp", "telemetry", ["timestamp"])

    op.create_table(
        "service_history",
        sa.Column("ticket_id", sa.String(length=32), primary_key=True),
        sa.Column("site_id", sa.String(length=16), sa.ForeignKey("sites.site_id"), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("complaint_type", sa.String(length=64), nullable=False),
        sa.Column("complaint_severity", sa.String(length=32), nullable=False),
        sa.Column("actual_fault", sa.Text(), nullable=True),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("visit_cost_inr", sa.Float(), nullable=True),
        sa.Column(
            "technician_id",
            sa.String(length=16),
            sa.ForeignKey("technicians.technician_id"),
            nullable=True,
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("remote_resolution", sa.Boolean(), nullable=False),
        sa.Column("repeat_complaint", sa.Boolean(), nullable=False),
        sa.Column("sla_due_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_service_history_site_id", "service_history", ["site_id"])

    op.create_table(
        "site_diagnostics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "analysis_run_id",
            sa.String(length=64),
            sa.ForeignKey("analysis_runs.analysis_run_id"),
            nullable=False,
        ),
        sa.Column("analysis_date", sa.Date(), nullable=False),
        sa.Column("site_id", sa.String(length=16), sa.ForeignKey("sites.site_id"), nullable=False),
        sa.Column("data_completeness_pct", sa.Float(), nullable=False),
        sa.Column("expected_energy_kwh", sa.Float(), nullable=False),
        sa.Column("actual_energy_kwh", sa.Float(), nullable=False),
        sa.Column("energy_loss_kwh", sa.Float(), nullable=False),
        sa.Column("performance_ratio", sa.Float(), nullable=True),
        sa.Column("probable_issue", sa.String(length=128), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("confidence_label", sa.String(length=32), nullable=False),
        sa.Column("evidence_json", sa.JSON(), nullable=True),
        sa.Column("recommended_action", sa.String(length=128), nullable=False),
        sa.Column("visit_required", sa.Boolean(), nullable=False),
        sa.Column("estimated_value_at_risk_inr", sa.Float(), nullable=False),
        sa.Column("estimated_recoverable_value_inr", sa.Float(), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=False),
        sa.Column("priority_label", sa.String(length=32), nullable=False),
    )
    op.create_index("ix_site_diagnostics_analysis_run_id", "site_diagnostics", ["analysis_run_id"])
    op.create_index("ix_site_diagnostics_site_id", "site_diagnostics", ["site_id"])

    op.create_table(
        "expected_generation_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "analysis_run_id",
            sa.String(length=64),
            sa.ForeignKey("analysis_runs.analysis_run_id"),
            nullable=False,
        ),
        sa.Column("site_id", sa.String(length=16), sa.ForeignKey("sites.site_id"), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expected_generation_kwh", sa.Float(), nullable=False),
        sa.Column("actual_generation_kwh", sa.Float(), nullable=True),
        sa.Column("ghi_wm2", sa.Float(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("eligible", sa.Boolean(), nullable=False),
        sa.UniqueConstraint(
            "analysis_run_id",
            "site_id",
            "timestamp",
            name="uq_expected_generation_run_site_time",
        ),
    )
    op.create_index(
        "ix_expected_generation_results_analysis_run_id",
        "expected_generation_results",
        ["analysis_run_id"],
    )
    op.create_index(
        "ix_expected_generation_results_site_id",
        "expected_generation_results",
        ["site_id"],
    )
    op.create_index(
        "ix_expected_generation_results_timestamp",
        "expected_generation_results",
        ["timestamp"],
    )

    op.create_table(
        "service_jobs",
        sa.Column("job_id", sa.String(length=64), primary_key=True),
        sa.Column(
            "analysis_run_id",
            sa.String(length=64),
            sa.ForeignKey("analysis_runs.analysis_run_id"),
            nullable=False,
        ),
        sa.Column("site_id", sa.String(length=16), sa.ForeignKey("sites.site_id"), nullable=False),
        sa.Column("job_type", sa.String(length=64), nullable=False),
        sa.Column("required_skill", sa.String(length=64), nullable=False),
        sa.Column("priority_score", sa.Float(), nullable=False),
        sa.Column("estimated_duration_min", sa.Integer(), nullable=False),
        sa.Column("earliest_visit", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latest_visit", sa.DateTime(timezone=True), nullable=True),
        sa.Column("selected_for_route", sa.Boolean(), nullable=False),
    )
    op.create_index("ix_service_jobs_analysis_run_id", "service_jobs", ["analysis_run_id"])
    op.create_index("ix_service_jobs_site_id", "service_jobs", ["site_id"])

    op.create_table(
        "route_plans",
        sa.Column("route_plan_id", sa.String(length=64), primary_key=True),
        sa.Column(
            "analysis_run_id",
            sa.String(length=64),
            sa.ForeignKey("analysis_runs.analysis_run_id"),
            nullable=False,
        ),
        sa.Column("plan_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=True),
    )
    op.create_index("ix_route_plans_analysis_run_id", "route_plans", ["analysis_run_id"])

    op.create_table(
        "route_stops",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "route_plan_id",
            sa.String(length=64),
            sa.ForeignKey("route_plans.route_plan_id"),
            nullable=False,
        ),
        sa.Column(
            "technician_id",
            sa.String(length=16),
            sa.ForeignKey("technicians.technician_id"),
            nullable=False,
        ),
        sa.Column("stop_order", sa.Integer(), nullable=False),
        sa.Column("site_id", sa.String(length=16), sa.ForeignKey("sites.site_id"), nullable=False),
        sa.Column(
            "job_id",
            sa.String(length=64),
            sa.ForeignKey("service_jobs.job_id"),
            nullable=True,
        ),
        sa.Column("distance_from_previous_km", sa.Float(), nullable=True),
        sa.Column("estimated_arrival", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_route_stops_route_plan_id", "route_stops", ["route_plan_id"])
    op.create_index("ix_route_stops_technician_id", "route_stops", ["technician_id"])


def downgrade() -> None:
    for table_name in [
        "route_stops",
        "route_plans",
        "service_jobs",
        "expected_generation_results",
        "site_diagnostics",
        "service_history",
        "telemetry",
        "weather_forecast",
        "weather_history",
        "analysis_runs",
        "technicians",
        "sites",
    ]:
        op.drop_table(table_name)
