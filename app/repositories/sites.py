from __future__ import annotations

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Connection


class SitesRepository:
    def __init__(self, connection: Connection) -> None:
        self.connection = connection

    def replace_sites(self, frame: pd.DataFrame) -> None:
        frame.to_sql("sites", self.connection, if_exists="append", index=False, method="multi")

    def count_sites(self) -> int:
        return int(self.connection.execute(text("SELECT count(*) FROM sites")).scalar_one())

    def read_sites_frame(self) -> pd.DataFrame:
        return pd.read_sql_query(
            """
            SELECT site_id, capacity_kw, latitude, longitude, weather_zone,
                   tilt_degree, azimuth_degree, site_efficiency_factor
            FROM sites
            """,
            self.connection,
        )
