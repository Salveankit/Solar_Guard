from __future__ import annotations

import numpy as np
import pandas as pd
import pvlib

FEATURE_COLUMNS = [
    "capacity_kw",
    "site_efficiency_factor",
    "tilt_degree",
    "azimuth_degree",
    "ghi_wm2",
    "dni_wm2",
    "dhi_wm2",
    "temperature_c",
    "cloud_cover_pct",
    "wind_speed_ms",
    "rainfall_mm",
    "solar_elevation_degree",
    "solar_azimuth_degree",
    "daylight_indicator",
    "temperature_adjusted_irradiance",
    "clear_sky_index",
    "hour_sin",
    "hour_cos",
    "day_of_year_sin",
    "day_of_year_cos",
]
FEATURE_SCHEMA_VERSION = "expected-generation-features-v3"
LOCAL_TIMEZONE = "Asia/Kolkata"


class ExpectedGenerationFeatureBuilder:
    def build_features(self, frame: pd.DataFrame) -> pd.DataFrame:
        features = self.add_derived_columns(frame)
        return features[FEATURE_COLUMNS].fillna(0.0)

    def add_derived_columns(self, frame: pd.DataFrame) -> pd.DataFrame:
        features = frame.copy()
        timestamps = pd.to_datetime(features["timestamp"], errors="coerce")
        if timestamps.dt.tz is None:
            raise ValueError("Expected-generation timestamps must be timezone-aware")
        local_timestamps = timestamps.dt.tz_convert(LOCAL_TIMEZONE)
        hour_fraction = local_timestamps.dt.hour + local_timestamps.dt.minute / 60.0
        day_of_year = local_timestamps.dt.dayofyear
        features["local_hour"] = hour_fraction
        features["local_date"] = local_timestamps.dt.date
        features["morning_indicator"] = local_timestamps.dt.hour.between(8, 11).astype(float)
        features["afternoon_indicator"] = local_timestamps.dt.hour.between(14, 17).astype(float)
        if "solar_elevation_degree" not in features or "solar_azimuth_degree" not in features:
            solar = solar_position_features(features)
            features["solar_elevation_degree"] = solar["solar_elevation_degree"]
            features["solar_azimuth_degree"] = solar["solar_azimuth_degree"]
        for optional_column in ["dni_wm2", "dhi_wm2", "rainfall_mm"]:
            if optional_column not in features:
                features[optional_column] = 0.0
        features["hour_sin"] = _sin_cycle(hour_fraction, 24)
        features["hour_cos"] = _cos_cycle(hour_fraction, 24)
        features["day_of_year_sin"] = _sin_cycle(day_of_year, 365)
        features["day_of_year_cos"] = _cos_cycle(day_of_year, 365)
        features["daylight_indicator"] = (
            (features["solar_elevation_degree"] > 0) & (features["ghi_wm2"] > 0)
        ).astype(float)
        temperature_factor = (1 - 0.004 * (features["temperature_c"] - 25)).clip(
            lower=0.75,
            upper=1.1,
        )
        features["temperature_adjusted_irradiance"] = features["ghi_wm2"] * temperature_factor
        clear_sky = (1000 * np.sin(np.radians(features["solar_elevation_degree"].clip(lower=0))))
        features["clear_sky_index"] = (features["ghi_wm2"] / clear_sky.replace(0, np.nan)).clip(
            lower=0,
            upper=2,
        )
        return features


class XGBoostExpectedGenerationModel:
    model_version = "expected-xgb-v2"

    def __init__(self, model) -> None:
        self.model = model

    def predict(self, feature_frame: pd.DataFrame) -> pd.Series:
        predictions = self.model.predict(feature_frame[FEATURE_COLUMNS])
        return pd.Series(predictions, index=feature_frame.index).clip(lower=0)


def solar_position_features(frame: pd.DataFrame) -> pd.DataFrame:
    result = pd.DataFrame(index=frame.index)
    result["solar_elevation_degree"] = np.nan
    result["solar_azimuth_degree"] = np.nan
    for _site_id, group in frame.groupby("site_id", sort=False):
        timestamps = pd.DatetimeIndex(pd.to_datetime(group["timestamp"], errors="coerce"))
        if timestamps.tz is None:
            timestamps = timestamps.tz_localize("Asia/Kolkata")
        position = pvlib.solarposition.get_solarposition(
            time=timestamps,
            latitude=float(group["latitude"].iloc[0]),
            longitude=float(group["longitude"].iloc[0]),
        )
        result.loc[group.index, "solar_elevation_degree"] = position[
            "apparent_elevation"
        ].to_numpy()
        result.loc[group.index, "solar_azimuth_degree"] = position["azimuth"].to_numpy()
    return result


def _sin_cycle(values: pd.Series, period: int) -> pd.Series:
    return pd.Series(np.sin(2 * np.pi * values.astype(float) / period), index=values.index)


def _cos_cycle(values: pd.Series, period: int) -> pd.Series:
    return pd.Series(np.cos(2 * np.pi * values.astype(float) / period), index=values.index)
