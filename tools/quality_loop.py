from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys

from config_loader import load_simple_yaml
from context_scout import WORKBENCH_ROOT, load_project_config, resolve_cli_path
from response_format import extract_preferred_response_text, missing_required_sections


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run Phase 2 manual quality-loop review, retry, and promotion logic."
    )
    parser.add_argument("--project", required=True, help="Project key from configs/projects.yaml.")
    parser.add_argument("--run-dir", required=True, help="Run directory containing workflow artifacts.")
    parser.add_argument(
        "--mode",
        choices=[
            "auto",
            "same_model_retry",
            "alternate_model_review",
            "pairwise_compare",
            "evaluate_review",
            "promote_revision",
        ],
        default="auto",
        help="Quality-loop action to perform.",
    )
    parser.add_argument("--risk", choices=["low", "medium", "high"], help="Task risk level.")
    parser.add_argument("--validation-report", help="Validation report to inspect. Defaults to validation_report.json.")
    parser.add_argument("--review-prompt", help="Review prompt path. Defaults to review_prompt.md in the run folder.")
    parser.add_argument("--review-output", help="Review output path. Defaults to review_output.md in the run folder.")
    return parser


def read_text(file_path: Path) -> str:
    if not file_path.exists() or not file_path.is_file():
        return ""
    return file_path.read_text(encoding="utf-8", errors="replace")


def read_json(file_path: Path) -> dict[str, object]:
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def write_json(file_path: Path, payload: dict[str, object]) -> None:
    file_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def load_quality_config() -> dict[str, object]:
    config_path = WORKBENCH_ROOT / "configs" / "quality_loop.yaml"
    if not config_path.exists():
        return {}
    raw_config = load_simple_yaml(config_path)
    quality_loop = raw_config.get("quality_loop", {})
    return quality_loop if isinstance(quality_loop, dict) else {}


def captured_response(model_output_text: str) -> str:
    return extract_preferred_response_text(model_output_text)


