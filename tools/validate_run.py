from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
import re
import subprocess
import time

from config_loader import load_simple_yaml
from context_scout import WORKBENCH_ROOT, load_project_config, resolve_cli_path
from response_format import extract_preferred_response_text, missing_required_sections


@dataclass
class ValidationProfile:
    name: str
    description: str
    commands: list[dict[str, object]]
    required_artifacts: list[str]
    non_empty_artifacts: list[str]
    review_checks: list[str]
    consistency_checks: list[str]


@dataclass
class ValidationCheck:
    name: str
    status: str
    summary: str
    details: list[str]


@dataclass
class ParsedExpertPacket:
    run_id: str | None
    project: str | None
    search_terms: list[str]
    docs_read_count: int | None
    files_considered_count: int | None
    top_files: list[str]


@dataclass
class ParsedSearchResults:
    run_id: str | None
    project: str | None
    search_terms: list[str]
    rows: list[dict[str, object]]


@dataclass
class CommandResult:
    name: str
    command: str
    cwd: str
    required: bool
    weight: float
    exit_code: int
    status: str
    duration_ms: int


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run deterministic validation checks over a run folder before sign-off."
    )
    parser.add_argument("--project", required=True, help="Project key from configs/projects.yaml.")
    parser.add_argument("--profile", help="Validation profile from configs/validation_profiles.yaml.")
    parser.add_argument(
        "--changed-files",
        nargs="*",
        default=[],
        help="Optional list of changed files to scope validation.",
    )
    parser.add_argument("--out-dir", required=True, help="Run directory for validation artifacts.")
    parser.add_argument(
        "--report-name",
        default="validation_report.json",
        help="Validation report file name to write inside the run directory.",
    )
    return parser


def load_validation_profile(profile_name: str) -> ValidationProfile:
    raw_data = load_simple_yaml(WORKBENCH_ROOT / "configs" / "validation_profiles.yaml")
    profiles = raw_data.get("profiles", {})
    if profile_name not in profiles:
        raise ValueError(f"Unknown validation profile: {profile_name}")

    profile_data = profiles[profile_name]
    if not isinstance(profile_data, dict):
        raise ValueError(f"Validation profile must be a mapping: {profile_name}")

    return ValidationProfile(
        name=profile_name,
        description=str(profile_data.get("description", "")),
        commands=[item for item in profile_data.get("commands", []) if isinstance(item, dict)],
        required_artifacts=[str(item) for item in profile_data.get("required_artifacts", [])],
        non_empty_artifacts=[str(item) for item in profile_data.get("non_empty_artifacts", [])],
        review_checks=[str(item) for item in profile_data.get("review_checks", [])],
        consistency_checks=[str(item) for item in profile_data.get("consistency_checks", [])],
    )


def read_text_if_exists(file_path: Path) -> str:
    if not file_path.exists() or not file_path.is_file():
        return ""
    return file_path.read_text(encoding="utf-8", errors="replace")


def count_non_empty_lines(file_path: Path) -> int:
    return sum(1 for line in read_text_if_exists(file_path).splitlines() if line.strip())


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


def parse_backticked_bullets(lines: list[str]) -> list[str]:
    values: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("- "):
            continue
        match = re.match(r"- `([^`]+)`", stripped)
        if match:
            values.append(match.group(1))
    return values


def parse_expert_top_files(lines: list[str]) -> list[str]:
    values: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped.startswith("- `"):
            continue
        match = re.match(r"- `([^`]+)` \(score=", stripped)
        if match:
            values.append(match.group(1))
    return values


def parse_summary_count(text: str, label: str) -> int | None:
    match = re.search(rf"- {re.escape(label)}: (\d+)", text)
    if match:
        return int(match.group(1))
    return None


def parse_expert_packet(file_path: Path) -> ParsedExpertPacket:
    text = read_text_if_exists(file_path)
    run_id_match = re.search(r"Run ID: `([^`]+)`", text)
    project_match = re.search(r"Project: `([^`]+)`", text)
    return ParsedExpertPacket(
        run_id=run_id_match.group(1) if run_id_match else None,
        project=project_match.group(1) if project_match else None,
        search_terms=parse_backticked_bullets(get_section_lines(text, "## Search Terms")),
        docs_read_count=parse_summary_count(text, "Docs read"),
        files_considered_count=parse_summary_count(text, "Files considered"),
        top_files=parse_expert_top_files(get_section_lines(text, "## Top Files Considered")),
    )


