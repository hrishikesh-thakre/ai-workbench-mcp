from __future__ import annotations

from collections import Counter

from .run_cost_time import as_dict
from .run_evidence import final_prompt_name


def final_status(report: dict[str, object], decision: dict[str, object]) -> str:
    quality_status = str(decision.get("final_status", ""))
    if quality_status in {"review_required", "revision_required"}:
        return "needs_review"
    report_status = str(report.get("overall_status", "unknown"))
    if report_status in {"passed", "failed", "needs_review"}:
        return report_status
    return "unknown"


def recipe_for(
    metadata: dict[str, object],
    selection: dict[str, object],
    report: dict[str, object],
    logs: list[dict[str, object]],
) -> str:
    for candidate in (
        metadata.get("recipe"),
        selection.get("recipe"),
        report.get("recipe"),
    ):
        if candidate:
            return str(candidate)
    for row in reversed(logs):
        recipe = row.get("recipe")
        if recipe:
            return str(recipe)

    profile = str(report.get("profile", ""))
    profile_to_recipe = {
        "docs_only": "workbench-docs-only-acceptance.yaml",
        "python_package_maintenance": "workbench-python-package-maintenance.yaml",
        "test_fix": "workbench-test-fix-acceptance.yaml",
        "fixture_repair_proof": "workbench-test-fix-acceptance.yaml",
        "low_risk_coding": "workbench-engineering-acceptance.yaml",
        "run_signoff": "workbench-engineering-acceptance.yaml",
        "tiny_python_fix": "workbench-engineering-acceptance.yaml",
    }
    if profile in profile_to_recipe:
        return profile_to_recipe[profile]

    prompt = final_prompt_name(selection, logs)
    prompt_to_recipe = {
        "documentation_accuracy_audit": "workbench-docs-only-acceptance.yaml",
        "bug_root_cause_investigation": "workbench-test-fix-acceptance.yaml",
    }
    return prompt_to_recipe.get(prompt, "unknown")


def quality_gate_outcome(decision: dict[str, object]) -> str:
    outcome = str(decision.get("final_status", "")).strip()
    return outcome or "missing_decision"


def accepted_by_validation_and_gate(report: dict[str, object], decision: dict[str, object]) -> bool:
    return (
        quality_gate_outcome(decision) == "accepted"
        and report.get("overall_status") == "passed"
        and report.get("sign_off_ready") is True
    )


def acceptance_bucket(report: dict[str, object], decision: dict[str, object]) -> str:
    if accepted_by_validation_and_gate(report, decision):
        return "accepted"
    outcome = quality_gate_outcome(decision)
    if outcome in {"review_required", "revision_required"}:
        return "needs_review"
    if report.get("overall_status") == "failed":
        return "failed"
    return outcome


def public_outcome_bucket(report: dict[str, object], decision: dict[str, object]) -> str:
    if accepted_by_validation_and_gate(report, decision):
        return "accepted"
    outcome = quality_gate_outcome(decision)
    if outcome in {"review_required", "revision_required"}:
        return "review_required"
    if report.get("overall_status") == "failed":
        return "failed"
    return "other"


def acceptance_breakdown(matrix: dict[str, Counter[str]]) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for key, counts in sorted(matrix.items()):
        total = sum(counts.values())
        accepted = counts.get("accepted", 0)
        result[key] = {
            "accepted": accepted,
            "needs_review": counts.get("needs_review", 0),
            "failed": counts.get("failed", 0),
            "other": total - accepted - counts.get("needs_review", 0) - counts.get("failed", 0),
            "total": total,
            "acceptance_rate": round(accepted / max(1, total), 2),
        }
    return result


def outcome_breakdown(matrix: dict[str, Counter[str]]) -> dict[str, dict[str, object]]:
    result: dict[str, dict[str, object]] = {}
    for key, counts in sorted(matrix.items()):
        total = sum(counts.values())
        accepted = counts.get("accepted", 0)
        review_required = counts.get("review_required", 0)
        failed = counts.get("failed", 0)
        result[key] = {
            "accepted": accepted,
            "review_required": review_required,
            "failed": failed,
            "other": total - accepted - review_required - failed,
            "total": total,
            "acceptance_rate": round(accepted / max(1, total), 2),
            "review_rate": round(review_required / max(1, total), 2),
            "failure_rate": round(failed / max(1, total), 2),
        }
    return result


