from __future__ import annotations

from pathlib import Path

import pandas as pd

from app.services.validation import DatasetValidator


def write_csvs(base_dir: Path, overrides: dict[str, pd.DataFrame] | None = None) -> None:
    overrides = overrides or {}
    frames = {
        "site_master.csv": pd.DataFrame(
            [
                {
                    "site_id": "MH-101",
                    "site_name": "Baner Site 101",
                    "capacity_kw": 5.0,
                    "latitude": 18.5709,
                    "longitude": 73.7570,
                    "weather_zone": "PUNE_WEST",
                    "commissioning_date": "2025-01-01",
                    "inverter_vendor": "Vendor-A",
                    "inverter_model": "INV-5K",
                    "panel_capacity_w": 550,
                    "panel_count": 9,
                    "tilt_degree": 18,
                    "azimuth_degree": 180,
                    "site_efficiency_factor": 0.91,
                    "tariff_per_kwh": 8.0,
                    "service_region": "Pune West",
                    "customer_type": "residential",
                    "warranty_end_date": "2030-01-01",
                    "cleaning_cost_inr": 750,
                    "visit_cost_inr": 800,
                }
            ]
        ),
        "telemetry.csv": pd.DataFrame(
            [
                {
                    "site_id": "MH-101",
                    "timestamp": "2026-06-01T10:00:00+05:30",
                    "generation_kwh": 0.5,
                    "ac_power_kw": 2.0,
                    "dc_voltage": 380,
                    "dc_current": 6.1,
                    "ac_voltage": 230,
                    "grid_frequency_hz": 50,
                    "inverter_temperature_c": 42,
                    "inverter_status": "RUNNING",
                    "fault_code": "",
                    "data_received": True,
                    "source_quality_flag": "GOOD",
                },
                {
                    "site_id": "MH-101",
                    "timestamp": "2026-06-01T10:15:00+05:30",
                    "generation_kwh": None,
                    "ac_power_kw": None,
                    "dc_voltage": None,
                    "dc_current": None,
                    "ac_voltage": None,
                    "grid_frequency_hz": None,
                    "inverter_temperature_c": None,
                    "inverter_status": None,
                    "fault_code": "",
                    "data_received": False,
                    "source_quality_flag": "MISSING",
                },
                {
                    "site_id": "MH-101",
                    "timestamp": "2026-06-01T10:30:00+05:30",
                    "generation_kwh": 0.0,
                    "ac_power_kw": 0.0,
                    "dc_voltage": 350,
                    "dc_current": 0.0,
                    "ac_voltage": 230,
                    "grid_frequency_hz": 50,
                    "inverter_temperature_c": 40,
                    "inverter_status": "STANDBY",
                    "fault_code": "",
                    "data_received": True,
                    "source_quality_flag": "GOOD",
                },
            ]
        ),
        "weather_history.csv": pd.DataFrame(
            [
                {
                    "timestamp": "2026-06-01T10:00:00+05:30",
                    "weather_zone": "PUNE_WEST",
                    "ghi_wm2": 700,
                    "dni_wm2": 560,
                    "dhi_wm2": 150,
                    "temperature_c": 32,
                    "cloud_cover_pct": 20,
                    "rainfall_mm": 0,
                    "wind_speed_ms": 3,
                    "weather_quality_flag": "GOOD",
                }
            ]
        ),
        "weather_forecast.csv": pd.DataFrame(
            [
                {
                    "forecast_generated_at": "2026-06-01T18:00:00+05:30",
                    "forecast_horizon_hours": 72,
                    "timestamp": "2026-06-02T10:00:00+05:30",
                    "weather_zone": "PUNE_WEST",
                    "ghi_wm2": 650,
                    "dni_wm2": 520,
                    "dhi_wm2": 140,
                    "temperature_c": 31,
                    "cloud_cover_pct": 25,
                    "rainfall_mm": 0,
                    "wind_speed_ms": 3,
                    "weather_quality_flag": "GOOD",
                }
            ]
        ),
        "service_history.csv": pd.DataFrame(
            [
                {
                    "ticket_id": "TKT-1001",
                    "site_id": "MH-101",
                    "reported_at": "2026-05-30T10:00:00+05:30",
                    "complaint_type": "LOW_GENERATION",
                    "complaint_severity": "MEDIUM",
                    "actual_fault": "",
                    "resolution": "",
                    "visit_cost_inr": 800,
                    "technician_id": "TECH-01",
                    "resolved_at": "2026-05-30T12:00:00+05:30",
                    "remote_resolution": True,
                    "repeat_complaint": False,
                    "sla_due_at": "2026-05-31T10:00:00+05:30",
                }
            ]
        ),
        "technicians.csv": pd.DataFrame(
            [
                {
                    "technician_id": "TECH-01",
                    "technician_name": "Aarav Kulkarni",
                    "start_latitude": 18.5204,
                    "start_longitude": 73.8567,
                    "shift_start": "09:00",
                    "shift_end": "18:00",
                    "maximum_visits": 4,
                    "skill_set": "electrical;inverter",
                    "region": "Pune West",
                    "active": True,
                }
            ]
        ),
        "fault_ground_truth.csv": pd.DataFrame(
            [
                {
                    "incident_id": "INC-001",
                    "site_id": "MH-101",
                    "fault_type": "COMMUNICATION",
                    "start_timestamp": "2026-06-01T10:15:00+05:30",
                    "end_timestamp": "2026-06-01T10:30:00+05:30",
                    "severity": "MEDIUM",
                    "injected_loss_pct": 0,
                    "expected_action": "REMOTE_CHECK",
                    "expected_visit_required": False,
                    "notes": "Missing telemetry test case",
                }
            ]
        ),
        "scenario_validation_expected.csv": pd.DataFrame(
            [
                {
                    "scenario_id": "INC-001",
                    "site_id": "MH-101",
                    "expected_issue_category": "COMMUNICATION",
                    "expected_action": "REMOTE_CHECK",
                    "expected_visit_required": False,
                    "minimum_expected_confidence": 0.7,
                    "acceptance_note": "Missing telemetry should be communication",
                }
            ]
        ),
    }
    frames.update(overrides)
    for filename, frame in frames.items():
        frame.to_csv(base_dir / filename, index=False)


