from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime
import fnmatch
import json
from pathlib import Path
import re
import subprocess
import time

from .config_loader import load_simple_yaml
from .context_scout import WORKBENCH_ROOT, load_project_config, resolve_cli_path
from .policy_packs import load_policy_pack_catalog, resolve_policy_pack_reference
from .response_format import extract_preferred_response_text, missing_required_sections


@dataclass
class ValidationProfile:
    name: str
    description: str
    commands: list[dict[str, object]]
    required_artifacts: list[str]
    non_empty_artifacts: list[str]
    review_checks: list[str]
    consistency_checks: list[str]
    changed_file_policy: dict[str, object]
    task_test_command: dict[str, object]
    policy_pack: dict[str, object]


@dataclass
class ValidationCheck:
    name: str
    status: str
    summary: str
    details: list[str]
    reason_codes: list[str]


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


@dataclass(frozen=True)
class ValidationProfileCandidate:
    profile: str
    source: str
    field: str


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
        "--task-test-command",
        help="Optional task-specific Python test command to run before profile-level commands.",
    )
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

    policy_pack = resolve_policy_pack_reference(profile_name, profile_data)

    return ValidationProfile(
        name=profile_name,
        description=str(profile_data.get("description", "")),
        commands=[item for item in profile_data.get("commands", []) if isinstance(item, dict)],
        required_artifacts=[str(item) for item in profile_data.get("required_artifacts", [])],
        non_empty_artifacts=[str(item) for item in profile_data.get("non_empty_artifacts", [])],
        review_checks=[str(item) for item in profile_data.get("review_checks", [])],
        consistency_checks=[str(item) for item in profile_data.get("consistency_checks", [])],
        changed_file_policy=profile_data.get("changed_file_policy", {})
        if isinstance(profile_data.get("changed_file_policy", {}), dict)
        else {},
        task_test_command=profile_data.get("task_test_command", {})
        if isinstance(profile_data.get("task_test_command", {}), dict)
        else {},
        policy_pack=policy_pack,
    )


def read_text_if_exists(file_path: Path) -> str:
    if not file_path.exists() or not file_path.is_file():
        return ""
    return file_path.read_text(encoding="utf-8", errors="replace")


def read_json_if_exists(file_path: Path) -> dict[str, object]:
    if not file_path.exists() or not file_path.is_file():
        return {}
    try:
        data = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


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


def build_check(
    name: str,
    status: str,
    summary: str,
    details: list[str],
    reason_codes: list[str] | None = None,
) -> ValidationCheck:
    return ValidationCheck(
        name=name,
        status=status,
        summary=summary,
        details=details,
        reason_codes=reason_codes or [],
    )


def nested_reason_code(policy: dict[str, object], key: str, default: str) -> str:
    reason_codes = policy.get("reason_codes", {})
    if isinstance(reason_codes, dict):
        configured = reason_codes.get(key)
        if isinstance(configured, str) and configured.strip():
            return configured.strip()
    return default


def severity_for_status(status: str) -> str:
    if status == "failed":
        return "blocker"
    if status == "needs_review":
        return "review"
    return "info"


def reason_source(
    *,
    code: str,
    status: str,
    source: str,
    name: str,
    summary: str,
    details: list[str] | None = None,
) -> dict[str, object]:
    return {
        "code": code,
        "status": status,
        "severity": severity_for_status(status),
        "source": source,
        "name": name,
        "summary": summary,
        "details": details or [],
    }


def validate_artifact_presence(run_dir: Path, required_artifacts: list[str]) -> ValidationCheck:
    if not required_artifacts:
        return build_check(
            name="artifact_presence",
            status="passed",
            summary="No required artifact presence checks were configured.",
            details=[],
            reason_codes=["artifact_presence.not_required"],
        )

    if not run_dir.exists():
        return build_check(
            name="artifact_presence",
            status="failed",
            summary="Run directory does not exist.",
            details=[f"Missing run directory: {run_dir}"],
            reason_codes=["run_directory.missing"],
        )

    missing = [artifact for artifact in required_artifacts if not (run_dir / artifact).exists()]
    if missing:
        return build_check(
            name="artifact_presence",
            status="failed",
            summary="Required run artifacts are missing.",
            details=[f"Missing artifact: {artifact}" for artifact in missing],
            reason_codes=["artifact_presence.missing"],
        )

    return build_check(
        name="artifact_presence",
        status="passed",
        summary="All required run artifacts are present.",
        details=[f"Found {len(required_artifacts)} required artifacts."],
        reason_codes=["artifact_presence.present"],
    )


