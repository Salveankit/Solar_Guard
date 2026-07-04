from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Site(Base):
    __tablename__ = "sites"

    site_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    site_name: Mapped[str] = mapped_column(String(128))
    capacity_kw: Mapped[float] = mapped_column(Float)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    weather_zone: Mapped[str] = mapped_column(String(64), index=True)
    commissioning_date: Mapped[date] = mapped_column(Date)
    inverter_vendor: Mapped[str] = mapped_column(String(64))
    inverter_model: Mapped[str] = mapped_column(String(64))
    panel_capacity_w: Mapped[int | None] = mapped_column(Integer, nullable=True)
    panel_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tilt_degree: Mapped[float] = mapped_column(Float)
    azimuth_degree: Mapped[float] = mapped_column(Float)
    site_efficiency_factor: Mapped[float] = mapped_column(Float)
    tariff_per_kwh: Mapped[float] = mapped_column(Float)
    service_region: Mapped[str] = mapped_column(String(64), index=True)
    customer_type: Mapped[str] = mapped_column(String(32))
    warranty_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    cleaning_cost_inr: Mapped[float] = mapped_column(Float)
    visit_cost_inr: Mapped[float] = mapped_column(Float)


class Telemetry(Base):
    __tablename__ = "telemetry"
    __table_args__ = (UniqueConstraint("site_id", "timestamp", name="uq_telemetry_site_time"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    site_id: Mapped[str] = mapped_column(String(16), ForeignKey("sites.site_id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    generation_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    ac_power_kw: Mapped[float | None] = mapped_column(Float, nullable=True)
    dc_voltage: Mapped[float | None] = mapped_column(Float, nullable=True)
    dc_current: Mapped[float | None] = mapped_column(Float, nullable=True)
    ac_voltage: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_frequency_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    inverter_temperature_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    inverter_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fault_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    data_received: Mapped[bool] = mapped_column(Boolean)
    source_quality_flag: Mapped[str] = mapped_column(String(32))


class WeatherHistory(Base):
    __tablename__ = "weather_history"
    __table_args__ = (UniqueConstraint("weather_zone", "timestamp", name="uq_weather_zone_time"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    weather_zone: Mapped[str] = mapped_column(String(64), index=True)
    ghi_wm2: Mapped[float] = mapped_column(Float)
    dni_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    dhi_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float] = mapped_column(Float)
    cloud_cover_pct: Mapped[float] = mapped_column(Float)
    rainfall_mm: Mapped[float] = mapped_column(Float)
    wind_speed_ms: Mapped[float] = mapped_column(Float)
    weather_quality_flag: Mapped[str] = mapped_column(String(32))


class WeatherForecast(Base):
    __tablename__ = "weather_forecast"
    __table_args__ = (
        UniqueConstraint("weather_zone", "timestamp", name="uq_weather_forecast_zone_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    forecast_generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    forecast_horizon_hours: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    weather_zone: Mapped[str] = mapped_column(String(64), index=True)
    ghi_wm2: Mapped[float] = mapped_column(Float)
    dni_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    dhi_wm2: Mapped[float | None] = mapped_column(Float, nullable=True)
    temperature_c: Mapped[float] = mapped_column(Float)
    cloud_cover_pct: Mapped[float] = mapped_column(Float)
    rainfall_mm: Mapped[float] = mapped_column(Float)
    wind_speed_ms: Mapped[float] = mapped_column(Float)
    weather_quality_flag: Mapped[str] = mapped_column(String(32))


class ServiceHistory(Base):
    __tablename__ = "service_history"

    ticket_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    site_id: Mapped[str] = mapped_column(String(16), ForeignKey("sites.site_id"), index=True)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    complaint_type: Mapped[str] = mapped_column(String(64))
    complaint_severity: Mapped[str] = mapped_column(String(32))
    actual_fault: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolution: Mapped[str | None] = mapped_column(Text, nullable=True)
    visit_cost_inr: Mapped[float | None] = mapped_column(Float, nullable=True)
    technician_id: Mapped[str | None] = mapped_column(
        String(16),
        ForeignKey("technicians.technician_id"),
        nullable=True,
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    remote_resolution: Mapped[bool] = mapped_column(Boolean)
    repeat_complaint: Mapped[bool] = mapped_column(Boolean)
    sla_due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Technician(Base):
    __tablename__ = "technicians"

    technician_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    technician_name: Mapped[str] = mapped_column(String(128))
    start_latitude: Mapped[float] = mapped_column(Float)
    start_longitude: Mapped[float] = mapped_column(Float)
    shift_start: Mapped[time] = mapped_column(Time)
    shift_end: Mapped[time] = mapped_column(Time)
    maximum_visits: Mapped[int] = mapped_column(Integer)
    skill_set: Mapped[str] = mapped_column(Text)
    region: Mapped[str] = mapped_column(String(128))
    active: Mapped[bool] = mapped_column(Boolean)


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    analysis_run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    analysis_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    configuration_version: Mapped[str] = mapped_column(String(64))
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class SiteDiagnostic(Base):
    __tablename__ = "site_diagnostics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analysis_runs.analysis_run_id"),
        index=True,
    )
    analysis_date: Mapped[date] = mapped_column(Date)
    site_id: Mapped[str] = mapped_column(String(16), ForeignKey("sites.site_id"), index=True)
    data_completeness_pct: Mapped[float] = mapped_column(Float)
    expected_energy_kwh: Mapped[float] = mapped_column(Float)
    actual_energy_kwh: Mapped[float] = mapped_column(Float)
    energy_loss_kwh: Mapped[float] = mapped_column(Float)
    performance_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    probable_issue: Mapped[str] = mapped_column(String(128))
    confidence_score: Mapped[float] = mapped_column(Float)
    confidence_label: Mapped[str] = mapped_column(String(32))
    evidence_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    recommended_action: Mapped[str] = mapped_column(String(128))
    visit_required: Mapped[bool] = mapped_column(Boolean)
    estimated_value_at_risk_inr: Mapped[float] = mapped_column(Float)
    estimated_recoverable_value_inr: Mapped[float] = mapped_column(Float)
    priority_score: Mapped[float] = mapped_column(Float)
    priority_label: Mapped[str] = mapped_column(String(32))


class ExpectedGenerationResult(Base):
    __tablename__ = "expected_generation_results"
    __table_args__ = (
        UniqueConstraint(
            "analysis_run_id",
            "site_id",
            "timestamp",
            name="uq_expected_generation_run_site_time",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    analysis_run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analysis_runs.analysis_run_id"),
        index=True,
    )
    site_id: Mapped[str] = mapped_column(String(16), ForeignKey("sites.site_id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    model_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    predictor_type: Mapped[str] = mapped_column(String(32), default="baseline")
    expected_generation_kwh: Mapped[float] = mapped_column(Float)
    actual_generation_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    signed_residual_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    energy_loss_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    performance_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    ghi_wm2: Mapped[float] = mapped_column(Float)
    solar_elevation_degree: Mapped[float | None] = mapped_column(Float, nullable=True)
    data_quality_status: Mapped[str] = mapped_column(String(32), default="GOOD")
    model_version: Mapped[str] = mapped_column(String(64))
    eligible: Mapped[bool] = mapped_column(Boolean)
    anomaly_eligible: Mapped[bool] = mapped_column(Boolean, default=False)
    anomaly_state: Mapped[str] = mapped_column(String(64), default="ineligible", index=True)


class ExpectedModelRun(Base):
    __tablename__ = "expected_model_runs"

    model_run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    predictor_type: Mapped[str] = mapped_column(String(32), index=True)
    model_version: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean)
    promotion_decision: Mapped[str] = mapped_column(String(64))
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class IncidentCandidate(Base):
    __tablename__ = "incident_candidates"
    __table_args__ = (
        UniqueConstraint(
            "analysis_run_id",
            "candidate_stage",
            "site_id",
            "start_timestamp",
            "provisional_category",
            name="uq_incident_candidate_run_stage_site_start_category",
        ),
    )

    incident_candidate_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analysis_runs.analysis_run_id"),
        index=True,
    )
    site_id: Mapped[str] = mapped_column(String(16), ForeignKey("sites.site_id"), index=True)
    start_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    end_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    interval_count: Mapped[int] = mapped_column(Integer)
    duration_minutes: Mapped[int] = mapped_column(Integer)
    expected_energy_kwh: Mapped[float] = mapped_column(Float)
    actual_energy_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_energy_loss_kwh: Mapped[float] = mapped_column(Float)
    average_performance_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    minimum_performance_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    anomaly_state: Mapped[str] = mapped_column(String(64))
    dominant_evidence: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    data_completeness: Mapped[float] = mapped_column(Float)
    provisional_category: Mapped[str] = mapped_column(String(96), index=True)
    preliminary_recommendation: Mapped[str | None] = mapped_column(String(128), nullable=True)
    candidate_stage: Mapped[str] = mapped_column(String(32), default="consolidated", index=True)
    source_candidate_count: Mapped[int] = mapped_column(Integer, default=1)
    secondary_evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)
    operational_qualification_status: Mapped[str] = mapped_column(
        String(32),
        default="qualified",
    )
    actionable: Mapped[bool] = mapped_column(Boolean, default=True, index=True)


class ServiceDecision(Base):
    __tablename__ = "service_decisions"
    __table_args__ = (
        UniqueConstraint(
            "analysis_run_id",
            "incident_candidate_id",
            name="uq_service_decision_run_candidate",
        ),
    )

    decision_id: Mapped[str] = mapped_column(String(96), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("analysis_runs.analysis_run_id"), index=True
    )
    incident_candidate_id: Mapped[str] = mapped_column(
        String(96), ForeignKey("incident_candidates.incident_candidate_id")
    )
    site_id: Mapped[str] = mapped_column(String(16), ForeignKey("sites.site_id"), index=True)
    probable_issue: Mapped[str] = mapped_column(String(128))
    confidence_score: Mapped[float] = mapped_column(Float)
    confidence_label: Mapped[str] = mapped_column(String(32))
    supporting_evidence: Mapped[list] = mapped_column(JSON)
    contradictory_evidence: Mapped[list] = mapped_column(JSON)
    confidence_components: Mapped[dict] = mapped_column(JSON)
    expected_energy_kwh: Mapped[float] = mapped_column(Float)
    actual_energy_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_energy_loss_kwh: Mapped[float] = mapped_column(Float)
    estimated_value_at_risk_inr: Mapped[float] = mapped_column(Float)
    projected_seven_day_loss_kwh: Mapped[float] = mapped_column(Float)
    estimated_recoverable_energy_kwh: Mapped[float] = mapped_column(Float)
    estimated_recoverable_value_inr: Mapped[float] = mapped_column(Float)
    tariff_per_kwh: Mapped[float] = mapped_column(Float)
    visit_cost_inr: Mapped[float] = mapped_column(Float)
    cleaning_cost_inr: Mapped[float] = mapped_column(Float)
    cleaning_decision: Mapped[str] = mapped_column(String(32))
    cleaning_reason: Mapped[str] = mapped_column(Text)
    recommended_action: Mapped[str] = mapped_column(String(64))
    action_reason: Mapped[str] = mapped_column(Text)
    prerequisite_remote_checks: Mapped[list] = mapped_column(JSON)
    escalation_condition: Mapped[str] = mapped_column(Text)
    remote_action_available: Mapped[bool] = mapped_column(Boolean)
    visit_required: Mapped[bool] = mapped_column(Boolean)
    actionable: Mapped[bool] = mapped_column(Boolean, index=True)
    complaint_severity: Mapped[str] = mapped_column(String(32))
    sla_status: Mapped[str] = mapped_column(String(32))
    priority_score: Mapped[float] = mapped_column(Float, index=True)
    priority_label: Mapped[str] = mapped_column(String(32))
    priority_components: Mapped[dict] = mapped_column(JSON)
    queue_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ServiceJob(Base):
    __tablename__ = "service_jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analysis_runs.analysis_run_id"),
        index=True,
    )
    site_id: Mapped[str] = mapped_column(String(16), ForeignKey("sites.site_id"), index=True)
    job_type: Mapped[str] = mapped_column(String(64))
    required_skill: Mapped[str] = mapped_column(String(64))
    priority_score: Mapped[float] = mapped_column(Float)
    estimated_duration_min: Mapped[int] = mapped_column(Integer)
    earliest_visit: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    latest_visit: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    selected_for_route: Mapped[bool] = mapped_column(Boolean, default=False)


class RoutePlan(Base):
    __tablename__ = "route_plans"

    route_plan_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    analysis_run_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("analysis_runs.analysis_run_id"),
        index=True,
    )
    plan_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    summary_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class RouteStop(Base):
    __tablename__ = "route_stops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_plan_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("route_plans.route_plan_id"),
        index=True,
    )
    technician_id: Mapped[str] = mapped_column(
        String(16),
        ForeignKey("technicians.technician_id"),
        index=True,
    )
    stop_order: Mapped[int] = mapped_column(Integer)
    site_id: Mapped[str] = mapped_column(String(16), ForeignKey("sites.site_id"))
    job_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("service_jobs.job_id"))
    distance_from_previous_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_arrival: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
