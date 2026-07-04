from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment and YAML config."""

    model_config = SettingsConfigDict(env_prefix="SOLARGUARD_", env_file=".env", extra="ignore")

    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    test_database_url: str | None = Field(default=None, alias="TEST_DATABASE_URL")
    allow_development_db_tests: bool = Field(
        default=False,
        alias="ALLOW_DEVELOPMENT_DB_TESTS",
    )
    config_path: Path = Path("config/poc_config.yaml")
    raw_data_dir: Path | None = None
    api_version: str = "1.0.0"

    @property
    def project_root(self) -> Path:
        return Path(__file__).resolve().parents[2]

    @property
    def resolved_config_path(self) -> Path:
        return self._resolve_path(self.config_path)

    @property
    def config(self) -> dict[str, Any]:
        with self.resolved_config_path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return data

    @property
    def configuration_version(self) -> str:
        return str(self.config.get("metadata", {}).get("configuration_version", "unknown"))

    @property
    def resolved_raw_data_dir(self) -> Path:
        configured = self.raw_data_dir or Path(
            self.config.get("paths", {}).get("raw_data_dir", "data/raw")
        )
        return self._resolve_path(configured)

    def _resolve_path(self, path: Path) -> Path:
        if path.is_absolute():
            return path
        return self.project_root / path


@lru_cache
def get_settings() -> Settings:
    return Settings()


def redact_url(url: str | None) -> str:
    if not url:
        return "<not configured>"
    if "@" not in url:
        return "<redacted>"
    scheme_and_credentials, host_part = url.split("@", 1)
    scheme = scheme_and_credentials.split("://", 1)[0] if "://" in scheme_and_credentials else ""
    prefix = f"{scheme}://" if scheme else ""
    return f"{prefix}<redacted>@{host_part}"


def require_test_database_url(settings: Settings | None = None) -> str:
    resolved = settings or get_settings()
    if resolved.test_database_url:
        if resolved.database_url and resolved.test_database_url == resolved.database_url:
            if not resolved.allow_development_db_tests:
                raise ValueError(
                    "TEST_DATABASE_URL must not match DATABASE_URL unless "
                    "ALLOW_DEVELOPMENT_DB_TESTS=true"
                )
        return resolved.test_database_url
    if resolved.database_url and resolved.allow_development_db_tests:
        return resolved.database_url
    raise ValueError(
        "TEST_DATABASE_URL is required for database integration tests unless "
        "ALLOW_DEVELOPMENT_DB_TESTS=true permits DATABASE_URL"
    )