def parse_metadata(model_output_text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for line in model_output_text.splitlines():
        match = re.match(r"- ([^:]+): `([^`]+)`", line.strip())
        if match:
            metadata[match.group(1).strip().lower().replace(" ", "_")] = match.group(2).strip()
    return metadata


def status_from_validation(report: dict[str, object]) -> str:
    return str(report.get("overall_status", "unknown"))


def missing_context_has_needs_review(report: dict[str, object]) -> bool:
    notes = report.get("missing_context_notes", {})
    if not isinstance(notes, dict):
        return False
    needs_review = notes.get("needs_review", [])
    return isinstance(needs_review, list) and bool(needs_review)


def load_selection(run_dir: Path) -> dict[str, object]:
    return read_json(run_dir / "model_selection.json")


def enabled_section(config: dict[str, object], section_name: str) -> bool:
    section = config.get(section_name, {})
    return not isinstance(section, dict) or section.get("enabled", True) is not False


def candidate_output_paths(run_dir: Path) -> list[Path]:
    names = [
        "model_output.md",
        "model_output_2.md",
        "model_output_alt.md",
        "candidate_output_a.md",
        "candidate_output_b.md",
    ]
    return [run_dir / name for name in names if read_text(run_dir / name).strip()]


def review_recommendation(review_text: str) -> str:
    lowered = review_text.lower()
    blocking, _non_blocking = classify_review_output(review_text)
    if blocking or "revise_required" in lowered or "human review" in lowered or "escalate" in lowered:
        return "revise"
    if "recommend accept" in lowered or "accepted" in lowered or "accept" in lowered:
        return "accept"
    return "unknown"


def conflicting_review_paths(run_dir: Path) -> list[Path]:
    primary = run_dir / "review_output.md"
    alternate = run_dir / "review_output_alt.md"
    if not primary.exists() or not alternate.exists():
        return []
    primary_recommendation = review_recommendation(read_text(primary))
    alternate_recommendation = review_recommendation(read_text(alternate))
    if "unknown" in {primary_recommendation, alternate_recommendation}:
        return []
    if primary_recommendation != alternate_recommendation:
        return [primary, alternate]
    return []


def pairwise_trigger(run_dir: Path, config: dict[str, object]) -> tuple[bool, str, list[str]]:
    if not enabled_section(config, "pairwise_compare"):
        return False, "", []

    candidates = candidate_output_paths(run_dir)
    if len(candidates) >= 2:
        names = [path.name for path in candidates[:2]]
        return True, "Two candidate model outputs are present.", [f"Compare candidate outputs: {', '.join(names)}"]

    conflicting = conflicting_review_paths(run_dir)
    if conflicting:
        names = [path.name for path in conflicting]
        return True, "Review outputs conflict.", [f"Resolve conflicting reviews: {', '.join(names)}"]

    return False, "", []


def infer_prompt_name(model_output_text: str, selection: dict[str, object]) -> str:
    metadata = parse_metadata(model_output_text)
    if metadata.get("prompt"):
        return metadata["prompt"]
    prompt = selection.get("prompt")
    return str(prompt) if prompt is not None else ""


def determine_auto_trigger(
    run_dir: Path,
    model_output_text: str,
    report: dict[str, object],
    risk: str,
    config: dict[str, object],
) -> tuple[str, str, list[str], list[str]]:
    if config.get("enabled") is False:
        return "none", "Quality loop is disabled in configs/quality_loop.yaml.", [], []

    response_text = captured_response(model_output_text)
    pairwise_required, pairwise_reason, pairwise_blocking = pairwise_trigger(run_dir, config)
    if pairwise_required:
        return "pairwise_compare", pairwise_reason, pairwise_blocking, []

    if enabled_section(config, "same_model_retry"):
        if not response_text:
            return "same_model_retry", "model_output.md has no captured response.", ["Captured response is missing."], []

        missing = missing_required_sections(response_text)
        if missing:
            return (
                "same_model_retry",
                "model_output.md captured response is missing required sections.",
                [f"Missing required response section: {section}" for section in missing],
                [],
            )

    if not enabled_section(config, "alternate_model_review"):
        return "none", "No quality loop triggers detected.", [], []

    validation_status = status_from_validation(report)
    if validation_status == "failed":
        return "alternate_model_review", "Validation failed.", ["Canonical validation_report.json failed."], []

    if missing_context_has_needs_review(report):
        return (
            "alternate_model_review",
            "Validation report contains missing-context items that need review.",
            ["missing_context.md has review-blocking notes."],
            [],
        )

    if risk == "high":
        return "alternate_model_review", "High-risk task requires alternate-model review.", ["Task risk is high."], []

    selection = load_selection(run_dir)
    selected_tier = str(selection.get("selected_tier", ""))
    prompt_name = infer_prompt_name(model_output_text, selection)
    prompt_lower = prompt_name.lower()
    if "security" in prompt_lower or "privacy" in prompt_lower:
        return "alternate_model_review", "Security/privacy prompt requires alternate-model review.", ["Security/privacy prompt detected."], []

    task_text = " ".join(
        str(value)
        for value in (
            selection.get("task_type", ""),
            selection.get("workflow_mode", ""),
            prompt_name,
            read_text(run_dir / "final_prompt.md")[:2000],
        )
    ).lower()
    if "architecture" in task_text:
        return "alternate_model_review", "Architecture task requires alternate-model review.", ["Architecture task detected."], []
    if re.search(r"\bapi\b", task_text) or re.search(r"\bcontract\b", task_text):
        return "alternate_model_review", "API or contract task requires alternate-model review.", ["API/contract task detected."], []
    if selected_tier in {"cheap_cloud", "local_coding"} and risk == "medium":
        return (
            "alternate_model_review",
            "Medium-risk low-capability model output requires alternate-model review.",
            [f"{selected_tier} used for medium risk."],
            [],
        )

    return "none", "No quality loop triggers detected.", [], []


def base_decision(
    loop_type: str,
    required: bool,
    reason: str,
    next_action: str,
    final_status: str,
    accepted_pass: int,
    blocking_findings: list[str],
    non_blocking_findings: list[str],
) -> dict[str, object]:
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "loop_type": loop_type,
        "required": required,
        "reason": reason,
        "next_action": next_action,
        "accepted_pass": accepted_pass,
        "final_status": final_status,
        "authoritative_model_output": "model_output.md",
        "authoritative_validation_report": "validation_report.json",
        "first_pass_artifacts": {
            "model_output": "model_output.md",
            "validation_report": "validation_report.json",
        },
        "second_pass_artifacts": {
            "model_output": "model_output_2.md",
            "validation_report": "validation_report_2.json",
        },
        "blocking_findings": blocking_findings,
        "non_blocking_findings": non_blocking_findings,
    }


def review_prompt_text(loop_type: str, reason: str, model_output_text: str, report: dict[str, object]) -> str:
    prompt_lines = [
        "# Review Prompt",
        "",
        f"Mode: `{loop_type}`",
        f"Reason: {reason}",
        "",
        "## Original Model Output",
        "",
        model_output_text,
        "",
        "## Validation Summary",
        "",
        f"- Overall status: `{report.get('overall_status', 'unknown')}`",
        f"- Confidence: `{report.get('confidence', 'unknown')}`",
        "",
        "## Instructions",
        "",
    ]
    if loop_type == "same_model_retry":
        prompt_lines.extend(
            [
                "Revise the response only enough to satisfy the missing format or validation issue.",
                "Preserve the original intent and do not claim validation that was not run.",
                "Include these sections: Summary, Files touched, Validation run or Validation not run, and Risks / follow-ups.",
            ]
        )
    else:
        prompt_lines.extend(
            [
                "Review for correctness, missed edge cases, unsupported claims, regression risk, and validation gaps.",
                "Do not rewrite from scratch.",
                "Classify findings as blocking or non-blocking.",
                "Recommend accept, revise, escalate, or human review.",
            ]
        )
    return "\n".join(prompt_lines) + "\n"


