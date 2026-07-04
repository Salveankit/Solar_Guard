from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy.engine import Engine

from app.core.errors import DataValidationError
from app.repositories import (
    AnalysisRepository,
    SitesRepository,
    TelemetryRepository,
    WeatherRepository,
)
from app.services.validation import OPERATIONAL_FILES, DatasetValidator


class DemoDataLoader:
    def __init__(self, dataset_dir: Path, engine: Engine) -> None:
        self.dataset_dir = dataset_dir
        self.engine = engine
        self.validator = DatasetValidator(dataset_dir)

    def load_demo(self, reset_existing: bool = True) -> dict:
        validation_result = self.validator.validate_all(include_evaluation_files=True)
        if not validation_result.is_valid:
            raise DataValidationError("Demo dataset validation failed", validation_result.errors)

        frames = self.validator.load_operational_frames()

        with self.engine.begin() as connection:
            analysis_repository = AnalysisRepository(connection)
            sites_repository = SitesRepository(connection)
            telemetry_repository = TelemetryRepository(connection)
            weather_repository = WeatherRepository(connection)
            if reset_existing:
                analysis_repository.clear_demo_data()

            sites_repository.replace_sites(self._normalise_frame(frames["site_master"]))
            analysis_repository.insert_technicians(self._normalise_frame(frames["technicians"]))
            weather_repository.replace_weather_history(
                self._normalise_frame(frames["weather_history"])
            )
            weather_repository.replace_weather_forecast(
                self._normalise_frame(frames["weather_forecast"])
            )
            telemetry_repository.replace_telemetry(self._normalise_frame(frames["telemetry"]))
            analysis_repository.insert_service_history(
                self._normalise_frame(frames["service_history"])
            )
            database_counts = self._database_counts(
                analysis_repository,
                sites_repository,
                telemetry_repository,
                weather_repository,
            )

        return {
            "status": "loaded",
            "idempotency_strategy": "controlled_replace" if reset_existing else "append_only",
            "datasets": {
                self._api_dataset_name(filename): validation_result.row_counts[filename]
                for filename in OPERATIONAL_FILES
            },
            "database_counts": database_counts,
            "validation_warnings": [
                warning.as_dict() for warning in validation_result.warnings
            ],
        }

    def _normalise_frame(self, frame: pd.DataFrame) -> pd.DataFrame:
        normalised = frame.copy()
        for column in normalised.columns:
            if column.endswith("_at") or column in {
                "timestamp",
                "reported_at",
                "resolved_at",
                "sla_due_at",
                "forecast_generated_at",
            }:
                normalised[column] = pd.to_datetime(normalised[column], errors="coerce")
            if column.endswith("_date") or column in {"commissioning_date", "warranty_end_date"}:
                normalised[column] = pd.to_datetime(normalised[column], errors="coerce").dt.date
            if column in {"shift_start", "shift_end"}:
                normalised[column] = pd.to_datetime(
                    normalised[column],
                    format="%H:%M",
                    errors="coerce",
                ).dt.time
        return normalised.where(pd.notna(normalised), None)

    def _api_dataset_name(self, filename: str) -> str:
        mapping = {
            "site_master.csv": "sites",
            "telemetry.csv": "telemetry",
            "weather_history.csv": "weather_history",
            "weather_forecast.csv": "weather_forecast",
            "service_history.csv": "service_history",
            "technicians.csv": "technicians",
        }
        return mapping[filename]

    def _database_counts(
        self,
        analysis_repository: AnalysisRepository,
        sites_repository: SitesRepository,
        telemetry_repository: TelemetryRepository,
        weather_repository: WeatherRepository,
    ) -> dict[str, int]:
        return {
            "sites": sites_repository.count_sites(),
            "telemetry": telemetry_repository.count_telemetry(),
            "weather_history": weather_repository.count_weather_history(),
            "weather_forecast": weather_repository.count_weather_forecast(),
            "service_history": analysis_repository.count_table("service_history"),
            "technicians": analysis_repository.count_table("technicians"),
            "fault_ground_truth": 0,
            "scenario_validation_expected": 0,
        }
