"""Contract wrappers around existing Workbench core artifacts."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

from .contracts import JsonObject, error_envelope, response_envelope


WORKBENCH_ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = WORKBENCH_ROOT / "tools"


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


def _append_optional(command: list[str], flag: str, value: object | None) -> None:
    if value is not None:
        command.extend([flag, str(value)])


def _workbench_path(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else WORKBENCH_ROOT / candidate


def _load_model_select_module() -> Any:
    tools_dir = str(TOOLS_DIR)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import model_select as model_select_module

    return model_select_module


def _load_validate_run_module() -> Any:
    tools_dir = str(TOOLS_DIR)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import validate_run as validate_run_module

    return validate_run_module


def _load_quality_loop_module() -> Any:
    tools_dir = str(TOOLS_DIR)
    if tools_dir not in sys.path:
        sys.path.insert(0, tools_dir)
    import quality_loop as quality_loop_module

    return quality_loop_module


def model_selection_response(selection: JsonObject, artifacts: JsonObject | None = None) -> JsonObject:
    selected_model = selection.get("selected_model", {})
    selected_model = selected_model if isinstance(selected_model, dict) else {}
    status = str(selection.get("status") or "selected")
    return response_envelope(
        operation="workbench_select_model",
        status=status,
        ok=status == "selected",
        artifacts=artifacts,
        summary={
            "run_id": selection.get("run_id"),
            "project": selection.get("project"),
            "selected_tier": selection.get("selected_tier"),
            "provider": selected_model.get("provider"),
            "model": selected_model.get("model"),
            "risk": selection.get("risk"),
            "validation_strength": selection.get("validation_strength"),
            "complexity_score": selection.get("complexity_score"),
            "complexity_band": selection.get("complexity_band"),
            "matched_rule": selection.get("matched_rule"),
            "reason": selection.get("reason"),
        },
    )


def validation_response(report: JsonObject, artifacts: JsonObject | None = None) -> JsonObject:
    status = str(report.get("overall_status") or "unknown")
    summary = report.get("summary", {})
    summary = summary if isinstance(summary, dict) else {}
    return response_envelope(
        operation="workbench_validate_run",
        status=status,
        ok=status == "passed" and bool(report.get("sign_off_ready")),
        artifacts=artifacts,
        summary={
            "run_id": report.get("run_id"),
            "project": report.get("project"),
            "profile": report.get("profile"),
            "sign_off_ready": report.get("sign_off_ready"),
            "confidence": report.get("confidence"),
            "commands_passed": summary.get("commands_passed"),
            "commands_failed": summary.get("commands_failed"),
            "checks_passed": summary.get("checks_passed"),
            "checks_needs_review": summary.get("checks_needs_review"),
            "checks_failed": summary.get("checks_failed"),
        },
    )


def quality_gate_response(decision: JsonObject, artifacts: JsonObject | None = None) -> JsonObject:
    status = str(decision.get("final_status") or "unknown")
    blocking = decision.get("blocking_findings", [])
    non_blocking = decision.get("non_blocking_findings", [])
    blocking_count = len(blocking) if isinstance(blocking, list) else 0
    non_blocking_count = len(non_blocking) if isinstance(non_blocking, list) else 0
    return response_envelope(
        operation="workbench_quality_gate",
        status=status,
        ok=status == "accepted",
        artifacts=artifacts,
        summary={
            "loop_type": decision.get("loop_type"),
            "required": decision.get("required"),
            "reason": decision.get("reason"),
            "next_action": decision.get("next_action"),
            "accepted_pass": decision.get("accepted_pass"),
            "blocking_findings": blocking_count,
            "non_blocking_findings": non_blocking_count,
            "authoritative_model_output": decision.get("authoritative_model_output"),
            "authoritative_validation_report": decision.get("authoritative_validation_report"),
        },
    )


def run_analysis_response(metrics: JsonObject, artifacts: JsonObject | None = None) -> JsonObject:
    return response_envelope(
        operation="workbench_analyze_runs",
        status="completed",
        ok=True,
        artifacts=artifacts,
        summary={
            "runs_total": metrics.get("runs_total"),
            "runs_passed": metrics.get("runs_passed"),
            "runs_failed": metrics.get("runs_failed"),
            "runs_needs_review": metrics.get("runs_needs_review"),
            "workflow_signoff_pass_rate": metrics.get("workflow_signoff_pass_rate"),
            "workflow_needs_review_rate": metrics.get("workflow_needs_review_rate"),
            "average_confidence": metrics.get("average_confidence"),
        },
    )


def model_selection_file_response(path: str | Path) -> JsonObject:
    return model_selection_response(
        read_json_artifact(path),
        artifacts={"model_selection": Path(path)},
    )


def validation_file_response(path: str | Path) -> JsonObject:
    return validation_response(
        read_json_artifact(path),
        artifacts={"validation_report": Path(path)},
    )


def quality_gate_file_response(path: str | Path) -> JsonObject:
    return quality_gate_response(
        read_json_artifact(path),
        artifacts={"revision_decision": Path(path)},
    )


def run_analysis_file_response(path: str | Path, summary_path: str | Path | None = None) -> JsonObject:
    artifacts: dict[str, Any] = {"run_metrics": Path(path)}
    if summary_path is not None:
        artifacts["run_summary"] = Path(summary_path)
    return run_analysis_response(read_json_artifact(path), artifacts=artifacts)


def select_model(
    *,
    project: str,
    task_type: str,
    risk: str,
    out: str | Path,
    validation_strength: str = "medium",
    prompt: str | None = None,
    complexity_score: int | None = None,
    test_complexity_level: int | None = None,
    instruction_following: str = "normal",
    task_text: str | None = None,
    code_files: list[str] | None = None,
) -> JsonObject:
    output_path = _workbench_path(out)
    args = SimpleNamespace(
        project=project,
        task_type=task_type,
        risk=risk,
        validation_strength=validation_strength,
        prompt=prompt,
        complexity_score=complexity_score,
        test_complexity_level=test_complexity_level,
        instruction_following=instruction_following,
        task_text=task_text,
        code_file=code_files or [],
        out=str(output_path),
    )
    try:
        payload = _load_model_select_module().select_model_payload(args)
    except Exception as exc:
        return error_envelope(
            operation="workbench_select_model",
            code="model_selection_failed",
            message=str(exc),
        )
    return model_selection_response(payload, artifacts={"model_selection": output_path})


def validate_run(
    *,
    project: str,
    out_dir: str | Path,
    profile: str | None = None,
    changed_files: list[str] | None = None,
    report_name: str = "validation_report.json",
) -> JsonObject:
    args = SimpleNamespace(
        project=project,
        profile=profile,
        changed_files=changed_files or [],
        out_dir=str(out_dir),
        report_name=report_name,
    )
    report_path = _workbench_path(out_dir) / report_name
    try:
        report = _load_validate_run_module().validate_run_payload(args)
    except Exception as exc:
        return error_envelope(
            operation="workbench_validate_run",
            code="validation_failed",
            message=str(exc),
            details={"validation_report": str(report_path)},
        )
    return validation_response(report, artifacts={"validation_report": report_path})


def quality_gate(
    *,
    project: str,
    run_dir: str | Path,
    mode: str = "auto",
    risk: str | None = None,
    validation_report: str | Path | None = None,
    review_prompt: str | Path | None = None,
    review_output: str | Path | None = None,
) -> JsonObject:
    args = SimpleNamespace(
        project=project,
        run_dir=str(run_dir),
        mode=mode,
        risk=risk,
        validation_report=str(validation_report) if validation_report is not None else None,
        review_prompt=str(review_prompt) if review_prompt is not None else None,
        review_output=str(review_output) if review_output is not None else None,
    )
    decision_path = _workbench_path(run_dir) / "revision_decision.json"
    try:
        decision = _load_quality_loop_module().quality_gate_payload(args)
    except Exception as exc:
        return error_envelope(
            operation="workbench_quality_gate",
            code="quality_gate_failed",
            message=str(exc),
            details={"revision_decision": str(decision_path)},
        )
    return quality_gate_response(decision, artifacts={"revision_decision": decision_path})


def analyze_runs(
    *,
    runs_dir: str | Path = "runs",
    task_type: str | None = None,
    since: str | None = None,
    out_dir: str | Path | None = None,
    evals_dir: str | Path = "evals/golden_cases",
) -> JsonObject:
    command = [
        str(TOOLS_DIR / "run_analyze.py"),
        "--runs-dir",
        str(runs_dir),
        "--evals-dir",
        str(evals_dir),
    ]
    _append_optional(command, "--task-type", task_type)
    _append_optional(command, "--since", since)
    _append_optional(command, "--out-dir", out_dir)

    result = run_tool(operation="workbench_analyze_runs", args=command)
    if isinstance(result, dict):
        return result

    report_dir = _workbench_path(out_dir) if out_dir is not None else _workbench_path(runs_dir) / "_reports"
    metrics_path = report_dir / "run_metrics.json"
    summary_path = report_dir / "run_summary.md"
    if not metrics_path.exists():
        return error_envelope(
            operation="workbench_analyze_runs",
            code="missing_run_metrics",
            message="Run analysis completed without writing run_metrics.json.",
            details={"run_metrics": str(metrics_path)},
        )
    return run_analysis_file_response(metrics_path, summary_path=summary_path)
