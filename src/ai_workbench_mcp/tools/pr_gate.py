from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any


SCHEMA_VERSION = 1
OPERATION = "workbench_pr_gate"
OUTCOME_LABELS = {
    "accept": "Accept",
    "needs_review": "Needs Review",
    "block": "Block",
}
STANDARD_EVIDENCE = (
    ("validation_report", "validation_report.json"),
    ("revision_decision", "revision_decision.json"),
    ("model_output", "model_output.md"),
    ("run_log", "run_log.jsonl"),
)
ACCEPTANCE_EVIDENCE_MISSING_CODE = "pr_gate.acceptance_evidence_missing"
ACCEPTANCE_EVIDENCE_MISSING_REASON = "No complete Workbench acceptance evidence found for this PR."
SCAFFOLD_PROFILES = {"scaffold"}


@dataclass(frozen=True)
class ArtifactRead:
    label: str
    file_name: str
    path: Path
    present: bool
    payload: dict[str, Any]
    error: str | None = None


@dataclass(frozen=True)
class EvidenceSelection:
    run_dir: Path
    evidence_source: str
    source_run_dir: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a PR-facing Workbench acceptance gate artifact.")
    parser.add_argument("--run-dir", help="Run directory containing Workbench acceptance evidence artifacts.")
    parser.add_argument("--runs-dir", help="Parent directory containing Workbench run folders.")
    parser.add_argument("--run-id", help="Run folder name to resolve under --runs-dir.")
    parser.add_argument(
        "--fallback-run-dir",
        help="Fallback scaffold or CI evidence directory used only when no full acceptance run is supplied.",
    )
    parser.add_argument("--out", required=True, help="Markdown PR comment artifact path to write.")
    parser.add_argument("--json-out", required=True, help="JSON PR gate decision artifact path to write.")
    parser.add_argument(
        "--fail-on-block",
        action="store_true",
        help="Exit non-zero when the rendered PR gate outcome is block.",
    )
    return parser


def normalized_public_path(value: str) -> str:
    return value.strip().replace("\\", "/").lstrip("./")


def safe_source_label(path: Path, preferred: str | None = None) -> str:
    if preferred and not Path(preferred).is_absolute():
        return normalized_public_path(preferred)
    try:
        cwd = Path.cwd().resolve()
        resolved = path.resolve()
        return normalized_public_path(str(resolved.relative_to(cwd)))
    except (OSError, ValueError):
        return path.name or "unknown"


def resolve_evidence_selection(args: argparse.Namespace | SimpleNamespace) -> EvidenceSelection:
    run_dir_value = str(getattr(args, "run_dir", "") or "").strip()
    runs_dir_value = str(getattr(args, "runs_dir", "") or "").strip()
    run_id_value = str(getattr(args, "run_id", "") or "").strip()
    fallback_value = str(getattr(args, "fallback_run_dir", "") or "").strip()

    if run_dir_value and (runs_dir_value or run_id_value):
        raise ValueError("Use either --run-dir or --runs-dir with --run-id, not both.")
    if bool(runs_dir_value) != bool(run_id_value):
        raise ValueError("--runs-dir and --run-id must be provided together.")

    if run_dir_value:
        run_dir = Path(run_dir_value)
        return EvidenceSelection(
            run_dir=run_dir,
            evidence_source="acceptance_run",
            source_run_dir=safe_source_label(run_dir, run_dir_value),
        )

    if runs_dir_value and run_id_value:
        run_dir = Path(runs_dir_value) / run_id_value
        return EvidenceSelection(
            run_dir=run_dir,
            evidence_source="acceptance_run",
            source_run_dir=safe_source_label(run_dir, f"{runs_dir_value}/{run_id_value}"),
        )

    if fallback_value:
        run_dir = Path(fallback_value)
        return EvidenceSelection(
            run_dir=run_dir,
            evidence_source="fallback_scaffold" if run_dir.exists() else "missing",
            source_run_dir=safe_source_label(run_dir, fallback_value),
        )

    raise ValueError("Provide --run-dir, --runs-dir with --run-id, or --fallback-run-dir.")


def read_json_artifact(run_dir: Path, label: str, file_name: str) -> ArtifactRead:
    path = run_dir / file_name
    if not path.exists():
        return ArtifactRead(label=label, file_name=file_name, path=path, present=False, payload={})
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return ArtifactRead(
            label=label,
            file_name=file_name,
            path=path,
            present=True,
            payload={},
            error=f"Invalid JSON: {exc.msg}",
        )
    except OSError as exc:
        return ArtifactRead(
            label=label,
            file_name=file_name,
            path=path,
            present=True,
            payload={},
            error=f"Unreadable artifact: {exc}",
        )
    if not isinstance(payload, dict):
        return ArtifactRead(
            label=label,
            file_name=file_name,
            path=path,
            present=True,
            payload={},
            error="JSON artifact is not an object.",
        )
    return ArtifactRead(label=label, file_name=file_name, path=path, present=True, payload=payload)