def validate_non_empty_artifacts(run_dir: Path, artifact_names: list[str]) -> ValidationCheck:
    if not artifact_names:
        return build_check(
            name="artifact_non_empty",
            status="passed",
            summary="No required non-empty artifact checks were configured.",
            details=[],
            reason_codes=["artifact_non_empty.not_required"],
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
            reason_codes=["artifact_non_empty.empty"],
        )

    return build_check(
        name="artifact_non_empty",
        status="passed",
        summary="Required artifacts contain content.",
        details=[f"Checked {len(artifact_names)} artifacts for non-empty content."],
        reason_codes=["artifact_non_empty.present"],
    )


def normalize_changed_file(path_text: str) -> str:
    normalized = path_text.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def parse_git_status_changed_files(project_root: Path, run_dir: Path) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--short", "--untracked-files=all"],
        cwd=project_root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []

    changed_files: list[str] = []
    run_dir_text = normalize_changed_file(str(run_dir.relative_to(project_root))) if run_dir.is_relative_to(project_root) else ""
    for raw_line in result.stdout.splitlines():
        if len(raw_line) < 4:
            continue
        path_text = raw_line[3:].strip()
        if " -> " in path_text:
            path_text = path_text.rsplit(" -> ", 1)[1]
        changed_file = normalize_changed_file(path_text.strip('"'))
        if run_dir_text and (changed_file == run_dir_text or changed_file.startswith(f"{run_dir_text}/")):
            continue
        if changed_file.startswith("runs/"):
            continue
        changed_files.append(changed_file)
    return sorted(set(changed_files))


def parse_run_log_changed_files(run_dir: Path) -> tuple[list[str], bool]:
    changed_files: list[str] = []
    has_files_touched_entry = False
    for entry in read_jsonl_entries(run_dir / "run_log.jsonl"):
        files_touched = entry.get("files_touched", [])
        if not isinstance(files_touched, list):
            continue
        has_files_touched_entry = True
        changed_files.extend(str(item) for item in files_touched if item is not None)
    return (
        sorted(set(normalize_changed_file(item) for item in changed_files if normalize_changed_file(item))),
        has_files_touched_entry,
    )


def read_jsonl_entries(file_path: Path) -> list[dict[str, object]]:
    if not file_path.exists():
        return []
    entries: list[dict[str, object]] = []
    for line in file_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
    return entries


def collect_changed_files(args_changed_files: list[str], run_dir: Path, project_root: Path) -> tuple[list[str], str]:
    explicit_files = sorted(set(normalize_changed_file(item) for item in args_changed_files if normalize_changed_file(item)))
    if explicit_files:
        return explicit_files, "cli_changed_files"

    run_log_files, has_run_log_files_touched = parse_run_log_changed_files(run_dir)
    if has_run_log_files_touched:
        return run_log_files, "run_log_files_touched"

    return parse_git_status_changed_files(project_root, run_dir), "git_status"


def matches_any_pattern(path_text: str, patterns: list[str]) -> bool:
    normalized = normalize_changed_file(path_text)
    return any(fnmatch.fnmatchcase(normalized, normalize_changed_file(pattern)) for pattern in patterns)


