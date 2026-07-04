from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, ValidationError

from app.core.errors import ValidationIssue
from app.schemas.canonical import (
    FaultGroundTruthRecord,
    ScenarioValidationRecord,
    ServiceHistoryRecord,
    SiteMasterRecord,
    TechnicianRecord,
    TelemetryRecord,
    WeatherForecastRecord,
    WeatherHistoryRecord,
)

DATASET_SCHEMAS: dict[str, type[BaseModel]] = {
    "site_master.csv": SiteMasterRecord,
    "telemetry.csv": TelemetryRecord,
    "weather_history.csv": WeatherHistoryRecord,
    "weather_forecast.csv": WeatherForecastRecord,
    "service_history.csv": ServiceHistoryRecord,
    "technicians.csv": TechnicianRecord,
    "fault_ground_truth.csv": FaultGroundTruthRecord,
    "scenario_validation_expected.csv": ScenarioValidationRecord,
}

OPERATIONAL_FILES = [
    "site_master.csv",
    "telemetry.csv",
    "weather_history.csv",
    "weather_forecast.csv",
    "service_history.csv",
    "technicians.csv",
]


@dataclass
class DatasetValidationResult:
    row_counts: dict[str, int] = field(default_factory=dict)
    errors: list[ValidationIssue] = field(default_factory=list)
    warnings: list[ValidationIssue] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "row_counts": self.row_counts,
            "errors": [issue.as_dict() for issue in self.errors],
            "warnings": [issue.as_dict() for issue in self.warnings],
        }