def split_markdown_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_search_results(file_path: Path) -> ParsedSearchResults:
    text = read_text_if_exists(file_path)
    run_id_match = re.search(r"Run ID: `([^`]+)`", text)
    project_match = re.search(r"Project: `([^`]+)`", text)
    rows: list[dict[str, object]] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        if stripped.startswith("| Rank ") or stripped.startswith("|---"):
            continue

        cells = split_markdown_row(stripped)
        if len(cells) != 7:
            continue

        try:
            rank = int(cells[0])
            score = int(cells[2])
        except ValueError:
            continue

        rows.append(
            {
                "rank": rank,
                "file": cells[1],
                "score": score,
                "matched": [] if cells[3] == "none" else [item.strip() for item in cells[3].split(",") if item.strip()],
                "boosts": [] if cells[4] == "none" else [item.strip() for item in cells[4].split(",") if item.strip()],
                "penalties": [] if cells[5] == "none" else [item.strip() for item in cells[5].split(",") if item.strip()],
                "reason": cells[6],
            }
        )

    return ParsedSearchResults(
        run_id=run_id_match.group(1) if run_id_match else None,
        project=project_match.group(1) if project_match else None,
        search_terms=parse_backticked_bullets(get_section_lines(text, "## Search Terms")),
        rows=rows,
    )


def build_check(name: str, status: str, summary: str, details: list[str]) -> ValidationCheck:
    return ValidationCheck(name=name, status=status, summary=summary, details=details)


def validate_artifact_presence(run_dir: Path, required_artifacts: list[str]) -> ValidationCheck:
    if not required_artifacts:
        return build_check(
            name="artifact_presence",
            status="passed",
            summary="No required artifact presence checks were configured.",
            details=[],
        )

    if not run_dir.exists():
        return build_check(
            name="artifact_presence",
            status="failed",
            summary="Run directory does not exist.",
            details=[f"Missing run directory: {run_dir}"],
        )

    missing = [artifact for artifact in required_artifacts if not (run_dir / artifact).exists()]
    if missing:
        return build_check(
            name="artifact_presence",
            status="failed",
            summary="Required run artifacts are missing.",
            details=[f"Missing artifact: {artifact}" for artifact in missing],
        )

    return build_check(
        name="artifact_presence",
        status="passed",
        summary="All required run artifacts are present.",
        details=[f"Found {len(required_artifacts)} required artifacts."],
    )


def validate_non_empty_artifacts(run_dir: Path, artifact_names: list[str]) -> ValidationCheck:
    if not artifact_names:
        return build_check(
            name="artifact_non_empty",
            status="passed",
            summary="No required non-empty artifact checks were configured.",
            details=[],
        )

    empty_artifacts: list[str] = []
    for artifact in artifact_names:
        artifact_path = run_dir / artifact
        if artifact_path.exists() and not read_text_if_exists(artifact_path).strip():
            empty_artifacts.append(artifact)

    if empty_artifacts:
        return build_check(
            name="artifact_non_empty",
            status="failed",
            summary="Required artifacts must not be empty.",
            details=[f"Empty artifact: {artifact}" for artifact in empty_artifacts],
        )

    return build_check(
        name="artifact_non_empty",
        status="passed",
        summary="Required artifacts contain content.",
        details=[f"Checked {len(artifact_names)} artifacts for non-empty content."],
    )


def parse_missing_context_sections(text: str) -> dict[str, list[str]]:
    if not text.strip() or "No missing context detected in this scout run." in text:
        return {"needs_review": [], "info": []}

    sections: dict[str, list[str]] = {"needs_review": [], "info": []}
    current_key: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped == "## Needs Review":
            current_key = "needs_review"
            continue
        if stripped == "## Info":
            current_key = "info"
            continue
        if stripped.startswith("- ") and current_key is not None:
            note = stripped[2:].strip()
            if note and note.lower() != "none.":
                sections[current_key].append(note)
    return sections


def validate_missing_context_review(file_path: Path) -> tuple[ValidationCheck, dict[str, list[str]]]:
    text = read_text_if_exists(file_path)
    if not text.strip():
        return (
            build_check(
                name="missing_context_review",
                status="failed",
                summary="missing_context.md is missing or empty.",
                details=["The validator could not review missing_context.md because it has no readable content."],
            ),
            {"needs_review": [], "info": []},
        )

    sections = parse_missing_context_sections(text)
    needs_review_notes = sections.get("needs_review", [])
    info_notes = sections.get("info", [])

    if not needs_review_notes and not info_notes and "No missing context detected in this scout run." in text:
        return (
            build_check(
                name="missing_context_review",
                status="passed",
                summary="missing_context.md was reviewed and reports no open gaps.",
                details=["No missing context items remain."],
            ),
            sections,
        )

    if needs_review_notes:
        return (
            build_check(
                name="missing_context_review",
                status="needs_review",
                summary="missing_context.md was reviewed and contains open gaps.",
                details=[f"Open gap: {note}" for note in needs_review_notes],
            ),
            sections,
        )

    return (
        build_check(
            name="missing_context_review",
            status="passed",
            summary="missing_context.md contains informational notes only.",
            details=[f"Info: {note}" for note in info_notes] or ["No review-blocking missing context items remain."],
        ),
        sections,
    )


