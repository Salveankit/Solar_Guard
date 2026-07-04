from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection


class WeatherRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def replace_weather_history(self, frame: pd.DataFrame) -> None:
        frame.to_sql(
            "weather_history",
            self.connection,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )

    def replace_weather_forecast(self, frame: pd.DataFrame) -> None:
        frame.to_sql(
            "weather_forecast",
            self.connection,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )

    def count_weather_history(self) -> int:
        return int(
            self.connection.execute(text("SELECT count(*) FROM weather_history")).scalar_one()
        )

    def count_weather_forecast(self) -> int:
        return int(
            self.connection.execute(text("SELECT count(*) FROM weather_forecast")).scalar_one()
        )

    def read_weather_history_frame(self) -> pd.DataFrame:
        return pd.read_sql_query(
            """
            SELECT weather_zone, timestamp, ghi_wm2, dni_wm2, dhi_wm2, temperature_c,
                   cloud_cover_pct, rainfall_mm, wind_speed_ms, weather_quality_flag
            FROM weather_history
            """,
            self.connection,
        )
