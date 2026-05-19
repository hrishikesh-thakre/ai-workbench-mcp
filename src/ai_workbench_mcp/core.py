"""Contract wrappers around existing Workbench core artifacts."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace
from typing import Any

from .contracts import JsonObject, error_envelope, response_envelope
from .events import response_with_event
from .tools import context_scout as context_scout_tool
from .tools import model_handoff as model_handoff_tool
from .tools import model_select as model_select_tool
from .tools import policy_packs as policy_packs_tool
from .tools import policy_pack_select as policy_pack_select_tool
from .tools import quality_loop as quality_loop_tool
from .tools import run_analyze as run_analyze_tool
from .tools import run_log as run_log_tool
from .tools import validate_run as validate_run_tool


WORKBENCH_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_RISKS = {"low", "medium", "high"}
ALLOWED_EXECUTION_HOSTS = {"goose", "codex", "ci", "other"}
ALLOWED_RUN_STATUSES = {"started", "in_progress", "completed", "blocked"}
ALLOWED_RECORD_MODEL_OUTPUT_STATUSES = {"response_captured"}
AUTO_POLICY_SELECTION_MIN_CONFIDENCE = 0.7
MUTATING_TASK_TYPES = {"implementation", "bug investigation", "test development", "general investigation"}


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


def _require_choice(name: str, value: str, allowed: set[str]) -> None:
    if value not in allowed:
        choices = ", ".join(sorted(allowed))
        raise ValueError(f"{name} must be one of: {choices}.")


def _jsonl_entries(path: Path) -> list[JsonObject]:
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


def _has_jsonl_decision(path: Path, decision: str) -> bool:
    return any(entry.get("decision") == decision for entry in _jsonl_entries(path))


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


def _write_json(path: Path, payload: JsonObject) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _optional_text(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _confidence(value: object, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _policy_pack_for_profile(
    catalog: dict[str, dict[str, object]],
    validation_profile: str,
) -> str | None:
    for pack_name, pack_data in catalog.items():
        if str(pack_data.get("validation_profile", "")).strip() == validation_profile:
            return pack_name
    return None


def _policy_selection_base(
    *,
    auto_select_policy_pack: bool,
    policy_pack: str | None,
    validation_profile: str | None,
) -> JsonObject:
    return {
        "schema_version": 1,
        "operation": "workbench_select_policy_pack",
        "artifact": "policy_pack_selection",
        "selection_attempted": True,
        "auto_select_policy_pack": auto_select_policy_pack,
        "requested_policy_pack": policy_pack,
        "requested_validation_profile": validation_profile,
    }


def _manual_policy_selection(
    *,
    auto_select_policy_pack: bool,
    policy_pack: str | None,
    validation_profile: str | None,
) -> JsonObject:
    base = _policy_selection_base(
        auto_select_policy_pack=auto_select_policy_pack,
        policy_pack=policy_pack,
        validation_profile=validation_profile,
    )
    try:
        catalog = policy_packs_tool.load_policy_pack_catalog()
        selected_pack: str | None = None
        selected_profile: str | None = None

        if policy_pack is not None:
            pack_data = catalog.get(policy_pack)
            if pack_data is None:
                raise ValueError(f"Unknown policy pack: {policy_pack}")
            selected_pack = policy_pack
            selected_profile = str(pack_data.get("validation_profile", "")).strip() or None
            if selected_profile is None:
                raise ValueError(f"Policy pack {policy_pack} does not map to a validation profile.")

        if validation_profile is not None:
            profile = validate_run_tool.load_validation_profile(validation_profile)
            selected_profile = profile.name
            profile_pack = _policy_pack_for_profile(catalog, profile.name)
            profile_policy_pack = profile.policy_pack if isinstance(profile.policy_pack, dict) else {}
            profile_pack = _optional_text(profile_policy_pack.get("name")) or profile_pack
            if policy_pack is not None and selected_pack is not None:
                mapped_profile = str(catalog[selected_pack].get("validation_profile", "")).strip()
                if mapped_profile != profile.name:
                    raise ValueError(
                        "Conflicting policy_pack and validation_profile: "
                        f"{policy_pack} maps to {mapped_profile}, but validation_profile={profile.name}."
                    )
            selected_pack = profile_pack or selected_pack

        if selected_profile is None:
            raise ValueError("Manual policy-pack selection did not resolve a validation profile.")

        validate_run_tool.load_validation_profile(selected_profile)
        mode = "manual_validation_profile" if validation_profile is not None else "manual_policy_pack"
        if validation_profile is not None and policy_pack is not None:
            reason = "Explicit validation_profile was used; explicit policy_pack mapped to the same profile."
        elif validation_profile is not None:
            reason = "Explicit validation_profile was used."
        else:
            reason = "Explicit policy_pack was mapped through the catalog to its validation profile."
        return {
            **base,
            "status": "selected",
            "ok": True,
            "blocking": False,
            "policy_pack": selected_pack,
            "validation_profile": selected_profile,
            "recommended_policy_pack": selected_pack,
            "recommended_validation_profile": selected_profile,
            "profile_selection_mode": mode,
            "policy_pack_selection_mode": mode,
            "confidence": 1.0,
            "reason": reason,
            "matched_signals": [],
            "candidate_policy_packs": list(policy_packs_tool.PRODUCT_POLICY_PACK_NAMES),
        }
    except Exception as exc:
        return {
            **base,
            "status": "error",
            "ok": False,
            "blocking": True,
            "policy_pack": None,
            "validation_profile": validation_profile,
            "recommended_policy_pack": None,
            "recommended_validation_profile": validation_profile,
            "profile_selection_mode": "manual_error",
            "policy_pack_selection_mode": "manual_error",
            "confidence": 0.0,
            "reason": str(exc),
            "matched_signals": [],
            "candidate_policy_packs": list(policy_packs_tool.PRODUCT_POLICY_PACK_NAMES),
        }


def _auto_policy_selection_not_selected(base: JsonObject, reason: str) -> JsonObject:
    return {
        **base,
        "status": "not_selected",
        "ok": False,
        "blocking": False,
        "policy_pack": None,
        "validation_profile": None,
        "recommended_policy_pack": None,
        "recommended_validation_profile": None,
        "profile_selection_mode": "auto_advisory",
        "policy_pack_selection_mode": "auto_advisory",
        "confidence": 0.0,
        "reason": reason,
        "matched_signals": [],
        "candidate_policy_packs": list(policy_packs_tool.PRODUCT_POLICY_PACK_NAMES),
    }


def _automatic_policy_selection(
    *,
    task: str,
    task_type: str,
    prompt: str,
    risk: str,
    changed_files: list[str] | None,
) -> JsonObject:
    base = _policy_selection_base(
        auto_select_policy_pack=True,
        policy_pack=None,
        validation_profile=None,
    )
    try:
        selector_payload = policy_pack_select_tool.select_policy_pack_payload(
            task_text=task,
            task_type=task_type,
            changed_files=changed_files or [],
            prompt=prompt,
            risk=risk,
        )
    except Exception as exc:
        return _auto_policy_selection_not_selected(base, f"Automatic policy-pack selection failed: {exc}")

    status = str(selector_payload.get("status") or "")
    ok = bool(selector_payload.get("ok", status == "selected"))
    selected_pack = _optional_text(selector_payload.get("recommended_policy_pack"))
    selected_profile = _optional_text(selector_payload.get("recommended_validation_profile"))
    if not ok or status != "selected" or selected_pack is None or selected_profile is None:
        return _auto_policy_selection_not_selected(
            base,
            "Automatic policy-pack selection did not return a usable policy pack and validation profile.",
        )

    confidence = _confidence(selector_payload.get("confidence"), 0.0)
    if confidence < AUTO_POLICY_SELECTION_MIN_CONFIDENCE:
        return _auto_policy_selection_not_selected(
            base,
            "Automatic policy-pack selection confidence "
            f"{confidence:.2f} is below the required {AUTO_POLICY_SELECTION_MIN_CONFIDENCE:.2f}; "
            "pass validation_profile or policy_pack explicitly.",
        )

    if not changed_files and selected_pack != "docs_only" and task_type in MUTATING_TASK_TYPES:
        return _auto_policy_selection_not_selected(
            base,
            "Changed files are required before automatic policy-pack selection can choose a "
            f"mutating validation profile for task_type={task_type}.",
        )

    try:
        catalog = policy_packs_tool.load_policy_pack_catalog()
        pack_data = catalog.get(selected_pack)
        if pack_data is None:
            raise ValueError(f"recommended policy pack is not in the catalog: {selected_pack}")
        mapped_profile = str(pack_data.get("validation_profile", "")).strip()
        if mapped_profile != selected_profile:
            raise ValueError(
                f"recommended policy pack {selected_pack} maps to {mapped_profile}, "
                f"not {selected_profile}"
            )
        validate_run_tool.load_validation_profile(selected_profile)
    except Exception as exc:
        return _auto_policy_selection_not_selected(
            base,
            f"Automatic policy-pack selection was not usable: {exc}",
        )

    mode = str(selector_payload.get("profile_selection_mode") or "auto_advisory")
    return {
        **base,
        **selector_payload,
        "operation": "workbench_select_policy_pack",
        "artifact": "policy_pack_selection",
        "selection_attempted": True,
        "auto_select_policy_pack": True,
        "requested_policy_pack": None,
        "requested_validation_profile": None,
        "status": "selected",
        "ok": True,
        "blocking": False,
        "policy_pack": selected_pack,
        "validation_profile": selected_profile,
        "profile_selection_mode": mode,
        "policy_pack_selection_mode": mode,
        "confidence": confidence,
    }


def _run_policy_pack_selection(
    *,
    task: str,
    task_type: str,
    prompt: str,
    risk: str,
    changed_files: list[str] | None,
    auto_select_policy_pack: bool,
    policy_pack: str | None,
    validation_profile: str | None,
) -> JsonObject | None:
    requested_pack = _optional_text(policy_pack)
    requested_profile = _optional_text(validation_profile)
    if requested_pack is None and requested_profile is None and not auto_select_policy_pack:
        return None
    if requested_pack is not None or requested_profile is not None:
        return _manual_policy_selection(
            auto_select_policy_pack=auto_select_policy_pack,
            policy_pack=requested_pack,
            validation_profile=requested_profile,
        )
    return _automatic_policy_selection(
        task=task,
        task_type=task_type,
        prompt=prompt,
        risk=risk,
        changed_files=changed_files,
    )


def _policy_selection_metadata(selection: JsonObject | None) -> JsonObject:
    if not selection or selection.get("status") != "selected":
        return {}
    validation_profile = _optional_text(selection.get("validation_profile"))
    if validation_profile is None:
        return {}
    mode = _optional_text(selection.get("policy_pack_selection_mode")) or _optional_text(
        selection.get("profile_selection_mode")
    )
    return {
        "policy_pack": _optional_text(selection.get("policy_pack")),
        "validation_profile": validation_profile,
        "policy_pack_selection_mode": mode,
        "policy_pack_selection_confidence": _confidence(selection.get("confidence"), 0.0),
    }


def _final_prompt_text(
    *,
    run_id: str,
    project: str,
    task: str,
    prompt: str,
    risk: str,
    task_type: str,
    context_profile: str,
    execution_host: str,
) -> str:
    return "\n".join(
        [
            "# Final Prompt",
            "",
            "## Run Metadata",
            "",
            f"- Run ID: `{run_id}`",
            f"- Project: `{project}`",
            f"- Execution Host: `{execution_host}`",
            f"- Mode: `{execution_host}`",
            f"- Task Type: `{task_type}`",
            f"- Risk: `{risk}`",
            f"- Prompt: `{Path(prompt).stem}`",
            f"- Context Profile: `{context_profile}`",
            "",
            "## Task Summary",
            "",
            task,
            "",
            "## Approved Prompt Reference",
            "",
            f"Use approved prompt `{Path(prompt).stem}` with the run metadata and task summary above.",
            "",
        ]
    )


def _selected_model_summary(selection: JsonObject) -> tuple[str | None, str | None]:
    selected_model = selection.get("selected_model", {})
    if not isinstance(selected_model, dict):
        return None, None
    provider = selected_model.get("provider")
    model = selected_model.get("model")
    return str(provider) if provider is not None else None, str(model) if model is not None else None


def open_run(
    *,
    project: str,
    task: str,
    run_dir: str | Path | None = None,
    prompt: str = "implement_request_change_request",
    risk: str = "medium",
    context_profile: str | None = None,
    recipe: str | None = None,
    changed_files: list[str] | None = None,
    docs: list[str] | None = None,
    include_diff: bool = False,
    execution_host: str = "goose",
    auto_select_policy_pack: bool = True,
    policy_pack: str | None = None,
    validation_profile: str | None = None,
) -> JsonObject:
    try:
        _require_choice("risk", risk, ALLOWED_RISKS)
        _require_choice("execution_host", execution_host, ALLOWED_EXECUTION_HOSTS)
        context_scout = context_scout_tool
        project_config = context_scout.load_project_config(project)
        prompt_path = context_scout.resolve_prompt_path(prompt, project_config.prompts_dir)
        if not prompt_path.exists():
            raise FileNotFoundError(f"Approved prompt file not found: {prompt_path}")
        profile_name = context_profile or project_config.default_context_profile
        task_type = context_scout.classify_task(prompt)

        scout_args = SimpleNamespace(
            project=project,
            task=task,
            prompt=prompt,
            risk=risk,
            include_diff=include_diff,
            docs=docs or [],
            changed_files=changed_files or [],
            context_profile=context_profile,
            out_dir=str(run_dir) if run_dir is not None else None,
        )
        scout_payload = context_scout.context_scout_payload(scout_args)
        output_dir = Path(str(scout_payload["output_dir"]))
        run_id = str(scout_payload["run_id"])

        policy_selection = _run_policy_pack_selection(
            task=task,
            task_type=task_type,
            prompt=Path(prompt).stem,
            risk=risk,
            changed_files=changed_files or [],
            auto_select_policy_pack=auto_select_policy_pack,
            policy_pack=policy_pack,
            validation_profile=validation_profile,
        )
        policy_selection_path = output_dir / "policy_pack_selection.json"
        if policy_selection is not None:
            _write_json(policy_selection_path, policy_selection)
            if bool(policy_selection.get("blocking", False)):
                raise ValueError(str(policy_selection.get("reason") or "Policy-pack selection failed."))
        selected_policy_metadata = _policy_selection_metadata(policy_selection)

        task_metadata = {
            "schema_version": 1,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "run_id": run_id,
            "project": project,
            "task": task,
            "prompt": Path(prompt).stem,
            "risk": risk,
            "task_type": task_type,
            "context_profile": profile_name,
            "execution_host": execution_host,
            "recipe": recipe,
            "changed_files": changed_files or [],
            "docs": docs or [],
            "include_diff": include_diff,
            **selected_policy_metadata,
        }
        task_metadata_path = output_dir / "task_metadata.json"
        _write_json(task_metadata_path, task_metadata)

        final_prompt_path = output_dir / "final_prompt.md"
        final_prompt_path.write_text(
            _final_prompt_text(
                run_id=run_id,
                project=project,
                task=task,
                prompt=prompt,
                risk=risk,
                task_type=task_type,
                context_profile=profile_name,
                execution_host=execution_host,
            ),
            encoding="utf-8",
        )

        run_log_path = output_dir / "run_log.jsonl"
        if not _has_jsonl_decision(run_log_path, "run_opened"):
            run_log_tool.run_log_payload(
                SimpleNamespace(
                    run_id=run_id,
                    task=task,
                    decision="run_opened",
                    status="started",
                    prompt=Path(prompt).stem,
                    model_tier=None,
                    model=None,
                    validation=None,
                    first_pass_outcome=None,
                    final_outcome=None,
                    quality_loop_status=None,
                    authoritative_validation=None,
                    follow_up=None,
                    context_docs=docs or [],
                    files_touched=changed_files or [],
                    artifacts=[
                        "task_metadata.json",
                        "final_prompt.md",
                        "expert_packet.md",
                        "search_results.md",
                    ],
                    out=str(run_log_path),
                )
            )

        payload: JsonObject = {
            **scout_payload,
            "run_dir": str(output_dir),
            "task": task,
            "prompt": Path(prompt).stem,
            "risk": risk,
            "context_profile": profile_name,
            "execution_host": execution_host,
            "recipe": recipe,
            **selected_policy_metadata,
        }
    except Exception as exc:
        return error_envelope(
            operation="workbench_open_run",
            code="open_run_failed",
            message=str(exc),
        )

    response = open_run_response(
        payload,
        artifacts={
            "run_dir": output_dir,
            "task_metadata": task_metadata_path,
            "final_prompt": final_prompt_path,
            "run_log": run_log_path,
            "expert_packet": output_dir / "expert_packet.md",
            **({"policy_pack_selection": policy_selection_path} if policy_selection is not None else {}),
        },
    )
    return response_with_event(response, output_dir / "events.jsonl")


def record_execution(
    *,
    project: str,
    run_dir: str | Path,
    response_text: str,
    files_touched: list[str] | None = None,
    model_output_status: str = "response_captured",
    run_status: str = "in_progress",
    response_source: str = "goose",
    validation: str | None = None,
    follow_up: str | None = None,
) -> JsonObject:
    try:
        _require_choice("model_output_status", model_output_status, ALLOWED_RECORD_MODEL_OUTPUT_STATUSES)
        _require_choice("run_status", run_status, ALLOWED_RUN_STATUSES)
        context_scout = context_scout_tool
        project_config = context_scout.load_project_config(project)
        run_dir_path = context_scout.resolve_cli_path(str(run_dir), project_config.root)
        model_selection_path = run_dir_path / "model_selection.json"
        final_prompt_path = run_dir_path / "final_prompt.md"
        model_output_path = run_dir_path / "model_output.md"
        run_log_path = run_dir_path / "run_log.jsonl"

        selection = read_json_artifact(model_selection_path)
        selected_tier = selection.get("selected_tier")
        selected_provider, selected_model = _selected_model_summary(selection)
        prompt_name = selection.get("prompt") or "unknown"
        task_metadata = read_json_artifact(run_dir_path / "task_metadata.json")
        task_text = task_metadata.get("task") or selection.get("task_text") or ""
        execution_host = str(task_metadata.get("execution_host") or "goose")
        touched = files_touched or []

        duplicate_ignored = model_output_path.exists() and _has_jsonl_decision(
            run_log_path,
            "model_response_captured",
        )
        if duplicate_ignored:
            payload = {
                "run_id": task_metadata.get("run_id") or selection.get("run_id") or run_dir_path.name,
                "project": project,
                "run_dir": str(run_dir_path),
                "status": model_output_status,
                "run_status": run_status,
                "execution_host": execution_host,
                "response_source": response_source,
                "provider": selected_provider,
                "model": selected_model,
                "files_touched": touched,
                "duplicate_ignored": True,
            }
        else:
            handoff_payload = model_handoff_tool.model_handoff_payload(
                SimpleNamespace(
                    project=project,
                    selection=str(model_selection_path),
                    prompt=str(final_prompt_path),
                    out=str(model_output_path),
                    response_file=None,
                    response_text=response_text,
                    response_source=response_source,
                    execution_host=execution_host,
                    model_output_status=model_output_status,
                )
            )
            run_log_tool.run_log_payload(
                SimpleNamespace(
                    run_id=str(handoff_payload["run_id"]),
                    task=str(task_text),
                    decision="model_response_captured",
                    status=run_status,
                    prompt=str(prompt_name) if prompt_name is not None else None,
                    model_tier=str(selected_tier) if selected_tier is not None else None,
                    model=selected_model,
                    validation=validation,
                    first_pass_outcome=None,
                    final_outcome=None,
                    quality_loop_status=None,
                    authoritative_validation=None,
                    follow_up=follow_up,
                    context_docs=[],
                    files_touched=touched,
                    artifacts=["model_output.md"],
                    out=str(run_log_path),
                )
            )

            payload = {
                **handoff_payload,
                "project": project,
                "run_dir": str(run_dir_path),
                "run_status": run_status,
                "execution_host": execution_host,
                "files_touched": touched,
                "duplicate_ignored": False,
            }
    except Exception as exc:
        return error_envelope(
            operation="workbench_record_execution",
            code="record_execution_failed",
            message=str(exc),
        )

    response = record_execution_response(
        payload,
        artifacts={
            "model_output": model_output_path,
            "run_log": run_log_path,
        },
    )
    return response_with_event(response, run_dir_path / "events.jsonl")


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
        _require_choice("risk", risk, ALLOWED_RISKS)
    except Exception as exc:
        return error_envelope(
            operation="workbench_select_model",
            code="model_selection_failed",
            message=str(exc),
        )
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
    report_path = _workbench_path(out_dir) / report_name
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
            _require_choice("risk", risk, ALLOWED_RISKS)
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
    decision_path = _workbench_path(run_dir) / "revision_decision.json"
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
    report_dir = _workbench_path(out_dir) if out_dir is not None else _workbench_path(runs_dir) / "_reports"
    metrics_path = report_dir / "run_metrics.json"
    summary_path = report_dir / "run_summary.md"
    dashboard_path = report_dir / "run_dashboard.html"
    args = SimpleNamespace(
        runs_dir=str(_workbench_path(runs_dir)),
        task_type=task_type,
        since=since,
        out_dir=str(_workbench_path(out_dir)) if out_dir is not None else None,
        evals_dir=str(_workbench_path(evals_dir)),
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