def evidence_entry(run_dir: Path, label: str, file_name: str) -> dict[str, object]:
    path = run_dir / file_name
    return {
        "label": label,
        "path": file_name,
        "present": path.exists(),
    }


def artifact_problem(read: ArtifactRead) -> str | None:
    if not read.present:
        return f"Missing required Workbench evidence: {read.file_name}."
    if read.error:
        return f"Unreadable Workbench evidence: {read.file_name} ({read.error})."
    return None


def list_from(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def dict_from(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def policy_pack_name_from(report: dict[str, object]) -> str:
    policy_pack = dict_from(report.get("policy_pack"))
    name = str(policy_pack.get("name") or "").strip()
    if name:
        return name
    profile = str(report.get("profile") or "").strip()
    if profile:
        return profile
    return "unknown"


def validation_profile_from(report: dict[str, object]) -> str:
    profile = str(report.get("profile") or "").strip()
    if profile:
        return profile
    return "unknown"


def first_non_empty_string(payload: dict[str, object], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        text = str(value or "").strip()
        if text:
            return text
    return None


def policy_pack_selection_mode_from(
    task_metadata: dict[str, object],
    policy_pack_selection: dict[str, object],
) -> str:
    keys = ("policy_pack_selection_mode", "profile_selection_mode", "selection_mode", "mode")
    for payload in (task_metadata, dict_from(task_metadata.get("policy_pack_selection")), policy_pack_selection):
        mode = first_non_empty_string(payload, keys)
        if mode:
            return mode
    return "unknown"


def policy_pack_selection_mode_for(run_dir: Path) -> str:
    task_metadata = read_json_artifact(run_dir, "task_metadata", "task_metadata.json").payload
    policy_pack_selection = read_json_artifact(run_dir, "policy_pack_selection", "policy_pack_selection.json").payload
    return policy_pack_selection_mode_from(task_metadata, policy_pack_selection)


def reason_codes_from(*payloads: dict[str, object]) -> list[str]:
    codes: list[str] = []
    seen: set[str] = set()
    for payload in payloads:
        for code in list_from(payload.get("reason_codes")):
            text = str(code)
            if text and text not in seen:
                codes.append(text)
                seen.add(text)
    return codes


def append_reason_code(codes: list[str], code: str) -> list[str]:
    if code not in codes:
        return [*codes, code]
    return codes


def reason_sources_from(*payloads: dict[str, object]) -> list[dict[str, object]]:
    sources: list[dict[str, object]] = []
    for payload in payloads:
        for source in list_from(payload.get("reason_sources")):
            if isinstance(source, dict):
                sources.append(source)
    return sources


def has_blocker_reason_source(*payloads: dict[str, object]) -> bool:
    return any(str(source.get("severity")) == "blocker" for source in reason_sources_from(*payloads))


def first_blocker_reason_summary(*payloads: dict[str, object]) -> str | None:
    for source in reason_sources_from(*payloads):
        if str(source.get("severity")) != "blocker":
            continue
        summary = source.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
    return None


def first_reason_summary(*payloads: dict[str, object]) -> str | None:
    for source in reason_sources_from(*payloads):
        summary = source.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary.strip()
    return None


def failed_command_reason(report: dict[str, object]) -> str | None:
    for command in list_from(report.get("commands_run")):
        command_data = dict_from(command)
        if command_data.get("required") is True and command_data.get("status") == "failed":
            return f"Required validation command failed: {command_data.get('name', 'unknown')}."
    for command in list_from(report.get("commands_not_run")):
        command_data = dict_from(command)
        name = command_data.get("name", "unknown")
        return f"Required validation command was not run: {name}."
    return None


def display_outcome(outcome: str) -> str:
    return OUTCOME_LABELS.get(outcome, outcome)


def default_next_action(outcome: str) -> str:
    if outcome == "accept":
        return "No Workbench action required before merge."
    if outcome == "needs_review":
        return "Review the Workbench findings, resolve required follow-up, then regenerate the PR gate artifact."
    return "Produce complete Workbench validation and quality-gate evidence, resolve blockers, then regenerate the PR gate artifact."


def is_scaffold_only_evidence(report: dict[str, object], evidence_source: str) -> bool:
    if evidence_source == "fallback_scaffold":
        return True
    profile = str(report.get("profile") or "").strip().lower()
    return profile in SCAFFOLD_PROFILES


def acceptance_evidence_missing_decision(
    *,
    run_dir: Path,
    evidence_source: str,
    source_run_dir: str,
    report: dict[str, object],
    evidence: list[dict[str, object]],
    decision: dict[str, object] | None = None,
) -> dict[str, object]:
    decision_payload = decision or {}
    reason_codes = append_reason_code(reason_codes_from(report, decision_payload), ACCEPTANCE_EVIDENCE_MISSING_CODE)
    return {
        "schema_version": SCHEMA_VERSION,
        "operation": OPERATION,
        "outcome": "block",
        "ok": True,
        "run_id": str(report.get("run_id") or decision_payload.get("run_id") or run_dir.name or "unknown"),
        "evidence_source": evidence_source,
        "source_run_dir": source_run_dir,
        "policy_pack": policy_pack_name_from(report),
        "validation_profile": validation_profile_from(report),
        "policy_pack_selection_mode": policy_pack_selection_mode_for(run_dir),
        "validation_status": str(report.get("overall_status", "unknown")),
        "quality_gate_status": str(decision_payload.get("final_status", "unknown")),
        "reason": ACCEPTANCE_EVIDENCE_MISSING_REASON,
        "reason_codes": reason_codes,
        "evidence": evidence,
        "required_next_action": (
            "Provide a complete Workbench acceptance run with validation_report.json and "
            "revision_decision.json, then regenerate the PR gate artifact."
        ),
    }


def decision_from_evidence(
    run_dir: Path,
    *,
    evidence_source: str = "acceptance_run",
    source_run_dir: str | None = None,
) -> dict[str, object]:
    validation_read = read_json_artifact(run_dir, "validation_report", "validation_report.json")
    decision_read = read_json_artifact(run_dir, "revision_decision", "revision_decision.json")
    evidence = [evidence_entry(run_dir, label, file_name) for label, file_name in STANDARD_EVIDENCE]

    blocking_problems = [
        problem
        for problem in (artifact_problem(validation_read), artifact_problem(decision_read))
        if problem is not None
    ]
    report = validation_read.payload
    decision = decision_read.payload
    validation_status = str(report.get("overall_status", "unknown"))
    quality_gate_status = str(decision.get("final_status", "unknown"))
    reason_codes = reason_codes_from(report, decision)
    source_label = source_run_dir or safe_source_label(run_dir)

    if validation_read.error is None and is_scaffold_only_evidence(report, evidence_source):
        return acceptance_evidence_missing_decision(
            run_dir=run_dir,
            evidence_source=evidence_source,
            source_run_dir=source_label,
            report=report,
            decision=decision,
            evidence=evidence,
        )
    if blocking_problems:
        outcome = "block"
        reason = " ".join(blocking_problems)
        next_action = default_next_action(outcome)
    elif validation_status == "passed" and report.get("sign_off_ready") is True and quality_gate_status == "accepted":
        outcome = "accept"
        reason = first_reason_summary(decision, report) or "Validation passed and the quality gate accepted the run."
        next_action = str(decision.get("next_action") or default_next_action(outcome))
    elif validation_status == "failed" or quality_gate_status == "revision_required" or has_blocker_reason_source(report, decision):
        blocker_reason = first_blocker_reason_summary(report, decision)
        outcome = "block"
        reason = (
            (
                blocker_reason
                if validation_status != "failed" and quality_gate_status != "revision_required"
                else None
            )
            or str(decision.get("reason") or "").strip()
            or blocker_reason
            or first_reason_summary(report, decision)
            or failed_command_reason(report)
            or "Workbench evidence contains blocker findings."
        )
        next_action = str(decision.get("next_action") or default_next_action(outcome))
    elif validation_status == "needs_review" or quality_gate_status == "review_required":
        outcome = "needs_review"
        reason = (
            str(decision.get("reason") or "").strip()
            or first_reason_summary(report, decision)
            or "Workbench evidence requires review before merge."
        )
        next_action = str(decision.get("next_action") or default_next_action(outcome))
    else:
        outcome = "block"
        reason = "Workbench evidence did not contain an accepted validation and quality-gate pair."
        next_action = default_next_action(outcome)

    return {
        "schema_version": SCHEMA_VERSION,
        "operation": OPERATION,
        "outcome": outcome,
        "ok": True,
        "run_id": str(report.get("run_id") or decision.get("run_id") or run_dir.name),
        "evidence_source": evidence_source,
        "source_run_dir": source_label,
        "policy_pack": policy_pack_name_from(report),
        "validation_profile": validation_profile_from(report),
        "policy_pack_selection_mode": policy_pack_selection_mode_for(run_dir),
        "validation_status": validation_status,
        "quality_gate_status": quality_gate_status,
        "reason": reason,
        "reason_codes": reason_codes,
        "evidence": evidence,
        "required_next_action": next_action,
    }


def fallback_decision_from_evidence(selection: EvidenceSelection) -> dict[str, object]:
    validation_read = read_json_artifact(selection.run_dir, "validation_report", "validation_report.json")
    report = validation_read.payload
    evidence = [evidence_entry(selection.run_dir, label, file_name) for label, file_name in STANDARD_EVIDENCE]
    return acceptance_evidence_missing_decision(
        run_dir=selection.run_dir,
        evidence_source=selection.evidence_source,
        source_run_dir=selection.source_run_dir,
        report=report,
        evidence=evidence,
    )


def markdown_escape(value: object) -> str:
    return str(value).replace("|", "\\|")


def evidence_present_value(evidence: list[object], label: str) -> str:
    for entry in evidence:
        if not isinstance(entry, dict):
            continue
        if entry.get("label") == label:
            return "yes" if entry.get("present") is True else "no"
    return "no"


def render_comment(decision: dict[str, object]) -> str:
    outcome = str(decision.get("outcome", "block"))
    reason_codes = [str(code) for code in list_from(decision.get("reason_codes"))]
    evidence = [entry for entry in list_from(decision.get("evidence")) if isinstance(entry, dict)]
    validation_present = evidence_present_value(evidence, "validation_report")
    revision_present = evidence_present_value(evidence, "revision_decision")
    lines = [
        f"# AI Workbench PR Gate: {display_outcome(outcome)}",
        "",
        f"Decision: {display_outcome(outcome)}",
        f"Why: {decision.get('reason', 'unknown')}",
        f"Required next action: {decision.get('required_next_action', default_next_action(outcome))}",
        f"Evidence present: validation_report {validation_present}, revision_decision {revision_present}",
        "",
        "## Details",
        "",
        f"**Run ID:** `{decision.get('run_id', 'unknown')}`",
        f"**Evidence source:** `{markdown_escape(decision.get('evidence_source', 'unknown'))}`",
        f"**Source run dir:** `{markdown_escape(decision.get('source_run_dir', 'unknown'))}`",
        f"**Policy pack:** `{markdown_escape(decision.get('policy_pack', 'unknown'))}`",
        f"**Validation profile:** `{markdown_escape(decision.get('validation_profile', 'unknown'))}`",
        f"**Selection mode:** `{markdown_escape(decision.get('policy_pack_selection_mode', 'unknown'))}`",
        "",
        "## Status",
        "",
        "| Check | Status |",
        "|---|---|",
        f"| Validation | `{markdown_escape(decision.get('validation_status', 'unknown'))}` |",
        f"| Quality gate | `{markdown_escape(decision.get('quality_gate_status', 'unknown'))}` |",
        "",
        "## Evidence",
        "",
        "| Artifact | Path | Present |",
        "|---|---|---|",
    ]
    for entry in evidence:
        present = "yes" if entry.get("present") is True else "no"
        lines.append(f"| {markdown_escape(entry.get('label', 'unknown'))} | `{markdown_escape(entry.get('path', 'unknown'))}` | {present} |")

    lines.extend(["", "## Reason Codes", ""])
    if reason_codes:
        lines.extend(f"- `{code}`" for code in reason_codes)
    else:
        lines.append("- None recorded")

    lines.extend(
        [
            "",
            "This artifact is generated from Workbench evidence only. It does not embed raw model output or provider logs.",
            "",
        ]
    )
    return "\n".join(lines)


def write_outputs(decision: dict[str, object], comment_path: Path, json_path: Path) -> None:
    comment_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    comment_path.write_text(render_comment(decision), encoding="utf-8")
    json_path.write_text(json.dumps(decision, indent=2) + "\n", encoding="utf-8")


def pr_gate_payload(args: argparse.Namespace | SimpleNamespace) -> dict[str, object]:
    selection = resolve_evidence_selection(args)
    if selection.evidence_source == "acceptance_run":
        decision = decision_from_evidence(
            selection.run_dir,
            evidence_source=selection.evidence_source,
            source_run_dir=selection.source_run_dir,
        )
    else:
        decision = fallback_decision_from_evidence(selection)
    write_outputs(decision, Path(str(args.out)), Path(str(args.json_out)))
    return decision


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        decision = pr_gate_payload(args)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"pr_gate_outcome={decision['outcome']}")
    print(f"pr_gate_comment={args.out}")
    print(f"pr_gate_decision={args.json_out}")
    if args.fail_on_block and decision["outcome"] == "block":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
