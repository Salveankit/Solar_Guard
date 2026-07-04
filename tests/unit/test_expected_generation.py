from __future__ import annotations

import pandas as pd
import pytest

from app.services.expected_generation import ExpectedGenerationService, add_expected_result_metrics


def service() -> ExpectedGenerationService:
    return ExpectedGenerationService(
        connection=None,  # type: ignore[arg-type]
        config={"analysis": {"minimum_irradiance_wm2": 200}},
        configuration_version="test",
    )


def site_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "site_id": "MH-101",
                "capacity_kw": 5.0,
                "latitude": 18.5204,
                "longitude": 73.8567,
                "weather_zone": "PUNE_CENTRAL",
                "tilt_degree": 18.0,
                "azimuth_degree": 180.0,
                "site_efficiency_factor": 0.9,
            }
        ]
    )


def test_nighttime_baseline_output_is_zero() -> None:
    result = service().calculate_baseline(
        site_frame(),
        pd.DataFrame(
            [
                {
                    "site_id": "MH-101",
                    "timestamp": "2026-06-01T00:15:00+05:30",
                    "generation_kwh": 0.0,
                    "data_received": True,
                    "source_quality_flag": "GOOD",
                }
            ]
        ),
        pd.DataFrame(
            [
                {
                    "weather_zone": "PUNE_CENTRAL",
                    "timestamp": "2026-06-01T00:15:00+05:30",
                    "ghi_wm2": 0,
                    "temperature_c": 25,
                    "cloud_cover_pct": 10,
                    "rainfall_mm": 0,
                    "wind_speed_ms": 2,
                }
            ]
        ),
    )

    assert result["expected_generation_kwh"].iloc[0] == 0


def test_daytime_baseline_is_non_negative_bounded_and_eligible() -> None:
    result = service().calculate_baseline(
        site_frame(),
        pd.DataFrame(
            [
                {
                    "site_id": "MH-101",
                    "timestamp": "2026-06-01T12:00:00+05:30",
                    "generation_kwh": 0.8,
                    "data_received": True,
                    "source_quality_flag": "GOOD",
                }
            ]
        ),
        pd.DataFrame(
            [
                {
                    "weather_zone": "PUNE_CENTRAL",
                    "timestamp": "2026-06-01T12:00:00+05:30",
                    "ghi_wm2": 800,
                    "temperature_c": 32,
                    "cloud_cover_pct": 10,
                    "rainfall_mm": 0,
                    "wind_speed_ms": 2,
                }
            ]
        ),
    )

    expected = result["expected_generation_kwh"].iloc[0]
    assert expected >= 0
    assert expected <= 5.0 * 0.25 * 1.2
    assert bool(result["eligible"].iloc[0])
    assert bool(result["anomaly_eligible"].iloc[0])
    assert result["actual_generation_kwh"].iloc[0] == 0.8


def test_residual_semantics_underperformance_and_overperformance() -> None:
    frame = pd.DataFrame(
        [
            {
                "generation_kwh": 0.7,
                "expected_generation_kwh": 1.0,
                "data_received": True,
                "source_quality_flag": "GOOD",
                "weather_quality_flag": "GOOD",
                "solar_elevation_degree": 50,
                "ghi_wm2": 800,
            },
            {
                "generation_kwh": 1.2,
                "expected_generation_kwh": 1.0,
                "data_received": True,
                "source_quality_flag": "GOOD",
                "weather_quality_flag": "GOOD",
                "solar_elevation_degree": 50,
                "ghi_wm2": 800,
            },
        ]
    )

    result = add_expected_result_metrics(
        frame,
        minimum_expected_generation_kwh=0.05,
        minimum_irradiance_wm2=200,
    )

    assert result["signed_residual_kwh"].tolist() == pytest.approx([-0.3, 0.2])
    assert result["energy_loss_kwh"].tolist() == pytest.approx([0.3, 0.0])
    assert result["performance_ratio"].tolist() == pytest.approx([0.7, 1.2])
