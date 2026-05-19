from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def read_json(file_path: Path) -> dict[str, object]:
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def read_jsonl(file_path: Path) -> list[dict[str, object]]:
    if not file_path.exists():
        return []
    rows: list[dict[str, object]] = []
    for line in file_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def evidence_scope_for(args: argparse.Namespace) -> str:
    scope = str(getattr(args, "evidence_scope", "all") or "all")
    if scope not in {"all", "complete"}:
        raise ValueError(f"invalid_evidence_scope={scope}")
    return scope


def missing_complete_evidence(run_dir: Path) -> list[str]:
    required = ("run_log.jsonl", "validation_report.json", "revision_decision.json")
    return [artifact_name for artifact_name in required if not (run_dir / artifact_name).exists()]


def exclusion_reason_for_missing_artifact(artifact_name: str) -> str:
    return f"missing_{artifact_name.removesuffix('.json').removesuffix('.jsonl')}"


def run_created_at(logs: list[dict[str, object]]) -> str:
    if not logs:
        return ""
    return str(logs[0].get("timestamp", ""))


def task_type_for(run_dir: Path, logs: list[dict[str, object]]) -> str:
    selection = read_json(run_dir / "model_selection.json")
    task_type = selection.get("task_type") or selection.get("workflow_mode")
    if task_type:
        return str(task_type)
    for row in reversed(logs):
        prompt = row.get("prompt")
        if prompt:
            return str(prompt)
    return "unknown"


def eligible_for_golden_case(run_dir: Path) -> bool:
    required = ["expert_packet.md", "final_prompt.md", "model_output.md", "validation_report.json"]
    return all((run_dir / artifact).exists() for artifact in required)


def selection_for(run_dir: Path) -> dict[str, object]:
    return read_json(run_dir / "model_selection.json")


def latest_tier(logs: list[dict[str, object]], selection: dict[str, object]) -> str:
    tier = str(selection.get("selected_tier", ""))
    if tier:
        return tier
    for row in reversed(logs):
        row_tier = row.get("model_tier")
        if row_tier and str(row_tier) != "not_selected":
            return str(row_tier)
    return "unknown"


def final_prompt_name(selection: dict[str, object], logs: list[dict[str, object]]) -> str:
    prompt = selection.get("prompt")
    if prompt:
        return str(prompt)
    for row in reversed(logs):
        row_prompt = row.get("prompt")
        if row_prompt:
            return str(row_prompt)
    return "unknown"


def task_metadata_for(run_dir: Path) -> dict[str, object]:
    return read_json(run_dir / "task_metadata.json")


def read_text_if_exists(file_path: Path) -> str:
    if not file_path.exists():
        return ""
    return file_path.read_text(encoding="utf-8", errors="replace")


def markdown_field_value(text: str, field_name: str) -> str | None:
    pattern = rf"^-\s*{re.escape(field_name)}:\s*`?([^`\n]+?)`?\s*$"
    match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


def execution_host_for(metadata: dict[str, object]) -> str:
    execution_host = metadata.get("execution_host")
    return str(execution_host) if execution_host else "goose"


def response_source_for(run_dir: Path) -> str:
    text = read_text_if_exists(run_dir / "model_output.md")
    response_source = markdown_field_value(text, "Response Source")
    return response_source or "unknown"


def scan_eval_results(runs_dir: Path) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    reports_dir = runs_dir / "_reports"
    for result_path in runs_dir.rglob("eval_result*.json"):
        if reports_dir in result_path.parents:
            continue
        payload = read_json(result_path)
        if payload:
            payload["_path"] = str(result_path)
            payload["_run_id"] = result_path.parent.name
            payload["_run_dir"] = str(result_path.parent)
            results.append(payload)
    return results


def scan_model_eval_results(runs_dir: Path) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for metadata_path in runs_dir.glob("*/model_eval_metadata.json"):
        metadata = read_json(metadata_path)
        score = read_json(metadata_path.parent / "score_report.json")
        if not metadata and not score:
            continue
        combined = {
            **metadata,
            "score_report": score,
            "_path": str(metadata_path),
            "_run_id": metadata_path.parent.name,
        }
        results.append(combined)
    return results


def scan_model_eval_matrices(runs_dir: Path) -> list[dict[str, object]]:
    reports_dir = runs_dir / "_reports"
    if not reports_dir.exists():
        return []
    matrices: list[dict[str, object]] = []
    for report_path in reports_dir.glob("model_eval_matrix*.json"):
        payload = read_json(report_path)
        if payload:
            payload["_path"] = str(report_path)
            matrices.append(payload)
    return matrices


def scan_prompt_normalizer_evals(runs_dir: Path) -> list[dict[str, object]]:
    reports_dir = runs_dir / "_reports"
    if not reports_dir.exists():
        return []
    reports: list[dict[str, object]] = []
    for report_path in reports_dir.glob("prompt_normalizer_eval*.json"):
        payload = read_json(report_path)
        if payload:
            payload["_path"] = str(report_path)
            reports.append(payload)
    return reports


def golden_case_count(evals_dir: Path) -> int:
    if not evals_dir.exists():
        return 0
    return len([path for path in evals_dir.glob("*.json") if path.is_file()])


def scan_model_call_metadata(runs_dir: Path) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    reports_dir = runs_dir / "_reports"
    for metadata_path in runs_dir.rglob("model_call_metadata.json"):
        if reports_dir in metadata_path.parents:
            continue
        payload = read_json(metadata_path)
        if payload:
            payload["_path"] = str(metadata_path)
            payload["_run_id"] = metadata_path.parent.name
            results.append(payload)
    return results

