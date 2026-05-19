"""Shared path, JSON, and validation helpers for core operations."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

from ai_workbench_mcp.contracts import JsonObject, error_envelope


WORKBENCH_ROOT = Path(__file__).resolve().parents[3]
ALLOWED_RISKS = {"low", "medium", "high"}
ALLOWED_EXECUTION_HOSTS = {"goose", "codex", "ci", "other"}
ALLOWED_RUN_STATUSES = {"started", "in_progress", "completed", "blocked"}
ALLOWED_RECORD_MODEL_OUTPUT_STATUSES = {"response_captured"}


def read_json_artifact(path: str | Path) -> JsonObject:
    file_path = Path(path)
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {"value": payload}


def run_tool(
    *,
    operation: str,
    args: list[str],
    accepted_exit_codes: set[int] | None = None,
) -> subprocess.CompletedProcess[str] | JsonObject:
    accepted = accepted_exit_codes or {0}
    result = subprocess.run(
        [sys.executable, *args],
        cwd=WORKBENCH_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode in accepted:
        return result
    return error_envelope(
        operation=operation,
        code="tool_execution_failed",
        message=f"{operation} exited with status {result.returncode}.",
        details={
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        },
    )


def append_optional(command: list[str], flag: str, value: object | None) -> None:
    if value is not None:
        command.extend([flag, str(value)])


def workbench_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else WORKBENCH_ROOT / candidate


def require_choice(name: str, value: str, allowed: set[str]) -> None:
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ValueError(f"{name} must be one of: {choices}.")


def jsonl_entries(path: Path) -> list[JsonObject]:
    if not path.exists():
        return []
    entries: list[JsonObject] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def has_jsonl_decision(path: Path, decision: str) -> bool:
    return any(entry.get("decision") == decision for entry in jsonl_entries(path))


def write_json(path: Path, payload: JsonObject) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def confidence(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