def parse_model_output_status(file_path: Path) -> str | None:
    text = read_text_if_exists(file_path)
    if not text.strip():
        return None
    match = re.search(r"- Status: `([^`]+)`", text)
    if match:
        return match.group(1).strip().lower()
    return None


def validate_model_output_status(file_path: Path) -> ValidationCheck:
    text = read_text_if_exists(file_path)
    if not text.strip():
        return build_check(
            name="model_output_status",
            status="failed",
            summary="model_output.md is missing or empty.",
            details=["The sign-off profile requires a non-empty model_output.md artifact."],
        )

    status = parse_model_output_status(file_path)
    if status == "response_captured":
        return build_check(
            name="model_output_status",
            status="passed",
            summary="model_output.md indicates an accepted execution state.",
            details=[f"Model output status: {status}"],
        )

    if status == "handoff_required":
        return build_check(
            name="model_output_status",
            status="needs_review",
            summary="model_output.md indicates manual model handoff is still required.",
            details=["Model output status: handoff_required"],
        )

    if status is None:
        return build_check(
            name="model_output_status",
            status="failed",
            summary="model_output.md does not contain a parseable status field.",
            details=["Expected a metadata line in the form: - Status: `response_captured|handoff_required`"],
        )

    return build_check(
        name="model_output_status",
        status="failed",
        summary="model_output.md contains an unsupported status value.",
        details=[f"Unsupported model output status: {status}"],
    )


def validate_captured_response_format(file_path: Path) -> ValidationCheck:
    text = read_text_if_exists(file_path)
    if not text.strip():
        return build_check(
            name="captured_response_format",
            status="failed",
            summary="model_output.md is missing or empty.",
            details=["The validator could not inspect the captured response because model_output.md has no readable content."],
        )

    status = parse_model_output_status(file_path)
    if status != "response_captured":
        return build_check(
            name="captured_response_format",
            status="passed",
            summary="Captured-response format check is not applicable until a response is captured.",
            details=[f"Model output status: {status or 'unknown'}"],
        )

    response_text = extract_preferred_response_text(text)
    if not response_text:
        return build_check(
            name="captured_response_format",
            status="failed",
            summary="model_output.md is marked response_captured but does not contain a readable captured response section.",
            details=["Expected either ## Normalized Response or ## Captured Response content."],
        )

    missing = missing_required_sections(response_text)
    if missing:
        return build_check(
            name="captured_response_format",
            status="needs_review",
            summary="Captured model response is missing the preferred structured sections.",
            details=[f"Missing required response section: {section}" for section in missing],
        )

    section_used = "normalized" if "## Normalized Response" in text else "captured"
    return build_check(
        name="captured_response_format",
        status="passed",
        summary="Captured model response matches the preferred structured format.",
        details=[f"Validated {section_used} response section."],
    )


