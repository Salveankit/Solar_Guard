from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection


class TelemetryRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def replace_telemetry(self, frame: pd.DataFrame) -> None:
        frame.to_sql(
            "telemetry",
            self.connection,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=1000,
        )

    def count_telemetry(self) -> int:
        return int(self.connection.execute(text("SELECT count(*) FROM telemetry")).scalar_one())

    def count_missing_measurements(self) -> int:
        return int(
            self.connection.execute(
                text(
                    """
                    SELECT count(*)
                    FROM telemetry
                    WHERE data_received = false
                      AND generation_kwh IS NULL
                      AND ac_power_kw IS NULL
                    """
                )
            ).scalar_one()
        )

    def read_received_telemetry_frame(self) -> pd.DataFrame:
        return pd.read_sql_query(
            """
            SELECT site_id, timestamp, generation_kwh, data_received, source_quality_flag
            FROM telemetry
            WHERE data_received = true
              AND generation_kwh IS NOT NULL
              AND source_quality_flag != 'MISSING'
            """,
            self.connection,
        )

    def read_telemetry_frame(self) -> pd.DataFrame:
        return pd.read_sql_query(
            """
            SELECT site_id, timestamp, generation_kwh, ac_power_kw, dc_voltage, dc_current,
                   ac_voltage, grid_frequency_hz, inverter_temperature_c, inverter_status,
                   fault_code, data_received, source_quality_flag
            FROM telemetry
            ORDER BY site_id, timestamp
            """,
            self.connection,
        )
