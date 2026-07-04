from __future__ import annotations

import pytest

from app.core.config import Settings, redact_url, require_test_database_url
from app.database.session import build_engine


def test_missing_database_url_raises() -> None:
    with pytest.raises(Exception, match="DATABASE_URL is required"):
        build_engine(None)


def test_missing_test_database_url_without_development_override_fails() -> None:
    settings = Settings(_env_file=None, DATABASE_URL="postgresql://user:pass@example/db")

    with pytest.raises(ValueError, match="TEST_DATABASE_URL is required"):
        require_test_database_url(settings)


def test_test_database_url_must_not_equal_database_url_without_override() -> None:
    url = "postgresql://user:pass@example/db"
    settings = Settings(_env_file=None, DATABASE_URL=url, TEST_DATABASE_URL=url)

    with pytest.raises(ValueError, match="must not match"):
        require_test_database_url(settings)


def test_database_url_can_be_used_with_explicit_development_override() -> None:
    url = "postgresql://user:pass@example/dev"
    settings = Settings(_env_file=None, DATABASE_URL=url, ALLOW_DEVELOPMENT_DB_TESTS=True)

    assert require_test_database_url(settings) == url


def test_database_url_redaction_hides_credentials() -> None:
    redacted = redact_url("postgresql://user:secret@example.neon.tech/db?sslmode=require")

    assert "secret" not in redacted
    assert "user" not in redacted
    assert "<redacted>" in redacted
    assert "example.neon.tech" in redacted