def validate_internal_consistency(
    project_key: str,
    run_dir_name: str,
    expert_packet: ParsedExpertPacket,
    search_results: ParsedSearchResults,
    docs_read_count: int,
    files_considered_count: int,
    consistency_checks: list[str],
) -> ValidationCheck:
    if not consistency_checks:
        return build_check(
            name="artifact_consistency",
            status="passed",
            summary="No artifact consistency checks were configured.",
            details=[],
        )

    details: list[str] = []
    enabled_checks = set(consistency_checks)

    if "matching_run_id" in enabled_checks:
        if expert_packet.run_id != run_dir_name or search_results.run_id != run_dir_name:
            details.append("Run ID mismatch across the run folder, expert_packet.md, or search_results.md.")

    if "matching_project" in enabled_checks:
        if expert_packet.project != project_key or search_results.project != project_key:
            details.append("Project mismatch across CLI input, expert_packet.md, or search_results.md.")

    if "matching_search_terms" in enabled_checks:
        if expert_packet.search_terms != search_results.search_terms:
            details.append("Search terms differ between expert_packet.md and search_results.md.")

    if "docs_count_match" in enabled_checks:
        if expert_packet.docs_read_count != docs_read_count:
            details.append(
                f"Docs read count mismatch: expert_packet.md reports {expert_packet.docs_read_count}, docs_read.txt has {docs_read_count}."
            )

    if "files_count_match" in enabled_checks:
        search_results_count = len(search_results.rows)
        if expert_packet.files_considered_count != files_considered_count:
            details.append(
                f"Files considered count mismatch: expert_packet.md reports {expert_packet.files_considered_count}, files_considered.txt has {files_considered_count}."
            )
        if search_results_count != files_considered_count:
            details.append(
                f"Files considered count mismatch: search_results.md has {search_results_count} ranked rows, files_considered.txt has {files_considered_count}."
            )

    if "top_files_match" in enabled_checks:
        top_ranked_files = [str(row.get("file", "")) for row in search_results.rows[: len(expert_packet.top_files)]]
        if expert_packet.top_files != top_ranked_files:
            details.append("Top files listed in expert_packet.md do not match the leading ranked rows in search_results.md.")

    if details:
        return build_check(
            name="artifact_consistency",
            status="failed",
            summary="Run artifacts are not internally consistent.",
            details=details,
        )

    return build_check(
        name="artifact_consistency",
        status="passed",
        summary="expert_packet.md and search_results.md are internally consistent.",
        details=[
            f"docs_read.txt count={docs_read_count}",
            f"files_considered.txt count={files_considered_count}",
            f"search_results.md rows={len(search_results.rows)}",
        ],
    )


def run_profile_commands(project_root: Path, profile: ValidationProfile) -> tuple[list[CommandResult], list[dict[str, str]]]:
    commands_run: list[CommandResult] = []
    commands_not_run: list[dict[str, str]] = []

    if not profile.commands:
        commands_not_run.append({"name": "none", "reason": "Profile does not define deterministic commands."})
        return commands_run, commands_not_run

    for raw_command in profile.commands:
        name = str(raw_command.get("name", "")).strip()
        command = str(raw_command.get("command", "")).strip()
        if not name or not command:
            commands_not_run.append({"name": name or "unnamed", "reason": "Command entry is missing name or command."})
            continue

        cwd_value = str(raw_command.get("cwd", "."))
        cwd_path = resolve_cli_path(cwd_value, project_root)
        required = bool(raw_command.get("required", True))
        weight = float(raw_command.get("weight", 1.0))

        start = time.perf_counter()
        result = subprocess.run(
            command,
            cwd=cwd_path,
            shell=True,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=False,
        )
        duration_ms = int(round((time.perf_counter() - start) * 1000))
        commands_run.append(
            CommandResult(
                name=name,
                command=command,
                cwd=str(cwd_path),
                required=required,
                weight=weight,
                exit_code=result.returncode,
                status="passed" if result.returncode == 0 else "failed",
                duration_ms=duration_ms,
            )
        )

    return commands_run, commands_not_run


def compute_overall_status(
    artifact_checks: list[ValidationCheck],
    review_checks: list[ValidationCheck],
    commands_run: list[CommandResult],
) -> str:
    if any(result.required and result.status == "failed" for result in commands_run):
        return "failed"

    statuses = {check.status for check in [*artifact_checks, *review_checks]}
    if "failed" in statuses:
        return "failed"
    if "needs_review" in statuses:
        return "needs_review"
    return "passed"


