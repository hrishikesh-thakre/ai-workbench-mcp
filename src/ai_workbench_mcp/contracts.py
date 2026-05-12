"""Shared JSON response contracts for Workbench MCP operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
JsonObject = dict[str, Any]


@dataclass(frozen=True)
class WorkbenchResponse:
    """Stable response envelope for future MCP tool wrappers."""

    operation: str
    status: str
    ok: bool
    artifacts: JsonObject = field(default_factory=dict)
    summary: JsonObject = field(default_factory=dict)
    errors: list[JsonObject] = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> JsonObject:
        return {
            "schema_version": self.schema_version,
            "operation": self.operation,
            "status": self.status,
            "ok": self.ok,
            "artifacts": json_safe(self.artifacts),
            "summary": json_safe(self.summary),
            "errors": json_safe(self.errors),
        }


def json_safe(value: Any) -> Any:
    """Convert common Python values to JSON-safe structures."""

    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value) and not isinstance(value, type):
        return json_safe(asdict(value))
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_safe(item) for item in value]
    return str(value)


def response_envelope(
    *,
    operation: str,
    status: str,
    ok: bool,
    artifacts: JsonObject | None = None,
    summary: JsonObject | None = None,
    errors: list[JsonObject] | None = None,
) -> JsonObject:
    return WorkbenchResponse(
        operation=operation,
        status=status,
        ok=ok,
        artifacts=artifacts or {},
        summary=summary or {},
        errors=errors or [],
    ).to_dict()


def error_envelope(
    *,
    operation: str,
    message: str,
    code: str = "error",
    status: str = "error",
    details: JsonObject | None = None,
) -> JsonObject:
    error: JsonObject = {"code": code, "message": message}
    if details:
        error["details"] = details
    return response_envelope(
        operation=operation,
        status=status,
        ok=False,
        errors=[error],
    )
