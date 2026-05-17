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


@dataclass(frozen=True)
class ArtifactRead:
    label: str
    file_name: str
    path: Path
    present: bool
    payload: dict[str, Any]
    error: str | None = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a PR-facing Workbench acceptance gate artifact.")
    parser.add_argument("--run-dir", required=True, help="Run directory containing Workbench evidence artifacts.")
    parser.add_argument("--out", required=True, help="Markdown PR comment artifact path to write.")
    parser.add_argument("--json-out", required=True, help="JSON PR gate decision artifact path to write.")
    parser.add_argument(
        "--fail-on-block",
        action="store_true",
        help="Exit non-zero when the rendered PR gate outcome is block.",
    )
    return parser


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


def reason_sources_from(*payloads: dict[str, object]) -> list[dict[str, object]]:
    sources: list[dict[str, object]] = []
    for payload in payloads:
        for source in list_from(payload.get("reason_sources")):
            if isinstance(source, dict):
                sources.append(source)
    return sources


def has_blocker_reason_source(*payloads: dict[str, object]) -> bool:
    return any(str(source.get("severity")) == "blocker" for source in reason_sources_from(*payloads))


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


def decision_from_evidence(run_dir: Path) -> dict[str, object]:
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

    if blocking_problems:
        outcome = "block"
        reason = " ".join(blocking_problems)
        next_action = default_next_action(outcome)
    elif validation_status == "passed" and report.get("sign_off_ready") is True and quality_gate_status == "accepted":
        outcome = "accept"
        reason = first_reason_summary(decision, report) or "Validation passed and the quality gate accepted the run."
        next_action = str(decision.get("next_action") or default_next_action(outcome))
    elif validation_status == "failed" or quality_gate_status == "revision_required" or has_blocker_reason_source(report, decision):
        outcome = "block"
        reason = (
            str(decision.get("reason") or "").strip()
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
        "validation_status": validation_status,
        "quality_gate_status": quality_gate_status,
        "reason": reason,
        "reason_codes": reason_codes,
        "evidence": evidence,
        "required_next_action": next_action,
    }


def markdown_escape(value: object) -> str:
    return str(value).replace("|", "\\|")


def render_comment(decision: dict[str, object]) -> str:
    outcome = str(decision.get("outcome", "block"))
    reason_codes = [str(code) for code in list_from(decision.get("reason_codes"))]
    evidence = [entry for entry in list_from(decision.get("evidence")) if isinstance(entry, dict)]
    lines = [
        f"# AI Workbench PR Gate: {display_outcome(outcome)}",
        "",
        f"**Run ID:** `{decision.get('run_id', 'unknown')}`",
        f"**Reason:** {decision.get('reason', 'unknown')}",
        f"**Required next action:** {decision.get('required_next_action', default_next_action(outcome))}",
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
    run_dir = Path(str(args.run_dir))
    decision = decision_from_evidence(run_dir)
    write_outputs(decision, Path(str(args.out)), Path(str(args.json_out)))
    return decision


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    decision = pr_gate_payload(args)
    print(f"pr_gate_outcome={decision['outcome']}")
    print(f"pr_gate_comment={args.out}")
    print(f"pr_gate_decision={args.json_out}")
    if args.fail_on_block and decision["outcome"] == "block":
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
