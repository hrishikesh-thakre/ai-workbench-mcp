"""Best-effort local event envelopes for Workbench core operations."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from uuid import uuid4

from .contracts import JsonObject, SCHEMA_VERSION, json_safe


EVENT_TYPE = "workbench.operation.completed"
EVENT_SOURCE = "ai_workbench_mcp"


def _dict_value(payload: JsonObject, key: str) -> JsonObject:
    value = payload.get(key, {})
    return value if isinstance(value, dict) else {}


def _derive_run_id(summary: JsonObject, artifacts: JsonObject) -> object | None:
    if summary.get("run_id") is not None:
        return summary.get("run_id")
    run_dir = summary.get("run_dir") or artifacts.get("run_dir")
    if run_dir:
        return Path(str(run_dir)).name
    for key in ("model_selection", "model_output", "validation_report", "revision_decision"):
        artifact = artifacts.get(key)
        if artifact:
            return Path(str(artifact)).parent.name
    return None


def build_event(response: JsonObject) -> JsonObject:
    """Build an operation event from the final public response envelope."""

    summary = _dict_value(response, "summary")
    artifacts = _dict_value(response, "artifacts")
    return {
        "schema_version": SCHEMA_VERSION,
        "event_id": uuid4().hex,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "event_type": EVENT_TYPE,
        "source": EVENT_SOURCE,
        "operation": response.get("operation"),
        "status": response.get("status"),
        "ok": response.get("ok"),
        "summary": json_safe(summary),
        "artifacts": json_safe(artifacts),
        "errors": json_safe(response.get("errors", [])),
        "run_id": json_safe(_derive_run_id(summary, artifacts)),
        "project": json_safe(summary.get("project")),
    }


def append_jsonl(file_path: Path, payload: JsonObject) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(json_safe(payload), separators=(",", ":")) + "\n")


def append_response_event(file_path: Path, response: JsonObject) -> bool:
    """Append an event, swallowing all write/build failures."""

    try:
        append_jsonl(file_path, build_event(response))
    except Exception:
        return False
    return True


def response_with_event(response: JsonObject, file_path: Path) -> JsonObject:
    """Return response plus artifacts.events only when event append succeeds."""

    artifacts = _dict_value(response, "artifacts")
    response_with_events_artifact = {
        **response,
        "artifacts": {
            **artifacts,
            "events": str(file_path),
        },
    }
    try:
        if append_response_event(file_path, response_with_events_artifact):
            return response_with_events_artifact
    except Exception:
        return response
    return response