def test_valid_dataset_passes(tmp_path: Path) -> None:
    write_csvs(tmp_path)

    result = DatasetValidator(tmp_path).validate_all()

    assert result.is_valid
    assert result.row_counts["site_master.csv"] == 1
    assert result.row_counts["telemetry.csv"] == 3


def test_missing_required_column_fails(tmp_path: Path) -> None:
    broken_sites = pd.DataFrame([{"site_id": "MH-101"}])
    write_csvs(tmp_path, {"site_master.csv": broken_sites})

    result = DatasetValidator(tmp_path).validate_all()

    assert not result.is_valid
    assert any(issue.field == "capacity_kw" for issue in result.errors)


def test_duplicate_telemetry_key_fails(tmp_path: Path) -> None:
    write_csvs(tmp_path)
    telemetry = pd.read_csv(tmp_path / "telemetry.csv")
    telemetry = pd.concat([telemetry, telemetry.iloc[[0]]], ignore_index=True)
    telemetry.to_csv(tmp_path / "telemetry.csv", index=False)

    result = DatasetValidator(tmp_path).validate_all()

    assert not result.is_valid
    assert any("duplicate key" in issue.reason for issue in result.errors)


def test_unknown_site_foreign_key_fails(tmp_path: Path) -> None:
    write_csvs(tmp_path)
    telemetry = pd.read_csv(tmp_path / "telemetry.csv")
    telemetry.loc[0, "site_id"] = "MH-999"
    telemetry.to_csv(tmp_path / "telemetry.csv", index=False)

    result = DatasetValidator(tmp_path).validate_all()

    assert not result.is_valid
    assert any(
        issue.field == "site_id" and "Invalid foreign key" in issue.reason
        for issue in result.errors
    )


def test_missing_telemetry_is_not_required_to_be_zero(tmp_path: Path) -> None:
    write_csvs(tmp_path)

    result = DatasetValidator(tmp_path).validate_all()

    assert result.is_valid
    assert not any("data_received=false" in issue.reason for issue in result.warnings)