def routing_feedback_candidates(
    outcome_matrix: dict[str, Counter[str]],
    failure_reason_matrix: dict[str, Counter[str]],
) -> dict[str, dict[str, object]]:
    candidates: dict[str, dict[str, object]] = {}
    for key, counts in sorted(outcome_matrix.items()):
        parts = str(key).split("|")
        recipe, profile, tier, risk, complexity = (parts + ["unknown"] * 5)[:5]
        total = sum(counts.values())
        accepted = counts.get("accepted", 0)
        review_required = counts.get("review_required", 0)
        failed = counts.get("failed", 0)
        candidates[key] = {
            "recipe": recipe,
            "validation_profile": profile,
            "selected_tier": tier,
            "risk": risk,
            "complexity_band": complexity,
            "accepted": accepted,
            "review_required": review_required,
            "failed": failed,
            "other": total - accepted - review_required - failed,
            "total": total,
            "acceptance_rate": round(accepted / max(1, total), 2),
            "review_rate": round(review_required / max(1, total), 2),
            "failure_rate": round(failed / max(1, total), 2),
            "top_failure_reasons": dict(failure_reason_matrix.get(key, Counter()).most_common(5)),
        }
    return candidates


def failure_reasons(report: dict[str, object], decision: dict[str, object]) -> list[str]:
    reasons: list[str] = []
    for reason_code in report.get("reason_codes", []) if isinstance(report.get("reason_codes", []), list) else []:
        if reason_code:
            reasons.append(str(reason_code))
    for reason_code in decision.get("reason_codes", []) if isinstance(decision.get("reason_codes", []), list) else []:
        if reason_code:
            reasons.append(str(reason_code))
    if report.get("overall_status") not in {"passed", None, ""}:
        reasons.append(f"validation_overall:{report.get('overall_status')}")
    if report and report.get("sign_off_ready") is False:
        reasons.append("validation_not_sign_off_ready")

    for command in report.get("commands_run", []) if isinstance(report.get("commands_run", []), list) else []:
        command = as_dict(command)
        status = str(command.get("status", ""))
        exit_code = command.get("exit_code")
        if status == "failed" or exit_code not in {None, 0}:
            reasons.append(f"command_failed:{command.get('name', 'unknown')}")

    for command in report.get("commands_not_run", []) if isinstance(report.get("commands_not_run", []), list) else []:
        command = as_dict(command)
        reasons.append(f"command_not_run:{command.get('name', 'unknown')}")

    for section in ("artifact_checks", "review_checks"):
        for check in report.get(section, []) if isinstance(report.get(section, []), list) else []:
            check = as_dict(check)
            status = str(check.get("status", ""))
            if status in {"failed", "needs_review"}:
                reasons.append(f"{section}:{status}:{check.get('name', 'unknown')}")

    notes = report.get("missing_context_notes", {})
    if isinstance(notes, dict):
        for note in notes.get("needs_review", []) if isinstance(notes.get("needs_review", []), list) else []:
            reasons.append(f"missing_context:{note}")

    outcome = quality_gate_outcome(decision)
    if outcome not in {"accepted", "missing_decision"}:
        reasons.append(f"quality_gate:{outcome}")
    loop_type = str(decision.get("loop_type", "none"))
    if loop_type and loop_type != "none":
        reasons.append(f"quality_loop:{loop_type}")
    if outcome == "missing_decision":
        reasons.append("quality_gate:missing_decision")

    unique_reasons: list[str] = []
    seen: set[str] = set()
    for reason in reasons:
        if reason in seen:
            continue
        seen.add(reason)
        unique_reasons.append(reason)
    return unique_reasons or ["unknown"]

