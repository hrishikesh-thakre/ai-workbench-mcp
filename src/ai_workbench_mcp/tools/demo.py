from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Sequence

from ai_workbench_mcp.tools.pr_gate import decision_from_evidence, write_outputs


DEMO_ROOT_NAME = "ai-workbench-demo"
DEMO_TIMESTAMP = "2026-05-19T00:00:00Z"
DEMO_NOTICE = (
    "Synthetic package-only demo fixture evidence. This is not a real target-repo "
    "acceptance run or a shortcut around validation and quality-gate evidence."
)


@dataclass(frozen=True)
class DemoScenario:
    folder: str
    expected_outcome: str
    run_id: str
    validation_report: dict[str, Any]
    revision_decision: dict[str, Any]
    task_metadata: dict[str, Any]
    model_output: str


@dataclass(frozen=True)
class DemoResult:
    root_dir: Path
    scenario: str
    outcome: str
    evidence_dir: Path
    comment_path: Path
    decision_path: Path


def _reason_source(
    *,
    code: str,
    status: str,
    severity: str,
    source: str,
    name: str,
    summary: str,
    details: list[str],
) -> dict[str, Any]:
    return {
        "code": code,
        "status": status,
        "severity": severity,
        "source": source,
        "name": name,
        "summary": summary,
        "details": details,
    }


def _base_task_metadata(
    *,
    run_id: str,
    task_type: str,
    risk: str,
    summary: str,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "project": "ai_workbench_demo_fixture",
        "task_type": task_type,
        "risk": risk,
        "recipe": "package-only-pr-gate-demo",
        "prompt": "demo_fixture",
        "execution_host": "other",
        "policy_pack_selection_mode": "demo_fixture",
        "created_at": DEMO_TIMESTAMP,
        "demo_fixture": True,
        "demo_notice": DEMO_NOTICE,
        "summary": summary,
    }


def _validation_report(
    *,
    run_id: str,
    profile: str,
    policy_pack: str,
    overall_status: str,
    sign_off_ready: bool,
    confidence: float,
    summary: dict[str, int],
    commands_run: list[dict[str, Any]],
    artifact_checks: list[dict[str, Any]],
    review_checks: list[dict[str, Any]],
    missing_context_notes: dict[str, list[str]],
    reason_codes: list[str],
    reason_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "run_id": run_id,
        "project": "ai_workbench_demo_fixture",
        "profile": profile,
        "generated_at": DEMO_TIMESTAMP,
        "demo_fixture": True,
        "demo_notice": DEMO_NOTICE,
        "commands_run": commands_run,
        "commands_not_run": [],
        "artifact_checks": artifact_checks,
        "review_checks": review_checks,
        "missing_context_notes": missing_context_notes,
        "overall_status": overall_status,
        "sign_off_ready": sign_off_ready,
        "confidence": confidence,
        "summary": summary,
        "policy_pack": {
            "name": policy_pack,
            "version": "demo",
        },
        "reason_codes": reason_codes,
        "reason_sources": reason_sources,
    }


def _revision_decision(
    *,
    final_status: str,
    reason: str,
    next_action: str,
    loop_type: str,
    required: bool,
    accepted_pass: int,
    blocking_findings: list[str],
    non_blocking_findings: list[str],
    reason_codes: list[str],
    reason_sources: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "generated_at": DEMO_TIMESTAMP,
        "demo_fixture": True,
        "demo_notice": DEMO_NOTICE,
        "loop_type": loop_type,
        "required": required,
        "reason": reason,
        "next_action": next_action,
        "accepted_pass": accepted_pass,
        "final_status": final_status,
        "authoritative_model_output": "model_output.md",
        "authoritative_validation_report": "validation_report.json",
        "blocking_findings": blocking_findings,
        "non_blocking_findings": non_blocking_findings,
        "reason_codes": reason_codes,
        "reason_sources": reason_sources,
    }


def _demo_command(status: str) -> dict[str, Any]:
    return {
        "name": "package_only_demo_fixture",
        "command": "demo fixture: no external command executed",
        "cwd": ".",
        "required": True,
        "weight": 1.0,
        "exit_code": 0,
        "status": status,
        "duration_ms": 0,
        "demo_fixture": True,
    }