def validate_changed_file_policy(
    profile: ValidationProfile,
    changed_files: list[str],
    source: str,
    project_root: Path | None = None,
    run_dir: Path | None = None,
) -> ValidationCheck | None:
    if not profile.changed_file_policy:
        return None

    require_actual_diff = bool(profile.changed_file_policy.get("require_actual_diff", False))
    require_non_empty = bool(profile.changed_file_policy.get("require_non_empty", False))
    allowed_patterns = [
        str(item)
        for item in profile.changed_file_policy.get("allowed_patterns", [])
        if item is not None
    ]
    forbidden_patterns = [
        str(item)
        for item in profile.changed_file_policy.get("forbidden_patterns", [])
        if item is not None
    ]

    violations: list[str] = []
    violation_codes: list[str] = []

    def add_violation(detail: str, code_key: str, default_code: str) -> None:
        violations.append(detail)
        violation_codes.append(nested_reason_code(profile.changed_file_policy, code_key, default_code))

    actual_changed_files: list[str] | None = None
    if require_actual_diff:
        if project_root is None or run_dir is None:
            add_violation(
                "Actual changed-file evidence is required but unavailable.",
                "actual_diff_unavailable",
                "changed_file_policy.actual_diff_unavailable",
            )
        else:
            actual_changed_files = parse_git_status_changed_files(project_root, run_dir)
            reported_changed_file_set = set(changed_files)
            actual_changed_file_set = set(actual_changed_files)
            for changed_file in changed_files:
                if changed_file not in actual_changed_file_set:
                    add_violation(
                        f"Claimed changed file has no worktree diff: {changed_file}",
                        "claimed_without_diff",
                        "changed_file_policy.claimed_without_diff",
                    )
            if source != "git_status":
                for actual_changed_file in actual_changed_files:
                    if actual_changed_file not in reported_changed_file_set:
                        add_violation(
                            f"Unreported worktree diff file: {actual_changed_file}",
                            "unreported_worktree_diff",
                            "changed_file_policy.unreported_worktree_diff",
                        )

    effective_changed_files = sorted(set(changed_files) | set(actual_changed_files or []))
    if require_non_empty and not effective_changed_files:
        add_violation(
            "Changed-file evidence is required but no changed files were reported or discovered.",
            "empty",
            "changed_file_policy.empty",
        )

    for changed_file in effective_changed_files:
        if forbidden_patterns and matches_any_pattern(changed_file, forbidden_patterns):
            add_violation(
                f"Forbidden changed file: {changed_file}",
                "forbidden",
                "changed_file_policy.forbidden",
            )
            continue
        if allowed_patterns and not matches_any_pattern(changed_file, allowed_patterns):
            add_violation(
                f"Changed file is outside allowed scope: {changed_file}",
                "outside_allowed_scope",
                "changed_file_policy.outside_allowed_scope",
            )

    details = [f"Changed-file source: {source}"]
    if require_actual_diff:
        details.append("Actual changed-file evidence required: true")
        if actual_changed_files is not None:
            details.append("Actual changed-file source: git_status")
            details.append(f"Actual changed files found: {len(actual_changed_files)}")
    if require_non_empty:
        details.append("Non-empty changed-file evidence required: true")

    if violations:
        return build_check(
            name="changed_file_policy",
            status="failed",
            summary="Changed files violate the validation profile policy.",
            details=[*details, *violations],
            reason_codes=sorted(set(violation_codes)),
        )

    return build_check(
        name="changed_file_policy",
        status="passed",
        summary="Changed files match the validation profile policy.",
        details=[
            *details,
            f"Checked {len(effective_changed_files)} changed files.",
        ],
        reason_codes=[
            nested_reason_code(
                profile.changed_file_policy,
                "passed",
                "changed_file_policy.passed",
            )
        ],
    )


def model_selection_validation_profile(run_dir: Path) -> str | None:
    selection = read_json_if_exists(run_dir / "model_selection.json")
    profile = selection.get("validation_profile")
    if isinstance(profile, str) and profile.strip():
        return profile.strip()
    return None


