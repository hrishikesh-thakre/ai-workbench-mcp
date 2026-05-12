from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

from context_scout import load_project_config, relative_path, resolve_cli_path
from response_format import normalize_response_text


@dataclass
class FinalPromptSummary:
    run_id: str | None
    project: str | None
    mode: str | None
    task_type: str | None
    risk: str | None
    task: str
    text: str


@dataclass
class ModelSelectionSummary:
    run_id: str | None
    project: str | None
    selected_tier: str
    provider: str
    model: str
    reason: str | None
    prompt: str | None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare a manual model handoff or capture a supplied response into model_output.md."
    )
    parser.add_argument("--project", required=True, help="Project key from configs/projects.yaml.")
    parser.add_argument("--selection", required=True, help="Path to model_selection.json.")
    parser.add_argument("--prompt", required=True, help="Path to final_prompt.md.")
    parser.add_argument("--out", required=True, help="Path for model_output.md.")
    parser.add_argument(
        "--response-file",
        help="Optional path to a captured model response file. If supplied, the response is written into model_output.md.",
    )
    return parser


def read_text(file_path: Path) -> str:
    return file_path.read_text(encoding="utf-8", errors="replace")


def parse_field(text: str, pattern: str) -> str | None:
    match = re.search(pattern, text)
    if match:
        return match.group(1)
    return None


def get_section_lines(text: str, heading: str) -> list[str]:
    lines = text.splitlines()
    collected: list[str] = []
    in_section = False
    for line in lines:
        if line.strip() == heading:
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            collected.append(line)
    return collected


def parse_section_text(text: str, heading: str) -> str:
    return "\n".join(line.rstrip() for line in get_section_lines(text, heading)).strip()


def parse_final_prompt(file_path: Path) -> FinalPromptSummary:
    text = read_text(file_path)
    return FinalPromptSummary(
        run_id=parse_field(text, r"- Run ID: `([^`]+)`"),
        project=parse_field(text, r"- Project: `([^`]+)`"),
        mode=parse_field(text, r"- Mode: `([^`]+)`"),
        task_type=parse_field(text, r"- Task Type: `([^`]+)`"),
        risk=parse_field(text, r"- Risk: `([^`]+)`"),
        task=parse_section_text(text, "## Task Summary"),
        text=text,
    )


def parse_model_selection(file_path: Path) -> ModelSelectionSummary:
    import json

    payload = json.loads(read_text(file_path))
    selected_model = payload.get("selected_model", {})
    return ModelSelectionSummary(
        run_id=payload.get("run_id"),
        project=payload.get("project"),
        selected_tier=str(payload.get("selected_tier", "unknown")),
        provider=str(selected_model.get("provider", "unknown")),
        model=str(selected_model.get("model", "unknown")),
        reason=payload.get("reason"),
        prompt=payload.get("prompt"),
    )

def determine_handoff_reason(selection: ModelSelectionSummary) -> str:
    if selection.provider == "human":
        return "Selected tier requires manual human review rather than automated model execution."
    if selection.provider == "litellm":
        return "No cloud provider response has been captured yet. Run model_call.py or supply --response-file."
    if selection.provider == "goose":
        return "No local Goose response has been captured yet. Run model_call.py or supply --response-file."
    if selection.provider == "ollama":
        return "No local model response has been captured yet. Run model_call.py or supply --response-file."
    if selection.provider == "local":
        return "Deterministic tool tiers do not produce model_output.md directly; use the underlying command or a manual model handoff."
    return "Selected provider is not automated in the workbench yet, so manual handoff is required."


