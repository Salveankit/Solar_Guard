from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ValidationIssue:
    file: str
    field: str | None
    reason: str
    row: int | None = None
    severity: str = "error"

    def as_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "file": self.file,
            "field": self.field,
            "reason": self.reason,
            "severity": self.severity,
        }
        if self.row is not None:
            payload["row"] = self.row
        return payload


class SolarGuardError(Exception):
    """Base application error with safe user-facing message."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class DataValidationError(SolarGuardError):
    def __init__(self, message: str, issues: list[ValidationIssue]) -> None:
        super().__init__(message, code="DATA_VALIDATION_FAILED")
        self.issues = issues

