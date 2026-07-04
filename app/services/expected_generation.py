from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
from sqlalchemy.engine import Connection

from app.repositories import (
    AnalysisRepository,
    SitesRepository,
    TelemetryRepository,
    WeatherRepository,
)
from app.services.model_features import solar_position_features

BASELINE_MODEL_VERSION = "expected-baseline-v1"
INTERVAL_HOURS = 0.25
STANDARD_IRRADIANCE_WM2 = 1000.0


@dataclass(frozen=True)
class ExpectedGenerationSummary:
    analysis_run_id: str
    rows_persisted: int
    eligible_rows: int
    model_version: str = BASELINE_MODEL_VERSION


class ExpectedGenerationService:
    def __init__(self, connection: Connection, config: dict, configuration_version: str) -> None:
        self.connection = connection
        self.config = config
        self.configuration_version = configuration_version
        self.sites_repository = SitesRepository(connection)
        self.telemetry_repository = TelemetryRepository(connection)
        self.weather_repository = WeatherRepository(connection)
        self.analysis_repository = AnalysisRepository(connection)

    def run_baseline(
        self,
        analysis_run_id: str,
        analysis_date: date | None = None,
        model_run_id: str | None = None,
        predictor_type: str = "baseline",
    ) -> ExpectedGenerationSummary:
        sites = self.sites_repository.read_sites_frame()
        telemetry = self.telemetry_repository.read_telemetry_frame()
        weather = self.weather_repository.read_weather_history_frame()
        expected = self.calculate_baseline(sites, telemetry, weather)
        expected["analysis_run_id"] = analysis_run_id
        expected["model_run_id"] = model_run_id
        expected["predictor_type"] = predictor_type

        self.analysis_repository.create_analysis_run(
            analysis_run_id=analysis_run_id,
            configuration_version=self.configuration_version,
            model_version=BASELINE_MODEL_VERSION,
            analysis_date=analysis_date,
        )
        self.analysis_repository.replace_expected_generation(analysis_run_id, expected)
        summary = {
            "expected_generation_rows": len(expected),
            "eligible_rows": int(expected["anomaly_eligible"].sum()) if not expected.empty else 0,
            "model_version": BASELINE_MODEL_VERSION,
        }
        self.analysis_repository.complete_analysis_run(analysis_run_id, summary)
        return ExpectedGenerationSummary(
            analysis_run_id=analysis_run_id,
            rows_persisted=len(expected),
            eligible_rows=summary["eligible_rows"],
        )

    def calculate_baseline(
        self,
        sites: pd.DataFrame,
        telemetry: pd.DataFrame,
        weather: pd.DataFrame,
    ) -> pd.DataFrame:
        if sites.empty or telemetry.empty or weather.empty:
            return self._empty_result()

        telemetry = telemetry.copy()
        weather = weather.copy()
        telemetry["timestamp"] = pd.to_datetime(telemetry["timestamp"], errors="coerce")
        weather["timestamp"] = pd.to_datetime(weather["timestamp"], errors="coerce")

        frame = telemetry.merge(sites, on="site_id", how="inner").merge(
            weather,
            on=["weather_zone", "timestamp"],
            how="inner",
        )
        frame = frame.dropna(subset=["timestamp", "ghi_wm2", "temperature_c"])
        if frame.empty:
            return self._empty_result()

        solar = solar_position_features(frame)
        frame["solar_elevation_degree"] = solar["solar_elevation_degree"]
        frame["solar_azimuth_degree"] = solar["solar_azimuth_degree"]
        frame["expected_generation_kwh"] = self._expected_generation(frame)
        frame = add_expected_result_metrics(
            frame,
            minimum_expected_generation_kwh=self._minimum_expected_generation(),
            minimum_irradiance_wm2=self._minimum_irradiance(),
        )
        frame["eligible"] = frame["anomaly_eligible"]
        frame["model_run_id"] = None
        frame["predictor_type"] = "baseline"
        frame["model_version"] = BASELINE_MODEL_VERSION
        frame["data_quality_status"] = frame["source_quality_flag"].fillna("UNKNOWN")

        return pd.DataFrame(
            {
                "analysis_run_id": "",
                "site_id": frame["site_id"],
                "timestamp": frame["timestamp"],
                "model_run_id": frame["model_run_id"],
                "predictor_type": frame["predictor_type"],
                "expected_generation_kwh": frame["expected_generation_kwh"],
                "actual_generation_kwh": frame["generation_kwh"],
                "signed_residual_kwh": frame["signed_residual_kwh"],
                "energy_loss_kwh": frame["energy_loss_kwh"],
                "performance_ratio": frame["performance_ratio"],
                "ghi_wm2": frame["ghi_wm2"],
                "solar_elevation_degree": frame["solar_elevation_degree"],
                "data_quality_status": frame["data_quality_status"],
                "model_version": frame["model_version"],
                "eligible": frame["eligible"],
                "anomaly_eligible": frame["anomaly_eligible"],
                "anomaly_state": frame["anomaly_state"],
            }
        )

    def apply_prediction_columns(
        self,
        frame: pd.DataFrame,
        expected_generation: pd.Series,
        model_version: str,
        predictor_type: str,
        model_run_id: str | None,
    ) -> pd.DataFrame:
        predicted = frame.copy()
        predicted["expected_generation_kwh"] = expected_generation
        predicted = add_expected_result_metrics(
            predicted,
            minimum_expected_generation_kwh=self._minimum_expected_generation(),
            minimum_irradiance_wm2=self._minimum_irradiance(),
        )
        predicted["model_run_id"] = model_run_id
        predicted["predictor_type"] = predictor_type
        predicted["model_version"] = model_version
        predicted["eligible"] = predicted["anomaly_eligible"]
        predicted["data_quality_status"] = predicted["source_quality_flag"].fillna("UNKNOWN")
        return pd.DataFrame(
            {
                "analysis_run_id": "",
                "site_id": predicted["site_id"],
                "timestamp": predicted["timestamp"],
                "model_run_id": predicted["model_run_id"],
                "predictor_type": predicted["predictor_type"],
                "expected_generation_kwh": predicted["expected_generation_kwh"],
                "actual_generation_kwh": predicted["generation_kwh"],
                "signed_residual_kwh": predicted["signed_residual_kwh"],
                "energy_loss_kwh": predicted["energy_loss_kwh"],
                "performance_ratio": predicted["performance_ratio"],
                "ghi_wm2": predicted["ghi_wm2"],
                "solar_elevation_degree": predicted["solar_elevation_degree"],
                "data_quality_status": predicted["data_quality_status"],
                "model_version": predicted["model_version"],
                "eligible": predicted["eligible"],
                "anomaly_eligible": predicted["anomaly_eligible"],
                "anomaly_state": predicted["anomaly_state"],
            }
        )

    def merged_operational_frame(self) -> pd.DataFrame:
        sites = self.sites_repository.read_sites_frame()
        telemetry = self.telemetry_repository.read_telemetry_frame()
        weather = self.weather_repository.read_weather_history_frame()
        if sites.empty or telemetry.empty or weather.empty:
            return pd.DataFrame()
        telemetry = telemetry.copy()
        weather = weather.copy()
        telemetry["timestamp"] = pd.to_datetime(telemetry["timestamp"], errors="coerce")
        weather["timestamp"] = pd.to_datetime(weather["timestamp"], errors="coerce")
        frame = telemetry.merge(sites, on="site_id", how="inner").merge(
            weather,
            on=["weather_zone", "timestamp"],
            how="inner",
        )
        if frame.empty:
            return frame
        solar = solar_position_features(frame)
        frame["solar_elevation_degree"] = solar["solar_elevation_degree"]
        frame["solar_azimuth_degree"] = solar["solar_azimuth_degree"]
        return frame

    def baseline_for_operational_frame(self, frame: pd.DataFrame) -> pd.Series:
        return self._expected_generation(frame)

    def _baseline_eligible(self, frame: pd.DataFrame) -> pd.Series:
        return (
            (frame["solar_elevation_degree"] > 0)
            & (frame["ghi_wm2"] >= self._minimum_irradiance())
            & (frame["expected_generation_kwh"] > 0)
        )

    def _expected_generation(self, frame: pd.DataFrame) -> pd.Series:
        irradiance_factor = (frame["ghi_wm2"] / STANDARD_IRRADIANCE_WM2).clip(lower=0)
        temperature_factor = (1 - 0.004 * (frame["temperature_c"] - 25)).clip(lower=0.75, upper=1.1)
        orientation_factor = self._orientation_factor(frame).clip(lower=0.65, upper=1.05)
        daylight = (frame["solar_elevation_degree"] > 0) & (frame["ghi_wm2"] > 0)
        raw_expected = (
            frame["capacity_kw"]
            * irradiance_factor
            * INTERVAL_HOURS
            * temperature_factor
            * orientation_factor
            * frame["site_efficiency_factor"]
        )
        capacity_bound = (
            frame["capacity_kw"] * INTERVAL_HOURS * self._maximum_capacity_factor()
        )
        bounded = raw_expected.clip(lower=0, upper=capacity_bound)
        return bounded.where(daylight, 0.0)

    def _orientation_factor(self, frame: pd.DataFrame) -> pd.Series:
        azimuth_penalty = 1 - (abs(frame["azimuth_degree"] - 180).clip(upper=90) / 90) * 0.12
        tilt_penalty = 1 - (abs(frame["tilt_degree"] - 18).clip(upper=45) / 45) * 0.08
        return azimuth_penalty * tilt_penalty

    def _minimum_irradiance(self) -> float:
        return float(self.config.get("analysis", {}).get("minimum_irradiance_wm2", 200))

    def _minimum_expected_generation(self) -> float:
        return float(self.config.get("analysis", {}).get("minimum_expected_generation_kwh", 0.05))

    def _maximum_capacity_factor(self) -> float:
        return float(
            self.config.get("modeling", {}).get("maximum_expected_generation_capacity_factor", 1.2)
        )

    def _empty_result(self) -> pd.DataFrame:
        return pd.DataFrame(
            columns=[
                "analysis_run_id",
                "site_id",
                "timestamp",
                "model_run_id",
                "predictor_type",
                "expected_generation_kwh",
                "actual_generation_kwh",
                "signed_residual_kwh",
                "energy_loss_kwh",
                "performance_ratio",
                "ghi_wm2",
                "solar_elevation_degree",
                "data_quality_status",
                "model_version",
                "eligible",
                "anomaly_eligible",
                "anomaly_state",
            ]
        )