def profile_value(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def task_metadata_validation_profile(run_dir: Path) -> ValidationProfileCandidate | None:
    metadata = read_json_if_exists(run_dir / "task_metadata.json")
    profile = profile_value(metadata, "validation_profile")
    if profile:
        return ValidationProfileCandidate(profile=profile, source="task_metadata", field="validation_profile")
    return None


def policy_pack_selection_validation_profiles(run_dir: Path) -> list[ValidationProfileCandidate]:
    selection = read_json_if_exists(run_dir / "policy_pack_selection.json")
    candidates: list[ValidationProfileCandidate] = []
    if selection and (
        str(selection.get("status") or "") != "selected"
        or selection.get("ok") is False
    ):
        return candidates

    for field in (
        "recommended_validation_profile",
        "selected_validation_profile",
        "validation_profile",
        "selected_profile",
        "profile",
    ):
        profile = profile_value(selection, field)
        if profile:
            candidates.append(
                ValidationProfileCandidate(profile=profile, source="policy_pack_selection", field=field)
            )

    policy_pack_candidates = [
        (field, policy_pack)
        for field in ("recommended_policy_pack", "selected_policy_pack", "policy_pack")
        if (policy_pack := profile_value(selection, field))
    ]
    if not policy_pack_candidates:
        return candidates

    catalog = load_policy_pack_catalog()
    for field, policy_pack in policy_pack_candidates:
        pack_data = catalog.get(policy_pack, {})
        mapped_profile = pack_data.get("validation_profile") if isinstance(pack_data, dict) else None
        profile = mapped_profile.strip() if isinstance(mapped_profile, str) and mapped_profile.strip() else policy_pack
        candidates.append(ValidationProfileCandidate(profile=profile, source="policy_pack_selection", field=field))

    return candidates


def selected_validation_profile_candidates(run_dir: Path) -> list[ValidationProfileCandidate]:
    candidates: list[ValidationProfileCandidate] = []
    metadata_candidate = task_metadata_validation_profile(run_dir)
    if metadata_candidate is not None:
        candidates.append(metadata_candidate)
    candidates.extend(policy_pack_selection_validation_profiles(run_dir))

    selection_profile = model_selection_validation_profile(run_dir)
    if selection_profile:
        candidates.append(
            ValidationProfileCandidate(
                profile=selection_profile,
                source="model_selection",
                field="validation_profile",
            )
        )
    return candidates


def has_profile_selection_artifact(run_dir: Path) -> bool:
    return any(
        (run_dir / artifact).exists()
        for artifact in ("task_metadata.json", "policy_pack_selection.json", "model_selection.json")
    )


def known_validation_profile_names() -> set[str]:
    raw_data = load_simple_yaml(WORKBENCH_ROOT / "configs" / "validation_profiles.yaml")
    profiles = raw_data.get("profiles", {})
    if not isinstance(profiles, dict):
        return set()
    return {str(profile_name) for profile_name in profiles}


def profile_candidate_label(candidate: ValidationProfileCandidate) -> str:
    return f"{candidate.source}.{candidate.field}={candidate.profile}"


def validate_selected_profile_candidates(candidates: list[ValidationProfileCandidate]) -> None:
    known_profiles = known_validation_profile_names()
    invalid_candidates = [candidate for candidate in candidates if candidate.profile not in known_profiles]
    if invalid_candidates:
        invalid_details = ", ".join(profile_candidate_label(candidate) for candidate in invalid_candidates)
        valid_details = ", ".join(sorted(known_profiles))
        raise ValueError(
            f"Invalid selected validation profile: {invalid_details}. "
            f"Valid profiles are: {valid_details}."
        )

    selected_profiles = {candidate.profile for candidate in candidates}
    if len(selected_profiles) > 1:
        selected_details = ", ".join(profile_candidate_label(candidate) for candidate in candidates)
        raise ValueError(
            "Conflicting selected validation profiles: "
            f"{selected_details}. Pass --profile to choose explicitly or update the run artifacts to agree."
        )


def resolve_validation_profile_name(args_profile: str | None, run_dir: Path, project_default: str) -> tuple[str, str]:
    if args_profile:
        return args_profile, "cli_profile"

    candidates = selected_validation_profile_candidates(run_dir)
    if candidates:
        validate_selected_profile_candidates(candidates)
        candidate = candidates[0]
        return candidate.profile, candidate.source

    if has_profile_selection_artifact(run_dir):
        raise ValueError(
            "No selected validation profile found. Pass --profile, set task_metadata.json validation_profile, "
            "write policy_pack_selection.json recommended_validation_profile, or provide model_selection.json "
            "validation_profile. Project default fallback is limited to legacy/scaffold runs."
        )

    return project_default, "project_default"


def normalized_task_test_command(command: str | None) -> str:
    return " ".join((command or "").strip().split())


def task_test_command_policy_check(profile: ValidationProfile, command: str | None) -> ValidationCheck | None:
    policy = profile.task_test_command
    if not policy:
        return None

    normalized = normalized_task_test_command(command)
    required = bool(policy.get("required", False))
    allowed_prefixes = [str(item).lower() for item in policy.get("allowed_prefixes", [])]

    if not normalized:
        if required:
            return build_check(
                name="task_test_command",
                status="failed",
                summary="Task-specific test command is required for this validation profile.",
                details=[
                    "Pass --task-test-command or the MCP task_test_command argument with the exact focused test command.",
                ],
                reason_codes=["task_test_command.missing"],
            )
        return build_check(
            name="task_test_command",
            status="passed",
            summary="No task-specific test command was required.",
            details=[],
            reason_codes=["task_test_command.not_required"],
        )

    lowered = normalized.lower()
    if allowed_prefixes and not any(lowered.startswith(prefix) for prefix in allowed_prefixes):
        return build_check(
            name="task_test_command",
            status="failed",
            summary="Task-specific test command is outside the allowed command family.",
            details=[
                f"Allowed prefixes: {', '.join(allowed_prefixes)}",
                f"Received command: {normalized}",
            ],
            reason_codes=["task_test_command.invalid_prefix"],
        )

    if re.search(r"[;&|<>`\r\n]", normalized):
        return build_check(
            name="task_test_command",
            status="failed",
            summary="Task-specific test command contains shell control syntax.",
            details=["Use a single Python pytest or unittest command without shell chaining or redirection."],
            reason_codes=["task_test_command.shell_control_syntax"],
        )

    return build_check(
        name="task_test_command",
        status="passed",
        summary="Task-specific test command accepted for execution.",
        details=[f"Command: {normalized}"],
        reason_codes=["task_test_command.accepted"],
    )


def validate_policy_required_tests(
    profile: ValidationProfile,
    commands_run: list[CommandResult],
) -> ValidationCheck | None:
    required_tests = profile.policy_pack.get("required_tests", [])
    if not isinstance(required_tests, list):
        return None

    required_names = [str(item).strip() for item in required_tests if str(item).strip()]
    if not required_names:
        return None

    command_status_by_name = {command.name: command.status for command in commands_run}
    missing = [name for name in required_names if name not in command_status_by_name]
    failed = [name for name in required_names if command_status_by_name.get(name) == "failed"]

    if missing:
        return build_check(
            name="policy_required_tests",
            status="needs_review",
            summary="Policy-required tests were not found in the validation command evidence.",
            details=[f"Missing required test command: {name}" for name in missing],
            reason_codes=[
                nested_reason_code(
                    profile.policy_pack,
                    "required_test_missing",
                    "policy.required_test_missing",
                )
            ],
        )

    if failed:
        return build_check(
            name="policy_required_tests",
            status="failed",
            summary="Policy-required tests were run but did not pass.",
            details=[f"Failed required test command: {name}" for name in failed],
            reason_codes=[
                nested_reason_code(
                    profile.policy_pack,
                    "required_test_failed",
                    "policy.required_test_failed",
                )
            ],
        )

    return build_check(
        name="policy_required_tests",
        status="passed",
        summary="All policy-required tests are present and passing.",
        details=[f"Required test command passed: {name}" for name in required_names],
        reason_codes=[
            nested_reason_code(
                profile.policy_pack,
                "required_tests_passed",
                "policy.required_tests_passed",
            )
        ],
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
                reason_codes=["missing_context.missing"],
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
                reason_codes=["missing_context.none"],
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
                reason_codes=["missing_context.needs_review"],
            ),
            sections,
        )

    return (
        build_check(
            name="missing_context_review",
            status="passed",
            summary="missing_context.md contains informational notes only.",
            details=[f"Info: {note}" for note in info_notes] or ["No review-blocking missing context items remain."],
            reason_codes=["missing_context.info_only"],
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
            reason_codes=["model_output.missing"],
        )

    status = parse_model_output_status(file_path)
    if status == "response_captured":
        return build_check(
            name="model_output_status",
            status="passed",
            summary="model_output.md indicates an accepted execution state.",
            details=[f"Model output status: {status}"],
            reason_codes=["model_output.response_captured"],
        )

    if status == "handoff_required":
        return build_check(
            name="model_output_status",
            status="needs_review",
            summary="model_output.md indicates manual model handoff is still required.",
            details=["Model output status: handoff_required"],
            reason_codes=["model_output.handoff_required"],
        )

    if status is None:
        return build_check(
            name="model_output_status",
            status="failed",
            summary="model_output.md does not contain a parseable status field.",
            details=["Expected a metadata line in the form: - Status: `response_captured|handoff_required`"],
            reason_codes=["model_output.status_unparseable"],
        )

    return build_check(
        name="model_output_status",
        status="failed",
        summary="model_output.md contains an unsupported status value.",
        details=[f"Unsupported model output status: {status}"],
        reason_codes=["model_output.status_unsupported"],
    )


def validate_captured_response_format(file_path: Path) -> ValidationCheck:
    text = read_text_if_exists(file_path)
    if not text.strip():
        return build_check(
            name="captured_response_format",
            status="failed",
            summary="model_output.md is missing or empty.",
            details=["The validator could not inspect the captured response because model_output.md has no readable content."],
            reason_codes=["captured_response.missing"],
        )

    status = parse_model_output_status(file_path)
    if status != "response_captured":
        return build_check(
            name="captured_response_format",
            status="passed",
            summary="Captured-response format check is not applicable until a response is captured.",
            details=[f"Model output status: {status or 'unknown'}"],
            reason_codes=["captured_response.not_applicable"],
        )

    response_text = extract_preferred_response_text(text)
    if not response_text:
        return build_check(
            name="captured_response_format",
            status="failed",
            summary="model_output.md is marked response_captured but does not contain a readable captured response section.",
            details=["Expected either ## Normalized Response or ## Captured Response content."],
            reason_codes=["captured_response.content_missing"],
        )

    missing = missing_required_sections(response_text)
    if missing:
        return build_check(
            name="captured_response_format",
            status="needs_review",
            summary="Captured model response is missing the preferred structured sections.",
            details=[f"Missing required response section: {section}" for section in missing],
            reason_codes=["captured_response.required_sections_missing"],
        )

    section_used = "normalized" if "## Normalized Response" in text else "captured"
    return build_check(
        name="captured_response_format",
        status="passed",
        summary="Captured model response matches the preferred structured format.",
        details=[f"Validated {section_used} response section."],
        reason_codes=["captured_response.structured"],
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
            reason_codes=["artifact_consistency.not_required"],
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
            reason_codes=["artifact_consistency.mismatch"],
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
        reason_codes=["artifact_consistency.passed"],
    )


def run_profile_commands(
    project_root: Path,
    profile: ValidationProfile,
    task_test_command: str | None = None,
) -> tuple[list[CommandResult], list[dict[str, str]]]:
    commands_run: list[CommandResult] = []
    commands_not_run: list[dict[str, str]] = []

    commands = [*profile.commands]
    normalized_task_command = normalized_task_test_command(task_test_command)
    task_command_check = task_test_command_policy_check(profile, normalized_task_command)
    if task_command_check is not None:
        if task_command_check.status == "passed" and normalized_task_command:
            commands.insert(
                0,
                {
                    "name": "task_test_command",
                    "command": normalized_task_command,
                    "cwd": ".",
                    "required": True,
                    "weight": 3.0,
                },
            )
        elif task_command_check.status == "failed":
            commands_not_run.append(
                {
                    "name": "task_test_command",
                    "reason": task_command_check.summary,
                }
            )
            return commands_run, commands_not_run

    if not commands:
        commands_not_run.append({"name": "none", "reason": "Profile does not define deterministic commands."})
        return commands_run, commands_not_run

    for raw_command in commands:
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


def policy_reason_code(profile: ValidationProfile, key: str, default: str) -> str:
    return nested_reason_code(profile.policy_pack, key, default)


def collect_validation_reason_sources(
    profile: ValidationProfile,
    overall_status: str,
    commands_run: list[CommandResult],
    commands_not_run: list[dict[str, str]],
    artifact_checks: list[ValidationCheck],
    review_checks: list[ValidationCheck],
) -> list[dict[str, object]]:
    sources: list[dict[str, object]] = []

    for command in commands_run:
        if command.required and command.status == "failed":
            sources.append(
                reason_source(
                    code=f"command_failed:{command.name}",
                    status="failed",
                    source="commands_run",
                    name=command.name,
                    summary=f"Required validation command failed: {command.name}",
                    details=[f"exit_code={command.exit_code}", f"command={command.command}"],
                )
            )

    for command in commands_not_run:
        name = str(command.get("name", "unknown"))
        sources.append(
            reason_source(
                code=f"command_not_run:{name}",
                status="failed",
                source="commands_not_run",
                name=name,
                summary=str(command.get("reason", "Validation command was not run.")),
                details=[],
            )
        )

    for section_name, checks in (("artifact_checks", artifact_checks), ("review_checks", review_checks)):
        for check in checks:
            if check.status not in {"failed", "needs_review"}:
                continue
            codes = check.reason_codes or [f"{section_name}:{check.status}:{check.name}"]
            for code in codes:
                sources.append(
                    reason_source(
                        code=code,
                        status=check.status,
                        source=section_name,
                        name=check.name,
                        summary=check.summary,
                        details=check.details,
                    )
                )

    if not sources:
        if overall_status == "passed":
            sources.append(
                reason_source(
                    code=policy_reason_code(profile, "accepted", "validation.accepted"),
                    status="passed",
                    source="validation_report",
                    name=profile.name,
                    summary="Validation passed and the run is sign-off ready.",
                    details=[],
                )
            )
        else:
            sources.append(
                reason_source(
                    code=policy_reason_code(profile, overall_status, f"validation.{overall_status}"),
                    status=overall_status,
                    source="validation_report",
                    name=profile.name,
                    summary=f"Validation finished with overall status: {overall_status}.",
                    details=[],
                )
            )

    return sources


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

    if any(check.status == "failed" for check in artifact_checks):
        confidence = min(confidence, 0.40)

    if any(check.status == "needs_review" for check in artifact_checks):
        confidence = min(confidence, 0.75)

    if any(check.status == "needs_review" for check in review_checks):
        confidence = min(confidence, 0.75)

    confidence = round(confidence, 2)
    all_checks = [*artifact_checks, *review_checks]
    reason_sources = collect_validation_reason_sources(
        profile=profile,
        overall_status=overall_status,
        commands_run=commands_run,
        commands_not_run=commands_not_run,
        artifact_checks=artifact_checks,
        review_checks=review_checks,
    )
    policy_pack_summary = {
        "name": str(profile.policy_pack.get("name", profile.name)),
        "version": str(profile.policy_pack.get("version", "v0.2")),
    }
    policy_pack_source = profile.policy_pack.get("source")
    if isinstance(policy_pack_source, str) and policy_pack_source.strip():
        policy_pack_summary["source"] = policy_pack_source.strip()

    return {
        "run_id": run_id,
        "project": project_key,
        "profile": profile.name,
        "policy_pack": policy_pack_summary,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "commands_run": [asdict(result) for result in commands_run],
        "commands_not_run": commands_not_run,
        "artifact_checks": [asdict(check) for check in artifact_checks],
        "review_checks": [asdict(check) for check in review_checks],
        "missing_context_notes": missing_context_notes,
        "overall_status": overall_status,
        "sign_off_ready": overall_status == "passed",
        "confidence": confidence,
        "reason_sources": reason_sources,
        "reason_codes": [str(source.get("code")) for source in reason_sources],
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
    run_dir = resolve_cli_path(args.out_dir, project.root)
    run_dir.mkdir(parents=True, exist_ok=True)
    profile_name, profile_source = resolve_validation_profile_name(args.profile, run_dir, project.default_validation_profile)
    profile = load_validation_profile(profile_name)
    task_test_command = getattr(args, "task_test_command", None)

    commands_run, commands_not_run = run_profile_commands(project.root, profile, task_test_command=task_test_command)

    artifact_checks: list[ValidationCheck] = []
    task_command_check = task_test_command_policy_check(profile, task_test_command)
    if task_command_check is not None:
        artifact_checks.append(task_command_check)
    artifact_checks.append(validate_artifact_presence(run_dir, profile.required_artifacts))
    artifact_checks.append(validate_non_empty_artifacts(run_dir, profile.non_empty_artifacts))
    policy_required_tests_check = validate_policy_required_tests(profile, commands_run)
    if policy_required_tests_check is not None:
        artifact_checks.append(policy_required_tests_check)
    changed_files, changed_file_source = collect_changed_files(args.changed_files, run_dir, project.root)
    changed_file_check = validate_changed_file_policy(
        profile,
        changed_files,
        changed_file_source,
        project_root=project.root,
        run_dir=run_dir,
    )
    if changed_file_check is not None:
        artifact_checks.append(changed_file_check)

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
    report["profile_source"] = profile_source
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