def pairwise_prompt_text(reason: str, run_dir: Path, report: dict[str, object]) -> str:
    candidates = candidate_output_paths(run_dir)
    if len(candidates) < 2:
        candidates = [run_dir / "review_output.md", run_dir / "review_output_alt.md"]
    first = candidates[0] if candidates else run_dir / "model_output.md"
    second = candidates[1] if len(candidates) > 1 else run_dir / "model_output_2.md"
    return "\n".join(
        [
            "# Pairwise Comparison Prompt",
            "",
            f"Reason: {reason}",
            "",
            "## Candidate A",
            "",
            f"Path: `{first.name}`",
            "",
            read_text(first),
            "",
            "## Candidate B",
            "",
            f"Path: `{second.name}`",
            "",
            read_text(second),
            "",
            "## Validation Summary",
            "",
            f"- Overall status: `{report.get('overall_status', 'unknown')}`",
            f"- Confidence: `{report.get('confidence', 'unknown')}`",
            "",
            "## Instructions",
            "",
            "Compare the candidates for correctness, validation evidence, instruction following, risk, and missing context.",
            "Choose Candidate A, Candidate B, revise, escalate, or human review.",
            "Classify any required fixes as Blocking and optional improvements as Non-blocking.",
            "Do not merge candidates or invent validation evidence.",
        ]
    ) + "\n"


def classify_review_output(review_text: str) -> tuple[list[str], list[str]]:
    blocking: list[str] = []
    non_blocking: list[str] = []
    for line in review_text.splitlines():
        stripped = line.strip().lstrip("-* ").strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if lowered.startswith("non-blocking:") or lowered.startswith("non blocking:"):
            non_blocking.append(stripped)
        elif lowered.startswith("blocking:") or "revise_required" in lowered or "must fix" in lowered:
            blocking.append(stripped)
        elif "nit" in lowered or "consider" in lowered:
            non_blocking.append(stripped)
    return blocking, non_blocking


def run_second_pass_validation(project_key: str, run_dir: Path) -> None:
    second_output = run_dir / "model_output_2.md"
    second_report = run_dir / "validation_report_2.json"
    if second_report.exists():
        return
    if not second_output.exists():
        raise FileNotFoundError(f"Missing second-pass output: {second_output}")

    original_output = run_dir / "model_output.md"
    backup_output = run_dir / ".quality_loop_model_output_original.tmp"
    if original_output.exists():
        shutil.copyfile(original_output, backup_output)
    try:
        shutil.copyfile(second_output, original_output)
        command = [
            sys.executable,
            str(WORKBENCH_ROOT / "tools" / "validate_run.py"),
            "--project",
            project_key,
            "--profile",
            "run_signoff",
            "--out-dir",
            str(run_dir),
            "--report-name",
            second_report.name,
        ]
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode not in {0, 1, 2}:
            raise RuntimeError(
                "Second-pass validation execution failed unexpectedly\n"
                f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            )
    finally:
        if backup_output.exists():
            shutil.copyfile(backup_output, original_output)
            try:
                backup_output.unlink()
            except PermissionError:
                pass


