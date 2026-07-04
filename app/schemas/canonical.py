from __future__ import annotations

from datetime import date, datetime, time
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CustomerType(StrEnum):
    residential = "residential"
    commercial = "commercial"
    society = "society"


class InverterStatus(StrEnum):
    running = "RUNNING"
    offline = "OFFLINE"
    fault = "FAULT"
    standby = "STANDBY"
    unknown = "UNKNOWN"


class SourceQualityFlag(StrEnum):
    good = "GOOD"
    suspect = "SUSPECT"
    missing = "MISSING"


class WeatherQualityFlag(StrEnum):
    good = "GOOD"
    suspect = "SUSPECT"


class ComplaintType(StrEnum):
    low_generation = "LOW_GENERATION"
    offline = "OFFLINE"
    no_display = "NO_DISPLAY"
    cleaning = "CLEANING"
    other = "OTHER"


class Severity(StrEnum):
    low = "LOW"
    medium = "MEDIUM"
    high = "HIGH"
    critical = "CRITICAL"


class GroundTruthFaultType(StrEnum):
    communication = "COMMUNICATION"
    sudden_outage = "SUDDEN_OUTAGE"
    gradual_degradation = "GRADUAL_DEGRADATION"
    time_specific = "TIME_SPECIFIC"
    ambiguous = "AMBIGUOUS"


class ExpectedAction(StrEnum):
    monitor = "MONITOR"
    remote_check = "REMOTE_CHECK"
    cleaning = "CLEANING"
    visit = "VISIT"
    collect_data = "COLLECT_DATA"


class CanonicalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SiteMasterRecord(CanonicalModel):
    site_id: str = Field(pattern=r"^MH-\d{3}$")
    site_name: str
    capacity_kw: float = Field(gt=0, le=100)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    weather_zone: str
    commissioning_date: date
    inverter_vendor: str
    inverter_model: str
    panel_capacity_w: int | None = Field(default=None, ge=250, le=800)
    panel_count: int | None = Field(default=None, gt=0)
    tilt_degree: float = Field(ge=0, le=60)
    azimuth_degree: float = Field(ge=0, le=360)
    site_efficiency_factor: float = Field(ge=0.70, le=1.05)
    tariff_per_kwh: float = Field(ge=0)
    service_region: str
    customer_type: CustomerType
    warranty_end_date: date | None = None
    cleaning_cost_inr: float = Field(ge=0)
    visit_cost_inr: float = Field(ge=0)


class TelemetryRecord(CanonicalModel):
    site_id: str
    timestamp: datetime
    generation_kwh: float | None = Field(default=None, ge=0)
    ac_power_kw: float | None = Field(default=None, ge=0)
    dc_voltage: float | None = Field(default=None, ge=0, le=1500)
    dc_current: float | None = Field(default=None, ge=0)
    ac_voltage: float | None = Field(default=None, ge=0, le=300)
    grid_frequency_hz: float | None = Field(default=None, ge=40, le=60)
    inverter_temperature_c: float | None = Field(default=None, ge=-20, le=100)
    inverter_status: InverterStatus | None
    fault_code: str | None = None
    data_received: bool
    source_quality_flag: SourceQualityFlag

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_have_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("timestamp must include timezone")
        return value


class WeatherHistoryRecord(CanonicalModel):
    timestamp: datetime
    weather_zone: str
    ghi_wm2: float = Field(ge=0, le=1400)
    dni_wm2: float | None = Field(default=None, ge=0, le=1400)
    dhi_wm2: float | None = Field(default=None, ge=0, le=1000)
    temperature_c: float = Field(ge=-10, le=60)
    cloud_cover_pct: float = Field(ge=0, le=100)
    rainfall_mm: float = Field(ge=0)
    wind_speed_ms: float = Field(ge=0, le=75)
    weather_quality_flag: WeatherQualityFlag


class WeatherForecastRecord(WeatherHistoryRecord):
    forecast_generated_at: datetime
    forecast_horizon_hours: int = Field(ge=1, le=168)


class ServiceHistoryRecord(CanonicalModel):
    ticket_id: str = Field(pattern=r"^TKT-\d{4}$")
    site_id: str
    reported_at: datetime
    complaint_type: ComplaintType
    complaint_severity: Severity
    actual_fault: str | None = None
    resolution: str | None = None
    visit_cost_inr: float | None = Field(default=None, ge=0)
    technician_id: str | None = None
    resolved_at: datetime | None = None
    remote_resolution: bool
    repeat_complaint: bool
    sla_due_at: datetime


class TechnicianRecord(CanonicalModel):
    technician_id: str = Field(pattern=r"^TECH-\d{2}$")
    technician_name: str
    start_latitude: float = Field(ge=-90, le=90)
    start_longitude: float = Field(ge=-180, le=180)
    shift_start: time
    shift_end: time
    maximum_visits: int = Field(ge=1, le=8)
    skill_set: str
    region: str
    active: bool


class FaultGroundTruthRecord(CanonicalModel):
    incident_id: str = Field(pattern=r"^INC-\d{3}$")
    site_id: str
    fault_type: GroundTruthFaultType
    start_timestamp: datetime
    end_timestamp: datetime
    severity: Severity
    injected_loss_pct: float = Field(ge=0, le=100)
    expected_action: ExpectedAction
    expected_visit_required: bool
    notes: str | None = None


class ScenarioValidationRecord(CanonicalModel):
    scenario_id: str
    site_id: str
    expected_issue_category: str
    expected_action: ExpectedAction
    expected_visit_required: bool
    minimum_expected_confidence: float = Field(ge=0, le=1)
    acceptance_note: str | None = None