def add_expected_result_metrics(
    frame: pd.DataFrame,
    minimum_expected_generation_kwh: float,
    minimum_irradiance_wm2: float,
) -> pd.DataFrame:
    result = frame.copy()
    actual = result["generation_kwh"]
    expected = result["expected_generation_kwh"]
    result["signed_residual_kwh"] = actual - expected
    result["energy_loss_kwh"] = (expected - actual).clip(lower=0).fillna(0.0)
    result["performance_ratio"] = actual.divide(expected.where(expected > 0))
    has_actual = actual.notna()
    received = result["data_received"].astype(bool)
    good_source = result["source_quality_flag"].eq("GOOD")
    weather_quality = result.get("weather_quality_flag", pd.Series("GOOD", index=result.index))
    good_weather = weather_quality.eq("GOOD")
    daylight = result["solar_elevation_degree"] > 0
    irradiance_ok = result["ghi_wm2"] >= minimum_irradiance_wm2
    expected_ok = expected >= minimum_expected_generation_kwh
    result["anomaly_eligible"] = (
        received & has_actual & good_source & good_weather & daylight & irradiance_ok & expected_ok
    )
    result["anomaly_state"] = "ineligible"
    result.loc[~received, "anomaly_state"] = "communication missing"
    result.loc[result["anomaly_eligible"], "anomaly_state"] = "normal"
    return result