def _artifact_presence_check() -> dict[str, Any]:
    return {
        "name": "artifact_presence",
        "status": "passed",
        "summary": "Required Workbench evidence artifacts are present in the demo fixture.",
        "details": [
            "Found validation_report.json.",
            "Found revision_decision.json.",
            "Found model_output.md.",
            "Found run_log.jsonl.",
        ],
        "reason_codes": ["artifact_presence.passed"],
        "demo_fixture": True,
    }


def _model_output(*, title: str, bullets: list[str]) -> str:
    lines = [
        "# Synthetic Demo Captured Output",
        "",
        f"Scenario: {title}",
        "",
        DEMO_NOTICE,
        "",
        "Summary:",
    ]
    lines.extend(f"- {bullet}" for bullet in bullets)
    lines.extend(
        [
            "",
            "This file intentionally contains no provider transcript, token log, private path, or target-repo claim.",
            "",
        ]
    )
    return "\n".join(lines)


def demo_scenarios() -> tuple[DemoScenario, ...]:
    accepted_run_id = "package-demo-accepted"
    needs_review_run_id = "package-demo-needs-review"
    blocked_run_id = "package-demo-blocked"

    accepted_reason = "Validation passed and the quality gate accepted the package-only demo fixture."
    needs_review_reason = "Policy requires contract-owner review before merge."
    blocked_reason = "Source file changed in docs-only policy."

    return (
        DemoScenario(
            folder="accepted",
            expected_outcome="accept",
            run_id=accepted_run_id,
            validation_report=_validation_report(
                run_id=accepted_run_id,
                profile="docs_only",
                policy_pack="docs_only",
                overall_status="passed",
                sign_off_ready=True,
                confidence=1.0,
                commands_run=[_demo_command("passed")],
                artifact_checks=[
                    _artifact_presence_check(),
                    {
                        "name": "changed_file_policy",
                        "status": "passed",
                        "summary": "Demo fixture changed files fit the docs-only policy surface.",
                        "details": ["Only sanitized documentation-style fixture evidence is represented."],
                        "reason_codes": ["docs_only.changed_files_allowed"],
                        "demo_fixture": True,
                    },
                ],
                review_checks=[],
                missing_context_notes={"needs_review": [], "info": [DEMO_NOTICE]},
                reason_codes=["docs_only.accepted", "demo.fixture"],
                reason_sources=[
                    _reason_source(
                        code="docs_only.accepted",
                        status="passed",
                        severity="info",
                        source="validation_report",
                        name="docs_only",
                        summary="Docs-only demo fixture validation passed.",
                        details=["This is synthetic package-only evidence for renderer onboarding."],
                    )
                ],
                summary={
                    "commands_passed": 1,
                    "commands_failed": 0,
                    "checks_passed": 2,
                    "checks_needs_review": 0,
                    "checks_failed": 0,
                },
            ),
            revision_decision=_revision_decision(
                final_status="accepted",
                reason=accepted_reason,
                next_action="No Workbench action required for this demo fixture.",
                loop_type="none",
                required=False,
                accepted_pass=1,
                blocking_findings=[],
                non_blocking_findings=[DEMO_NOTICE],
                reason_codes=["quality_gate.accepted", "demo.fixture"],
                reason_sources=[
                    _reason_source(
                        code="quality_gate.accepted",
                        status="accepted",
                        severity="info",
                        source="revision_decision",
                        name="quality_gate",
                        summary=accepted_reason,
                        details=["No demo quality-loop triggers were detected."],
                    )
                ],
            ),
            task_metadata=_base_task_metadata(
                run_id=accepted_run_id,
                task_type="docs_only",
                risk="low",
                summary="Synthetic accepted PR gate demo fixture.",
            ),
            model_output=_model_output(
                title="accepted",
                bullets=[
                    "Represents an accepted PR gate outcome.",
                    "Uses passed validation and accepted quality-gate metadata.",
                ],
            ),
        ),
        DemoScenario(
            folder="needs-review",
            expected_outcome="needs_review",
            run_id=needs_review_run_id,
            validation_report=_validation_report(
                run_id=needs_review_run_id,
                profile="api_contract_change",
                policy_pack="api_contract_change",
                overall_status="needs_review",
                sign_off_ready=False,
                confidence=0.7,
                commands_run=[_demo_command("passed")],
                artifact_checks=[_artifact_presence_check()],
                review_checks=[
                    {
                        "name": "contract_owner_approval",
                        "status": "needs_review",
                        "summary": "API contract changes require maintainer review before merge.",
                        "details": [
                            "The deterministic demo check passed.",
                            "Policy still requires a human contract-owner review.",
                        ],
                        "reason_codes": ["api_contract_change.review_required"],
                        "demo_fixture": True,
                    }
                ],
                missing_context_notes={
                    "needs_review": ["Record contract-owner approval before treating this PR as accepted."],
                    "info": [DEMO_NOTICE],
                },
                reason_codes=["api_contract_change.review_required", "demo.fixture"],
                reason_sources=[
                    _reason_source(
                        code="api_contract_change.review_required",
                        status="needs_review",
                        severity="review",
                        source="validation_report",
                        name="contract_owner_approval",
                        summary="API contract changes require maintainer review before merge.",
                        details=["No blocker-severity finding was recorded."],
                    )
                ],
                summary={
                    "commands_passed": 1,
                    "commands_failed": 0,
                    "checks_passed": 1,
                    "checks_needs_review": 1,
                    "checks_failed": 0,
                },
            ),
            revision_decision=_revision_decision(
                final_status="review_required",
                reason=needs_review_reason,
                next_action="Record contract-owner approval, then regenerate the PR gate artifact.",
                loop_type="human_review",
                required=True,
                accepted_pass=0,
                blocking_findings=[],
                non_blocking_findings=["Contract-owner review is required by policy."],
                reason_codes=["quality_gate.review_required", "demo.fixture"],
                reason_sources=[
                    _reason_source(
                        code="quality_gate.review_required",
                        status="review_required",
                        severity="review",
                        source="revision_decision",
                        name="quality_gate",
                        summary=needs_review_reason,
                        details=["Manual approval has not been recorded in the demo fixture."],
                    )
                ],
            ),
            task_metadata=_base_task_metadata(
                run_id=needs_review_run_id,
                task_type="api_contract_change",
                risk="medium",
                summary="Synthetic needs-review PR gate demo fixture.",
            ),
            model_output=_model_output(
                title="needs_review",
                bullets=[
                    "Represents a PR gate outcome that requires human review.",
                    "Uses needs_review validation and review_required quality-gate metadata.",
                ],
            ),
        ),
        DemoScenario(
            folder="blocked",
            expected_outcome="block",
            run_id=blocked_run_id,
            validation_report=_validation_report(
                run_id=blocked_run_id,
                profile="docs_only",
                policy_pack="docs_only",
                overall_status="needs_review",
                sign_off_ready=False,
                confidence=0.2,
                commands_run=[_demo_command("passed")],
                artifact_checks=[
                    {
                        "name": "changed_file_policy",
                        "status": "failed",
                        "summary": blocked_reason,
                        "details": [
                            "The selected demo policy profile is docs_only.",
                            "The changed-file evidence includes a source-code file.",
                        ],
                        "reason_codes": ["docs_only.source_file_blocked"],
                        "demo_fixture": True,
                    }
                ],
                review_checks=[],
                missing_context_notes={
                    "needs_review": ["Use an implementation profile for source-code changes or remove the source edit."],
                    "info": [DEMO_NOTICE],
                },
                reason_codes=["docs_only.source_file_blocked", "demo.fixture"],
                reason_sources=[
                    _reason_source(
                        code="docs_only.source_file_blocked",
                        status="failed",
                        severity="blocker",
                        source="validation_report",
                        name="changed_file_policy",
                        summary=blocked_reason,
                        details=["Blocker-severity evidence prevents a needs-review PR gate outcome."],
                    )
                ],
                summary={
                    "commands_passed": 1,
                    "commands_failed": 0,
                    "checks_passed": 0,
                    "checks_needs_review": 0,
                    "checks_failed": 1,
                },
            ),
            revision_decision=_revision_decision(
                final_status="review_required",
                reason="Docs-only policy was violated by source-code changes.",
                next_action=(
                    "Move source-code edits to an implementation profile or remove them, rerun validation, "
                    "and regenerate the PR gate artifact."
                ),
                loop_type="policy_blocker",
                required=True,
                accepted_pass=0,
                blocking_findings=[blocked_reason],
                non_blocking_findings=[],
                reason_codes=["quality_gate.blocker_present", "demo.fixture"],
                reason_sources=[
                    _reason_source(
                        code="quality_gate.blocker_present",
                        status="review_required",
                        severity="blocker",
                        source="revision_decision",
                        name="quality_gate",
                        summary=blocked_reason,
                        details=["Blocker-severity evidence prevents merge acceptance."],
                    )
                ],
            ),
            task_metadata=_base_task_metadata(
                run_id=blocked_run_id,
                task_type="docs_only",
                risk="low",
                summary="Synthetic blocked PR gate demo fixture.",
            ),
            model_output=_model_output(
                title="block",
                bullets=[
                    "Represents a PR gate outcome that blocks merge acceptance.",
                    "Uses blocker-severity evidence with review_required quality-gate metadata.",
                ],
            ),
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create package-only AI Workbench PR gate demo evidence."
    )
    parser.add_argument(
        "--target",
        default=".",
        help="Directory that should receive ai-workbench-demo/. Defaults to the current directory.",
    )
    return parser


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_events(path: Path, scenario: DemoScenario) -> None:
    events = [
        {
            "schema_version": 1,
            "run_id": scenario.run_id,
            "event": "demo_fixture_created",
            "response_source": "package_demo_fixture",
            "created_at": DEMO_TIMESTAMP,
        },
        {
            "schema_version": 1,
            "run_id": scenario.run_id,
            "event": "validation_completed",
            "status": scenario.validation_report["overall_status"],
            "created_at": DEMO_TIMESTAMP,
        },
        {
            "schema_version": 1,
            "run_id": scenario.run_id,
            "event": "quality_gate_completed",
            "final_status": scenario.revision_decision["final_status"],
            "created_at": DEMO_TIMESTAMP,
        },
    ]
    lines = [json.dumps(event, sort_keys=True) for event in events]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _public_source_dir(folder: str) -> str:
    return f"{DEMO_ROOT_NAME}/{folder}/evidence"


def _ensure_directory(path: Path, *, label: str) -> None:
    if path.exists() and not path.is_dir():
        raise NotADirectoryError(f"{label} exists and is not a directory: {path}")
    path.mkdir(parents=True, exist_ok=True)


def generate_demo(target_dir: str | Path = ".") -> list[DemoResult]:
    target_root = Path(target_dir).expanduser().resolve()
    _ensure_directory(target_root, label="target")
    demo_root = target_root / DEMO_ROOT_NAME
    _ensure_directory(demo_root, label="demo root")

    results: list[DemoResult] = []
    for scenario in demo_scenarios():
        scenario_dir = demo_root / scenario.folder
        evidence_dir = scenario_dir / "evidence"
        _ensure_directory(scenario_dir, label=f"{scenario.folder} scenario")
        _ensure_directory(evidence_dir, label=f"{scenario.folder} evidence")

        write_json(evidence_dir / "task_metadata.json", scenario.task_metadata)
        write_json(evidence_dir / "validation_report.json", scenario.validation_report)
        write_json(evidence_dir / "revision_decision.json", scenario.revision_decision)
        (evidence_dir / "model_output.md").write_text(scenario.model_output, encoding="utf-8")
        write_events(evidence_dir / "run_log.jsonl", scenario)

        decision = decision_from_evidence(
            evidence_dir,
            evidence_source="acceptance_run",
            source_run_dir=_public_source_dir(scenario.folder),
        )
        outcome = str(decision["outcome"])
        if outcome != scenario.expected_outcome:
            raise RuntimeError(
                f"Demo scenario {scenario.folder} rendered {outcome}, "
                f"expected {scenario.expected_outcome}."
            )
        comment_path = scenario_dir / "pr_comment.md"
        decision_path = scenario_dir / "pr_decision.json"
        write_outputs(decision, comment_path, decision_path)

        results.append(
            DemoResult(
                root_dir=demo_root,
                scenario=scenario.folder,
                outcome=outcome,
                evidence_dir=evidence_dir,
                comment_path=comment_path,
                decision_path=decision_path,
            )
        )
    return results


def print_summary(results: Sequence[DemoResult]) -> None:
    if not results:
        return
    print(f"ai_workbench_demo_root={results[0].root_dir}")
    for result in results:
        print(f"scenario={result.scenario} outcome={result.outcome}")
        print(f"evidence_dir={result.evidence_dir}")
        print(f"pr_gate_comment={result.comment_path}")
        print(f"pr_gate_decision={result.decision_path}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        results = generate_demo(args.target)
    except OSError as exc:
        parser.error(str(exc))
    print_summary(results)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
