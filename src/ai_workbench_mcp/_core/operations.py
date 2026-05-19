"""Model selection, validation, quality, and analytics core wrappers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from ai_workbench_mcp.contracts import JsonObject, error_envelope
from ai_workbench_mcp.events import response_with_event
from ai_workbench_mcp.tools import model_select as model_select_tool
from ai_workbench_mcp.tools import policy_pack_select as policy_pack_select_tool
from ai_workbench_mcp.tools import quality_loop as quality_loop_tool
from ai_workbench_mcp.tools import run_analyze as run_analyze_tool
from ai_workbench_mcp.tools import validate_run as validate_run_tool

from .common import ALLOWED_RISKS, require_choice, workbench_path
from .responses import (
    model_selection_response,
    policy_pack_selection_response,
    quality_gate_response,
    run_analysis_response,
    validation_response,
)


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
    recipe: str | None = None,
    validation_profile: str | None = None,
    routing_feedback_path: str | Path | None = None,
) -> JsonObject:
    try:
        require_choice("risk", risk, ALLOWED_RISKS)
    except Exception as exc:
        return error_envelope(
            operation="workbench_select_model",
            code="model_selection_failed",
            message=str(exc),
        )
    output_path = workbench_path(out)
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
        recipe=recipe,
        validation_profile=validation_profile,
        routing_feedback_path=str(routing_feedback_path) if routing_feedback_path is not None else None,
        out=str(output_path),
    )
    try:
        payload = model_select_tool.select_model_payload(args)
    except Exception as exc:
        return error_envelope(
            operation="workbench_select_model",
            code="model_selection_failed",
            message=str(exc),
        )
    response = model_selection_response(payload, artifacts={"model_selection": output_path})
    return response_with_event(response, output_path.parent / "events.jsonl")


def select_policy_pack(
    *,
    task_text: str | None = None,
    task_type: str | None = None,
    changed_files: list[str] | None = None,
    prompt: str | None = None,
    risk: str | None = None,
) -> JsonObject:
    try:
        payload = policy_pack_select_tool.select_policy_pack_payload(
            task_text=task_text,
            task_type=task_type,
            changed_files=changed_files or [],
            prompt=prompt,
            risk=risk,
        )
    except Exception as exc:
        return error_envelope(
            operation="workbench_select_policy_pack",
            code="policy_pack_selection_failed",
            message=str(exc),
        )
    return policy_pack_selection_response(payload)


def validate_run(
    *,
    project: str,
    out_dir: str | Path,
    profile: str | None = None,
    changed_files: list[str] | None = None,
    task_test_command: str | None = None,
    report_name: str = "validation_report.json",
) -> JsonObject:
    args = SimpleNamespace(
        project=project,
        profile=profile,
        changed_files=changed_files or [],
        task_test_command=task_test_command,
        out_dir=str(out_dir),
        report_name=report_name,
    )
    report_path = workbench_path(out_dir) / report_name
    try:
        report = validate_run_tool.validate_run_payload(args)
    except Exception as exc:
        return error_envelope(
            operation="workbench_validate_run",
            code="validation_failed",
            message=str(exc),
            details={"validation_report": str(report_path)},
        )
    response = validation_response(report, artifacts={"validation_report": report_path})
    return response_with_event(response, report_path.parent / "events.jsonl")


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
    if risk is not None:
        try:
            require_choice("risk", risk, ALLOWED_RISKS)
        except Exception as exc:
            return error_envelope(
                operation="workbench_quality_gate",
                code="quality_gate_failed",
                message=str(exc),
            )
    args = SimpleNamespace(
        project=project,
        run_dir=str(run_dir),
        mode=mode,
        risk=risk,
        validation_report=str(validation_report) if validation_report is not None else None,
        review_prompt=str(review_prompt) if review_prompt is not None else None,
        review_output=str(review_output) if review_output is not None else None,
    )
    decision_path = workbench_path(run_dir) / "revision_decision.json"
    try:
        decision = quality_loop_tool.quality_gate_payload(args)
    except Exception as exc:
        return error_envelope(
            operation="workbench_quality_gate",
            code="quality_gate_failed",
            message=str(exc),
            details={"revision_decision": str(decision_path)},
        )
    response = quality_gate_response(decision, artifacts={"revision_decision": decision_path})
    return response_with_event(response, decision_path.parent / "events.jsonl")


def analyze_runs(
    *,
    runs_dir: str | Path = "runs",
    task_type: str | None = None,
    since: str | None = None,
    out_dir: str | Path | None = None,
    evals_dir: str | Path = "evals/golden_cases",
    evidence_scope: str = "all",
) -> JsonObject:
    report_dir = workbench_path(out_dir) if out_dir is not None else workbench_path(runs_dir) / "_reports"
    metrics_path = report_dir / "run_metrics.json"
    summary_path = report_dir / "run_summary.md"
    dashboard_path = report_dir / "run_dashboard.html"
    args = SimpleNamespace(
        runs_dir=str(workbench_path(runs_dir)),
        task_type=task_type,
        since=since,
        out_dir=str(workbench_path(out_dir)) if out_dir is not None else None,
        evals_dir=str(workbench_path(evals_dir)),
        evidence_scope=evidence_scope,
    )
    try:
        metrics = run_analyze_tool.run_analysis_payload(args)
    except Exception as exc:
        return error_envelope(
            operation="workbench_analyze_runs",
            code="run_analysis_failed",
            message=str(exc),
            details={"run_metrics": str(metrics_path), "dashboard": str(dashboard_path)},
        )
    response = run_analysis_response(
        metrics,
        artifacts={"run_metrics": metrics_path, "run_summary": summary_path, "dashboard": dashboard_path},
    )
    return response_with_event(response, report_dir / "events.jsonl")