def build_validation_report(
    run_id: str,
    project_key: str,
    profile: ValidationProfile,
    commands_run: list[CommandResult],
    commands_not_run: list[dict[str, str]],
    artifact_checks: list[ValidationCheck],
    review_checks: list[ValidationCheck],
    missing_context_notes: dict[str, list[str]],
) -> dict[str, object]:
    overall_status = compute_overall_status(artifact_checks, review_checks, commands_run)

    artifact_passed = sum(1 for check in artifact_checks if check.status == "passed")
    artifact_total = len(artifact_checks)
    artifact_confidence = round(artifact_passed / artifact_total, 2) if artifact_total else 1.0

    required_commands = [result for result in commands_run if result.required]
    scheduled_weight = sum(result.weight for result in required_commands)
    passed_weight = sum(result.weight for result in required_commands if result.status == "passed")
    command_confidence = round(passed_weight / scheduled_weight, 2) if scheduled_weight else 0.0

    review_passed = sum(1 for check in review_checks if check.status == "passed")
    review_total = len(review_checks)
    review_confidence = round(review_passed / review_total, 2) if review_total else 1.0

    if scheduled_weight == 0:
        confidence = 0.25
    else:
        confidence = passed_weight / scheduled_weight

    if any(result.required and result.status == "failed" for result in commands_run):
        confidence = min(confidence, 0.40)

    if any(check.status == "needs_review" for check in review_checks):
        confidence = min(confidence, 0.75)

    confidence = round(confidence, 2)
    all_checks = [*artifact_checks, *review_checks]

    return {
        "run_id": run_id,
        "project": project_key,
        "profile": profile.name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "commands_run": [asdict(result) for result in commands_run],
        "commands_not_run": commands_not_run,
        "artifact_checks": [asdict(check) for check in artifact_checks],
        "review_checks": [asdict(check) for check in review_checks],
        "missing_context_notes": missing_context_notes,
        "overall_status": overall_status,
        "sign_off_ready": overall_status == "passed",
        "confidence": confidence,
        "detailed_confidence": {
            "artifact_confidence": artifact_confidence,
            "command_confidence": command_confidence,
            "review_confidence": review_confidence,
            "overall_confidence": confidence,
        },
        "summary": {
            "commands_passed": sum(1 for result in commands_run if result.status == "passed"),
            "commands_failed": sum(1 for result in commands_run if result.status == "failed"),
            "checks_passed": sum(1 for check in all_checks if check.status == "passed"),
            "checks_needs_review": sum(1 for check in all_checks if check.status == "needs_review"),
            "checks_failed": sum(1 for check in all_checks if check.status == "failed"),
        },
    }


def determine_exit_code(overall_status: str) -> int:
    if overall_status == "passed":
        return 0
    if overall_status == "needs_review":
        return 2
    return 1


def validate_run_payload(args: argparse.Namespace) -> dict[str, object]:
    project = load_project_config(args.project)
    profile = load_validation_profile(args.profile or project.default_validation_profile)
    run_dir = resolve_cli_path(args.out_dir, project.root)
    run_dir.mkdir(parents=True, exist_ok=True)

    commands_run, commands_not_run = run_profile_commands(project.root, profile)

    artifact_checks: list[ValidationCheck] = []
    artifact_checks.append(validate_artifact_presence(run_dir, profile.required_artifacts))
    artifact_checks.append(validate_non_empty_artifacts(run_dir, profile.non_empty_artifacts))

    review_checks: list[ValidationCheck] = []
    missing_context_notes = {"needs_review": [], "info": []}
    if "missing_context_review" in set(profile.review_checks):
        missing_context_check, missing_context_notes = validate_missing_context_review(run_dir / "missing_context.md")
        review_checks.append(missing_context_check)

    if "model_output_status" in set(profile.review_checks):
        review_checks.append(validate_model_output_status(run_dir / "model_output.md"))
        review_checks.append(validate_captured_response_format(run_dir / "model_output.md"))

    expert_packet = parse_expert_packet(run_dir / "expert_packet.md")
    search_results = parse_search_results(run_dir / "search_results.md")
    artifact_checks.append(
        validate_internal_consistency(
            project_key=args.project,
            run_dir_name=run_dir.name,
            expert_packet=expert_packet,
            search_results=search_results,
            docs_read_count=count_non_empty_lines(run_dir / "docs_read.txt"),
            files_considered_count=count_non_empty_lines(run_dir / "files_considered.txt"),
            consistency_checks=profile.consistency_checks,
        )
    )

    report = build_validation_report(
        run_id=run_dir.name,
        project_key=args.project,
        profile=profile,
        commands_run=commands_run,
        commands_not_run=commands_not_run,
        artifact_checks=artifact_checks,
        review_checks=review_checks,
        missing_context_notes=missing_context_notes,
    )
    report_path = run_dir / args.report_name
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    project = load_project_config(args.project)
    run_dir = resolve_cli_path(args.out_dir, project.root)
    report_path = run_dir / args.report_name
    report = validate_run_payload(args)

    print(f"project={args.project}")
    print(f"profile={report['profile']}")
    print(f"run_dir={run_dir}")
    print(f"validation_report={report_path}")
    print(f"overall_status={report['overall_status']}")
    print(f"sign_off_ready={str(report['sign_off_ready']).lower()}")
    print(f"confidence={report['confidence']}")
    print(f"commands_passed={report['summary']['commands_passed']}")
    print(f"commands_failed={report['summary']['commands_failed']}")
    print(f"checks_passed={report['summary']['checks_passed']}")
    print(f"checks_needs_review={report['summary']['checks_needs_review']}")
    print(f"checks_failed={report['summary']['checks_failed']}")
    return determine_exit_code(str(report["overall_status"]))


if __name__ == "__main__":
    raise SystemExit(main())