class DatasetValidator:
    def __init__(self, dataset_dir: Path) -> None:
        self.dataset_dir = dataset_dir

    def validate_all(self, include_evaluation_files: bool = True) -> DatasetValidationResult:
        files = list(OPERATIONAL_FILES)
        if include_evaluation_files:
            files.extend(["fault_ground_truth.csv", "scenario_validation_expected.csv"])

        result = DatasetValidationResult()
        frames: dict[str, pd.DataFrame] = {}

        for filename in files:
            frame = self._read_csv(filename, result)
            if frame is None:
                continue
            frames[filename] = frame
            result.row_counts[filename] = len(frame)
            self._validate_columns(filename, frame, result)
            self._validate_rows(filename, frame, result)
            self._validate_critical_values(filename, frame, result)

        self._validate_relationships(frames, result)
        return result

    def load_operational_frames(self) -> dict[str, pd.DataFrame]:
        return {
            filename.replace(".csv", ""): pd.read_csv(
                self.dataset_dir / filename,
                low_memory=False,
            )
            for filename in OPERATIONAL_FILES
        }

    def _read_csv(
        self,
        filename: str,
        result: DatasetValidationResult,
    ) -> pd.DataFrame | None:
        path = self.dataset_dir / filename
        if not path.exists():
            result.errors.append(
                ValidationIssue(file=filename, field=None, reason="Required file is missing")
            )
            return None
        try:
            return pd.read_csv(path, low_memory=False)
        except Exception as exc:  # pragma: no cover - defensive IO guard
            result.errors.append(
                ValidationIssue(file=filename, field=None, reason=f"Could not read CSV: {exc}")
            )
            return None

    def _validate_columns(
        self,
        filename: str,
        frame: pd.DataFrame,
        result: DatasetValidationResult,
    ) -> None:
        schema = DATASET_SCHEMAS[filename]
        required = set(schema.model_fields)
        actual = set(frame.columns)
        for column in sorted(required - actual):
            result.errors.append(
                ValidationIssue(file=filename, field=column, reason="Required column is missing")
            )
        for column in sorted(actual - required):
            result.warnings.append(
                ValidationIssue(
                    file=filename,
                    field=column,
                    reason="Unknown column will be ignored by canonical validation",
                    severity="warning",
                )
            )

    def _validate_rows(
        self,
        filename: str,
        frame: pd.DataFrame,
        result: DatasetValidationResult,
    ) -> None:
        schema = DATASET_SCHEMAS[filename]
        if any(column not in frame.columns for column in schema.model_fields):
            return
        for index, row in frame.iterrows():
            payload = self._normalise_payload(row.to_dict())
            try:
                schema.model_validate(payload)
            except ValidationError as exc:
                for error in exc.errors():
                    field = ".".join(str(part) for part in error["loc"]) or None
                    result.errors.append(
                        ValidationIssue(
                            file=filename,
                            row=int(index) + 2,
                            field=field,
                            reason=str(error["msg"]),
                        )
                    )
            if len(result.errors) >= 100:
                result.errors.append(
                    ValidationIssue(
                        file=filename,
                        field=None,
                        reason="Validation stopped after 100 row-level errors",
                    )
                )
                return

    def _validate_critical_values(
        self,
        filename: str,
        frame: pd.DataFrame,
        result: DatasetValidationResult,
    ) -> None:
        if filename == "telemetry.csv":
            self._check_required_datetimes(filename, frame, ["timestamp"], result)
            for column in ["generation_kwh", "ac_power_kw", "dc_current"]:
                self._check_non_negative(filename, frame, column, result)
        elif filename in {"weather_history.csv", "weather_forecast.csv"}:
            self._check_required_datetimes(filename, frame, ["timestamp"], result)
            for column in ["ghi_wm2", "temperature_c", "cloud_cover_pct", "rainfall_mm"]:
                self._check_non_negative(filename, frame, column, result)
        elif filename == "service_history.csv":
            self._check_required_datetimes(
                filename,
                frame,
                ["reported_at", "sla_due_at"],
                result,
            )

    def _check_required_datetimes(
        self,
        filename: str,
        frame: pd.DataFrame,
        columns: list[str],
        result: DatasetValidationResult,
    ) -> None:
        for column in columns:
            if column not in frame.columns:
                continue
            parsed = pd.to_datetime(frame[column], errors="coerce")
            invalid = int(parsed.isna().sum())
            if invalid:
                result.errors.append(
                    ValidationIssue(
                        file=filename,
                        field=column,
                        reason=f"{invalid} rows contain invalid required timestamp values",
                    )
                )

    def _check_non_negative(
        self,
        filename: str,
        frame: pd.DataFrame,
        column: str,
        result: DatasetValidationResult,
    ) -> None:
        if column not in frame.columns:
            return
        values = pd.to_numeric(frame[column], errors="coerce")
        negative = int((values < 0).sum())
        if negative:
            result.errors.append(
                ValidationIssue(
                    file=filename,
                    field=column,
                    reason=f"{negative} rows contain negative values",
                )
            )

    def _validate_relationships(
        self,
        frames: dict[str, pd.DataFrame],
        result: DatasetValidationResult,
    ) -> None:
        sites = self._string_values(frames.get("site_master.csv"), "site_id")
        technicians = self._string_values(frames.get("technicians.csv"), "technician_id")
        weather_zones = self._string_values(frames.get("site_master.csv"), "weather_zone")

        self._check_unique(frames, "site_master.csv", ["site_id"], result)
        self._check_unique(frames, "technicians.csv", ["technician_id"], result)
        self._check_unique(frames, "telemetry.csv", ["site_id", "timestamp"], result)
        self._check_unique(frames, "weather_history.csv", ["weather_zone", "timestamp"], result)

        for filename in [
            "telemetry.csv",
            "service_history.csv",
            "fault_ground_truth.csv",
            "scenario_validation_expected.csv",
        ]:
            self._check_foreign_key(frames, filename, "site_id", sites, result)

        self._check_foreign_key(
            frames,
            "weather_history.csv",
            "weather_zone",
            weather_zones,
            result,
        )
        self._check_foreign_key(
            frames,
            "weather_forecast.csv",
            "weather_zone",
            weather_zones,
            result,
        )
        self._check_foreign_key(
            frames,
            "service_history.csv",
            "technician_id",
            technicians,
            result,
            allow_blank=True,
        )
        self._check_telemetry_missing_vs_zero(frames.get("telemetry.csv"), result)

    def _check_unique(
        self,
        frames: dict[str, pd.DataFrame],
        filename: str,
        columns: list[str],
        result: DatasetValidationResult,
    ) -> None:
        frame = frames.get(filename)
        if frame is None or any(column not in frame.columns for column in columns):
            return
        duplicate_count = int(frame.duplicated(subset=columns).sum())
        if duplicate_count:
            result.errors.append(
                ValidationIssue(
                    file=filename,
                    field=",".join(columns),
                    reason=f"{duplicate_count} duplicate key rows found",
                )
            )

    def _check_foreign_key(
        self,
        frames: dict[str, pd.DataFrame],
        filename: str,
        column: str,
        allowed_values: set[str],
        result: DatasetValidationResult,
        allow_blank: bool = False,
    ) -> None:
        frame = frames.get(filename)
        if frame is None or column not in frame.columns or not allowed_values:
            return
        values = frame[column].dropna().astype(str)
        if allow_blank:
            values = values[values.str.len() > 0]
        invalid = sorted(set(values) - allowed_values)
        if invalid:
            result.errors.append(
                ValidationIssue(
                    file=filename,
                    field=column,
                    reason=f"Invalid foreign key values: {', '.join(invalid[:5])}",
                )
            )

    def _check_telemetry_missing_vs_zero(
        self,
        frame: pd.DataFrame | None,
        result: DatasetValidationResult,
    ) -> None:
        if frame is None or "data_received" not in frame.columns:
            return
        missing_mask = frame["data_received"].astype(str).str.lower() == "false"
        measurement_fields = [
            "generation_kwh",
            "ac_power_kw",
            "dc_voltage",
            "dc_current",
            "ac_voltage",
            "grid_frequency_hz",
            "inverter_temperature_c",
        ]
        existing_fields = [field_name for field_name in measurement_fields if field_name in frame]
        if not existing_fields:
            return
        fabricated = frame.loc[missing_mask, existing_fields].notna().any(axis=1)
        if bool(fabricated.any()):
            result.warnings.append(
                ValidationIssue(
                    file="telemetry.csv",
                    field="data_received",
                    reason=(
                        "Rows with data_received=false should keep measurement fields blank; "
                        f"{int(fabricated.sum())} rows contain measured values"
                    ),
                    severity="warning",
                )
            )

    def _string_values(self, frame: pd.DataFrame | None, column: str) -> set[str]:
        if frame is None or column not in frame.columns:
            return set()
        return set(frame[column].dropna().astype(str))

    def _normalise_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        normalised: dict[str, Any] = {}
        for key, value in payload.items():
            if pd.isna(value):
                normalised[key] = None
            else:
                normalised[key] = value
        return normalised