def build_model_output(
    project_root: Path,
    prompt_path: Path,
    selection_path: Path,
    output_path: Path,
    prompt_summary: FinalPromptSummary,
    selection_summary: ModelSelectionSummary,
    status: str,
    reason: str,
    response_text: str | None,
    normalized_response_text: str | None,
    normalization_notes: list[str] | None,
    response_source: str | None,
) -> str:
    lines: list[str] = [
        "# Model Output",
        "",
        f"Generated: `{datetime.now().isoformat(timespec='seconds')}`",
        "",
        "## Execution Metadata",
        "",
        f"- Project: `{selection_summary.project or prompt_summary.project or 'unknown'}`",
        f"- Run ID: `{selection_summary.run_id or prompt_summary.run_id or output_path.parent.name}`",
        f"- Selected Tier: `{selection_summary.selected_tier}`",
        f"- Provider: `{selection_summary.provider}`",
        f"- Model: `{selection_summary.model}`",
        f"- Prompt: `{selection_summary.prompt or 'unknown'}`",
        f"- Mode: `{prompt_summary.mode or 'unknown'}`",
        f"- Task Type: `{prompt_summary.task_type or 'unknown'}`",
        f"- Risk: `{prompt_summary.risk or 'unknown'}`",
        f"- Final Prompt Path: `{relative_path(prompt_path, project_root)}`",
        f"- Model Selection Path: `{relative_path(selection_path, project_root)}`",
        f"- Output Path: `{relative_path(output_path, project_root)}`",
        f"- Status: `{status}`",
        "",
        "## Task Summary",
        "",
        prompt_summary.task or "No task summary found in final_prompt.md.",
        "",
        "## Execution Notes",
        "",
        f"- {reason}",
    ]

    if selection_summary.reason:
        lines.append(f"- Model selection reason: {selection_summary.reason}")
    if response_source:
        lines.append(f"- Response source: {response_source}")
    if normalization_notes:
        for note in normalization_notes:
            lines.append(f"- Response normalization note: {note}")

    lines.append("")
    if response_text is not None:
        lines.extend(
            [
                "## Captured Response",
                "",
                response_text.rstrip() or "[empty model response]",
                "",
            ]
        )
        if normalized_response_text:
            lines.extend(
                [
                    "## Normalized Response",
                    "",
                    normalized_response_text.rstrip(),
                    "",
                ]
            )
    else:
        lines.extend(
            [
                "## Manual Handoff",
                "",
                "1. Open the selected model or provider using the tier and model above.",
                "2. Send the full contents of final_prompt.md to that model.",
                "3. Save the raw response to a file and rerun this tool with --response-file to capture it into model_output.md.",
                "",
                "## Awaiting Response",
                "",
                "No model response has been captured yet.",
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    project = load_project_config(args.project)
    selection_path = resolve_cli_path(args.selection, project.root)
    prompt_path = resolve_cli_path(args.prompt, project.root)
    output_path = resolve_cli_path(args.out, project.root)
    response_path = resolve_cli_path(args.response_file, project.root) if args.response_file else None

    if not selection_path.exists():
        raise FileNotFoundError(f"Model selection file not found: {selection_path}")
    if not prompt_path.exists():
        raise FileNotFoundError(f"Final prompt file not found: {prompt_path}")
    if response_path and not response_path.exists():
        raise FileNotFoundError(f"Response file not found: {response_path}")

    selection_summary = parse_model_selection(selection_path)
    prompt_summary = parse_final_prompt(prompt_path)
    if selection_summary.project and selection_summary.project != args.project:
        raise ValueError(
            f"Project mismatch: model_selection.json uses {selection_summary.project}, CLI requested {args.project}."
        )
    if prompt_summary.project and prompt_summary.project != args.project:
        raise ValueError(
            f"Project mismatch: final_prompt.md uses {prompt_summary.project}, CLI requested {args.project}."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    status = "handoff_required"
    reason = determine_handoff_reason(selection_summary)
    response_text: str | None = None
    normalized_response_text: str | None = None
    normalization_notes: list[str] = []
    response_source: str | None = None

    if response_path is not None:
        response_text = read_text(response_path)
        response_source = relative_path(response_path, project.root)
        status = "response_captured"
        reason = "Captured a model response from the supplied response file."
        normalization_result = normalize_response_text(response_text)
        normalized_response_text = normalization_result.normalized_text
        normalization_notes = normalization_result.normalization_notes

    output_path.write_text(
        build_model_output(
            project_root=project.root,
            prompt_path=prompt_path,
            selection_path=selection_path,
            output_path=output_path,
            prompt_summary=prompt_summary,
            selection_summary=selection_summary,
            status=status,
            reason=reason,
            response_text=response_text,
            normalized_response_text=normalized_response_text,
            normalization_notes=normalization_notes,
            response_source=response_source,
        ),
        encoding="utf-8",
    )

    print(f"project={args.project}")
    print(f"run_id={selection_summary.run_id or prompt_summary.run_id or output_path.parent.name}")
    print(f"status={status}")
    print(f"provider={selection_summary.provider}")
    print(f"model={selection_summary.model}")
    print(f"output={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
