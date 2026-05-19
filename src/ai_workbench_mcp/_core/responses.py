"""Response-envelope builders for Workbench MCP operations."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ai_workbench_mcp.contracts import JsonObject, response_envelope

from .common import read_json_artifact


def model_selection_response(selection: JsonObject, artifacts: JsonObject | None = None) -> JsonObject:
    selected_model = selection.get("selected_model", {})
    selected_model = selected_model if isinstance(selected_model, dict) else {}
    routing_feedback = selection.get("routing_feedback", {})
    routing_feedback = routing_feedback if isinstance(routing_feedback, dict) else {}
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
            "routing_feedback_status": routing_feedback.get("status"),
            "routing_feedback_recommendation": routing_feedback.get("recommendation"),
            "routing_feedback_candidate_key": routing_feedback.get("candidate_key"),
        },
    )


def policy_pack_selection_response(payload: JsonObject, artifacts: JsonObject | None = None) -> JsonObject:
    status = str(payload.get("status") or "selected")
    return response_envelope(
        operation="workbench_select_policy_pack",
        status=status,
        ok=bool(payload.get("ok", status == "selected")),
        artifacts=artifacts,
        summary={
            "recommended_policy_pack": payload.get("recommended_policy_pack"),
            "recommended_validation_profile": payload.get("recommended_validation_profile"),
            "profile_selection_mode": payload.get("profile_selection_mode"),
            "reason": payload.get("reason"),
            "matched_signals": payload.get("matched_signals"),
            "confidence": payload.get("confidence"),
            "candidate_policy_packs": payload.get("candidate_policy_packs"),
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
            "evidence_scope": metrics.get("evidence_scope"),
            "excluded_runs_total": metrics.get("excluded_runs_total"),
            "excluded_runs_by_reason": metrics.get("excluded_runs_by_reason"),
            "runs_passed": metrics.get("runs_passed"),
            "runs_failed": metrics.get("runs_failed"),
            "runs_needs_review": metrics.get("runs_needs_review"),
            "workflow_signoff_pass_rate": metrics.get("workflow_signoff_pass_rate"),
            "workflow_needs_review_rate": metrics.get("workflow_needs_review_rate"),
            "average_confidence": metrics.get("average_confidence"),
            "accepted_runs_total": metrics.get("accepted_runs_total"),
            "review_required_runs_total": metrics.get("review_required_runs_total"),
            "failed_runs_total": metrics.get("failed_runs_total"),
            "acceptance_rate": metrics.get("acceptance_rate"),
            "outcome_counts": metrics.get("outcome_counts"),
            "accepted_runs_by_recipe": metrics.get("accepted_runs_by_recipe"),
            "accepted_runs_by_execution_host": metrics.get("accepted_runs_by_execution_host"),
            "accepted_runs_by_response_source": metrics.get("accepted_runs_by_response_source"),
            "execution_host_counts": metrics.get("execution_host_counts"),
            "response_source_counts": metrics.get("response_source_counts"),
            "quality_gate_outcomes": metrics.get("quality_gate_outcomes"),
        },
    )


def open_run_response(payload: JsonObject, artifacts: JsonObject | None = None) -> JsonObject:
    summary = {
        "run_id": payload.get("run_id"),
        "project": payload.get("project"),
        "task": payload.get("task"),
        "prompt": payload.get("prompt"),
        "risk": payload.get("risk"),
        "execution_host": payload.get("execution_host"),
        "recipe": payload.get("recipe"),
        "run_dir": payload.get("run_dir"),
        "docs_read": payload.get("docs_read"),
        "files_considered": payload.get("files_considered"),
        "git_status": payload.get("git_status"),
    }
    for key in (
        "policy_pack",
        "validation_profile",
        "policy_pack_selection_mode",
        "policy_pack_selection_confidence",
    ):
        if key in payload:
            summary[key] = payload.get(key)
    return response_envelope(
        operation="workbench_open_run",
        status="opened",
        ok=True,
        artifacts=artifacts,
        summary=summary,
    )


def record_execution_response(payload: JsonObject, artifacts: JsonObject | None = None) -> JsonObject:
    status = str(payload.get("status") or "response_captured")
    files_touched = payload.get("files_touched", [])
    return response_envelope(
        operation="workbench_record_execution",
        status=status,
        ok=status == "response_captured",
        artifacts=artifacts,
        summary={
            "run_id": payload.get("run_id"),
            "project": payload.get("project"),
            "run_dir": payload.get("run_dir"),
            "model_output_status": status,
            "run_status": payload.get("run_status"),
            "execution_host": payload.get("execution_host"),
            "response_source": payload.get("response_source"),
            "provider": payload.get("provider"),
            "model": payload.get("model"),
            "files_touched": len(files_touched) if isinstance(files_touched, list) else 0,
            "duplicate_ignored": bool(payload.get("duplicate_ignored", False)),
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


def run_analysis_file_response(
    path: str | Path,
    summary_path: str | Path | None = None,
    dashboard_path: str | Path | None = None,
) -> JsonObject:
    artifacts: dict[str, Any] = {"run_metrics": Path(path)}
    if summary_path is not None:
        artifacts["run_summary"] = Path(summary_path)
    if dashboard_path is not None:
        artifacts["dashboard"] = Path(dashboard_path)
    return run_analysis_response(read_json_artifact(path), artifacts=artifacts)