def promote_revision(project_key: str, run_dir: Path) -> dict[str, object]:
    second_output = run_dir / "model_output_2.md"
    second_report = run_dir / "validation_report_2.json"
    if not second_output.exists():
        raise FileNotFoundError(f"Missing second-pass output: {second_output}")

    run_second_pass_validation(project_key, run_dir)
    second_payload = read_json(second_report)
    if second_payload.get("overall_status") != "passed":
        return base_decision(
            loop_type="same_model_retry",
            required=True,
            reason="Second-pass validation did not pass; canonical artifacts were not promoted.",
            next_action="await_revision",
            final_status="revision_required",
            accepted_pass=1,
            blocking_findings=[f"validation_report_2.json status: {second_payload.get('overall_status', 'unknown')}"],
            non_blocking_findings=[],
        )

    first_output = run_dir / "model_output.md"
    first_report = run_dir / "validation_report.json"
    archived_output = run_dir / "model_output_1.md"
    archived_report = run_dir / "validation_report_1.json"
    if first_output.exists():
        shutil.copyfile(first_output, archived_output)
    if first_report.exists():
        shutil.copyfile(first_report, archived_report)

    shutil.copyfile(second_output, first_output)
    shutil.copyfile(second_report, first_report)
    decision = base_decision(
        loop_type="same_model_retry",
        required=False,
        reason="Second-pass output passed validation and was promoted.",
        next_action="none",
        final_status="accepted",
        accepted_pass=2,
        blocking_findings=[],
        non_blocking_findings=[],
    )
    decision["first_pass_artifacts"] = {
        "model_output": "model_output_1.md",
        "validation_report": "validation_report_1.json",
    }
    return decision


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    project = load_project_config(args.project)
    run_dir = resolve_cli_path(args.run_dir, project.root)
    model_output_path = run_dir / "model_output.md"
    validation_path = resolve_cli_path(args.validation_report, project.root) if args.validation_report else run_dir / "validation_report.json"
    review_prompt_path = resolve_cli_path(args.review_prompt, project.root) if args.review_prompt else run_dir / "review_prompt.md"
    review_output_path = resolve_cli_path(args.review_output, project.root) if args.review_output else run_dir / "review_output.md"
    decision_path = run_dir / "revision_decision.json"

    if args.mode == "promote_revision":
        try:
            decision = promote_revision(args.project, run_dir)
        except (FileNotFoundError, RuntimeError) as exc:
            decision = base_decision(
                loop_type="same_model_retry",
                required=True,
                reason=str(exc),
                next_action="await_revision",
                final_status="revision_required",
                accepted_pass=1,
                blocking_findings=[str(exc)],
                non_blocking_findings=[],
            )
            write_json(decision_path, decision)
            print(f"revision_decision={decision_path}")
            print("final_status=revision_required")
            return 1
        write_json(decision_path, decision)
        print(f"revision_decision={decision_path}")
        print(f"final_status={decision['final_status']}")
        return 0 if decision["final_status"] == "accepted" else 2

    if not model_output_path.exists():
        print(f"Missing model_output.md: {model_output_path}")
        return 1

    model_output_text = read_text(model_output_path)
    report = read_json(validation_path)
    risk = args.risk or parse_metadata(model_output_text).get("risk", "medium")

    if args.mode == "evaluate_review":
        review_text = read_text(review_output_path)
        if not review_text:
            print(f"Missing review output: {review_output_path}")
            return 1
        blocking, non_blocking = classify_review_output(review_text)
        final_status = "revision_required" if blocking else "accepted"
        decision = base_decision(
            loop_type="alternate_model_review",
            required=bool(blocking),
            reason="Review output evaluated.",
            next_action="await_revision" if blocking else "none",
            final_status=final_status,
            accepted_pass=1,
            blocking_findings=blocking,
            non_blocking_findings=non_blocking,
        )
        write_json(decision_path, decision)
        print(f"revision_decision={decision_path}")
        print(f"final_status={final_status}")
        return 2 if blocking else 0

    config = load_quality_config()
    if args.mode == "auto":
        loop_type, reason, blocking, non_blocking = determine_auto_trigger(
            run_dir=run_dir,
            model_output_text=model_output_text,
            report=report,
            risk=str(risk),
            config=config,
        )
    elif args.mode == "pairwise_compare":
        loop_type = "pairwise_compare"
        reason = "Manual pairwise comparison requested."
        blocking = ["Pairwise comparison requires manual review in Phase 2."]
        non_blocking = []
    else:
        loop_type = args.mode
        reason = f"Manual {args.mode} requested."
        blocking = [reason]
        non_blocking = []

    if loop_type == "none":
        decision = base_decision(
            loop_type="none",
            required=False,
            reason=reason,
            next_action="none",
            final_status="accepted",
            accepted_pass=1,
            blocking_findings=[],
            non_blocking_findings=non_blocking,
        )
        write_json(decision_path, decision)
        print(f"revision_decision={decision_path}")
        print("final_status=accepted")
        return 0

    decision = base_decision(
        loop_type=loop_type,
        required=True,
        reason=reason,
        next_action="manual_review_handoff" if loop_type != "same_model_retry" else "revise_same_model",
        final_status="review_required",
        accepted_pass=0,
        blocking_findings=blocking,
        non_blocking_findings=non_blocking,
    )
    write_json(decision_path, decision)
    if loop_type == "pairwise_compare":
        review_prompt_path.write_text(pairwise_prompt_text(reason, run_dir, report), encoding="utf-8")
    else:
        review_prompt_path.write_text(review_prompt_text(loop_type, reason, model_output_text, report), encoding="utf-8")

    print(f"revision_decision={decision_path}")
    print(f"review_prompt={review_prompt_path}")
    print("final_status=review_required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
