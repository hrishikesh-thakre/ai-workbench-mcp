"""Shared JSON response contracts for Workbench MCP operations."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
JsonObject = dict[str, Any]

V03_COMPLETE_RUN_ARTIFACTS = (
    "task_metadata.json",
    "final_prompt.md",
    "model_selection.json",
    "model_output.md",
    "validation_report.json",
    "revision_decision.json",
    "run_log.jsonl",
)
V03_ACCEPTANCE_REQUIRED_ARTIFACTS = (
    "validation_report.json",
    "revision_decision.json",
)
V03_PR_GATE_EVIDENCE = (
    ("validation_report", "validation_report.json"),
    ("revision_decision", "revision_decision.json"),
    ("model_output", "model_output.md"),
    ("run_log", "run_log.jsonl"),
)
V03_PR_GATE_OUTCOMES = ("accept", "needs_review", "block")
V03_PR_GATE_EVIDENCE_SOURCES = ("acceptance_run", "fallback_scaffold", "missing")
V03_POLICY_PACK_NAMES = (
    "docs_only",
    "low_risk_bug_fix",
    "test_fix",
    "api_contract_change",
    "security_privacy_sensitive",
)
V03_POLICY_PACK_REQUIRED_FIELDS = (
    "name",
    "version",
    "source",
    "allowed_files",
    "required_tests",
    "required_evidence",
    "review_triggers",
    "blocker_rules",
    "reason_codes",
)
V03_POLICY_PACK_REASON_CODE_KEYS = (
    "accepted",
    "required_test_missing",
    "required_test_failed",
    "required_tests_passed",
)


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
