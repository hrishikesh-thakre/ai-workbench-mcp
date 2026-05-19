"""Run lifecycle operations for the public core facade."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

from ai_workbench_mcp.contracts import JsonObject, error_envelope
from ai_workbench_mcp.events import response_with_event
from ai_workbench_mcp.tools import context_scout as context_scout_tool
from ai_workbench_mcp.tools import model_handoff as model_handoff_tool
from ai_workbench_mcp.tools import run_log as run_log_tool

from .common import (
    ALLOWED_EXECUTION_HOSTS,
    ALLOWED_RECORD_MODEL_OUTPUT_STATUSES,
    ALLOWED_RISKS,
    ALLOWED_RUN_STATUSES,
    has_jsonl_decision,
    read_json_artifact,
    require_choice,
    write_json,
)
from .policy_selection import policy_selection_metadata, run_policy_pack_selection
from .responses import open_run_response, record_execution_response


def final_prompt_text(
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


def selected_model_summary(selection: JsonObject) -> tuple[str | None, str | None]:
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
        require_choice("risk", risk, ALLOWED_RISKS)
        require_choice("execution_host", execution_host, ALLOWED_EXECUTION_HOSTS)
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

        policy_selection = run_policy_pack_selection(
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
            write_json(policy_selection_path, policy_selection)
            if bool(policy_selection.get("blocking", False)):
                raise ValueError(str(policy_selection.get("reason") or "Policy-pack selection failed."))
        selected_policy_metadata = policy_selection_metadata(policy_selection)

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
        write_json(task_metadata_path, task_metadata)

        final_prompt_path = output_dir / "final_prompt.md"
        final_prompt_path.write_text(
            final_prompt_text(
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
        if not has_jsonl_decision(run_log_path, "run_opened"):
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
        require_choice("model_output_status", model_output_status, ALLOWED_RECORD_MODEL_OUTPUT_STATUSES)
        require_choice("run_status", run_status, ALLOWED_RUN_STATUSES)
        context_scout = context_scout_tool
        project_config = context_scout.load_project_config(project)
        run_dir_path = context_scout.resolve_cli_path(str(run_dir), project_config.root)
        model_selection_path = run_dir_path / "model_selection.json"
        final_prompt_path = run_dir_path / "final_prompt.md"
        model_output_path = run_dir_path / "model_output.md"
        run_log_path = run_dir_path / "run_log.jsonl"

        selection = read_json_artifact(model_selection_path)
        selected_tier = selection.get("selected_tier")
        selected_provider, selected_model = selected_model_summary(selection)
        prompt_name = selection.get("prompt") or "unknown"
        task_metadata = read_json_artifact(run_dir_path / "task_metadata.json")
        task_text = task_metadata.get("task") or selection.get("task_text") or ""
        execution_host = str(task_metadata.get("execution_host") or "goose")
        touched = files_touched or []

        duplicate_ignored = model_output_path.exists() and has_jsonl_decision(
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

