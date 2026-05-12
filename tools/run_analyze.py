from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path

from config_loader import load_simple_yaml


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze local runs folders for Phase 2 metrics.")
    parser.add_argument("--runs-dir", default="runs", help="Directory containing run folders.")
    parser.add_argument("--task-type", help="Optional task type filter.")
    parser.add_argument("--since", help="Optional ISO timestamp/date lower bound.")
    parser.add_argument("--out-dir", help="Report directory. Defaults to <runs-dir>/_reports.")
    parser.add_argument("--evals-dir", default="evals/golden_cases", help="Directory containing golden cases.")
    return parser


def read_json(file_path: Path) -> dict[str, object]:
    if not file_path.exists():
        return {}
    try:
        payload = json.loads(file_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def read_jsonl(file_path: Path) -> list[dict[str, object]]:
    if not file_path.exists():
        return []
    rows: list[dict[str, object]] = []
    for line in file_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def as_float(value: object) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    return None


def as_dict(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def first_non_none(*values: object) -> object | None:
    for value in values:
        if value is not None:
            return value
    return None


def load_runtime_config() -> dict[str, object]:
    config_path = Path(__file__).resolve().parent.parent / "configs" / "litellm.yaml"
    if not config_path.exists():
        return {}
    return load_simple_yaml(config_path)


def run_created_at(logs: list[dict[str, object]]) -> str:
    if not logs:
        return ""
    return str(logs[0].get("timestamp", ""))


def task_type_for(run_dir: Path, logs: list[dict[str, object]]) -> str:
    selection = read_json(run_dir / "model_selection.json")
    task_type = selection.get("task_type") or selection.get("workflow_mode")
    if task_type:
        return str(task_type)
    for row in reversed(logs):
        prompt = row.get("prompt")
        if prompt:
            return str(prompt)
    return "unknown"


def final_status(report: dict[str, object], decision: dict[str, object]) -> str:
    quality_status = str(decision.get("final_status", ""))
    if quality_status in {"review_required", "revision_required"}:
        return "needs_review"
    report_status = str(report.get("overall_status", "unknown"))
    if report_status in {"passed", "failed", "needs_review"}:
        return report_status
    return "unknown"


def eligible_for_golden_case(run_dir: Path) -> bool:
    required = ["expert_packet.md", "final_prompt.md", "model_output.md", "validation_report.json"]
    return all((run_dir / artifact).exists() for artifact in required)


def selection_for(run_dir: Path) -> dict[str, object]:
    return read_json(run_dir / "model_selection.json")


def model_pricing(runtime: dict[str, object], model: str) -> dict[str, object]:
    providers = as_dict(runtime.get("providers"))
    litellm = as_dict(providers.get("litellm"))
    pricing = as_dict(litellm.get("model_pricing_usd_per_1m"))
    return as_dict(pricing.get(model))


def latest_tier(logs: list[dict[str, object]], selection: dict[str, object]) -> str:
    tier = str(selection.get("selected_tier", ""))
    if tier:
        return tier
    for row in reversed(logs):
        row_tier = row.get("model_tier")
        if row_tier and str(row_tier) != "not_selected":
            return str(row_tier)
    return "unknown"


def final_prompt_name(selection: dict[str, object], logs: list[dict[str, object]]) -> str:
    prompt = selection.get("prompt")
    if prompt:
        return str(prompt)
    for row in reversed(logs):
        row_prompt = row.get("prompt")
        if row_prompt:
            return str(row_prompt)
    return "unknown"


def task_metadata_for(run_dir: Path) -> dict[str, object]:
    return read_json(run_dir / "task_metadata.json")


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

    return reasons or ["unknown"]


def scan_eval_results(runs_dir: Path) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    reports_dir = runs_dir / "_reports"
    for result_path in runs_dir.rglob("eval_result*.json"):
        if reports_dir in result_path.parents:
            continue
        payload = read_json(result_path)
        if payload:
            payload["_path"] = str(result_path)
            payload["_run_id"] = result_path.parent.name
            payload["_run_dir"] = str(result_path.parent)
            results.append(payload)
    return results


def scan_model_eval_results(runs_dir: Path) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for metadata_path in runs_dir.glob("*/model_eval_metadata.json"):
        metadata = read_json(metadata_path)
        score = read_json(metadata_path.parent / "score_report.json")
        if not metadata and not score:
            continue
        combined = {
            **metadata,
            "score_report": score,
            "_path": str(metadata_path),
            "_run_id": metadata_path.parent.name,
        }
        results.append(combined)
    return results


def scan_model_eval_matrices(runs_dir: Path) -> list[dict[str, object]]:
    reports_dir = runs_dir / "_reports"
    if not reports_dir.exists():
        return []
    matrices: list[dict[str, object]] = []
    for report_path in reports_dir.glob("model_eval_matrix*.json"):
        payload = read_json(report_path)
        if payload:
            payload["_path"] = str(report_path)
            matrices.append(payload)
    return matrices


def scan_prompt_normalizer_evals(runs_dir: Path) -> list[dict[str, object]]:
    reports_dir = runs_dir / "_reports"
    if not reports_dir.exists():
        return []
    reports: list[dict[str, object]] = []
    for report_path in reports_dir.glob("prompt_normalizer_eval*.json"):
        payload = read_json(report_path)
        if payload:
            payload["_path"] = str(report_path)
            reports.append(payload)
    return reports


def golden_case_count(evals_dir: Path) -> int:
    if not evals_dir.exists():
        return 0
    return len([path for path in evals_dir.glob("*.json") if path.is_file()])


def scan_model_call_metadata(runs_dir: Path) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    reports_dir = runs_dir / "_reports"
    for metadata_path in runs_dir.rglob("model_call_metadata.json"):
        if reports_dir in metadata_path.parents:
            continue
        payload = read_json(metadata_path)
        if payload:
            payload["_path"] = str(metadata_path)
            payload["_run_id"] = metadata_path.parent.name
            results.append(payload)
    return results


def usage_summary_from_metadata(metadata: dict[str, object]) -> dict[str, object]:
    existing = as_dict(metadata.get("usage_summary"))
    if existing:
        return existing

    attempts = metadata.get("attempts", [])
    for attempt in reversed(attempts) if isinstance(attempts, list) else []:
        attempt_dict = as_dict(attempt)
        if attempt_dict.get("status") != "completed":
            continue
        usage = as_dict(attempt_dict.get("usage"))
        if not usage:
            continue
        prompt_tokens = as_int(usage.get("prompt_tokens"))
        completion_tokens = as_int(usage.get("completion_tokens"))
        total_tokens = as_int(usage.get("total_tokens"))
        cached_input_tokens = as_int(
            first_non_none(
                as_int(usage.get("prompt_cache_hit_tokens")),
                as_int(usage.get("cache_read_input_tokens")),
                as_int(usage.get("cached_tokens")),
            )
        )
        if cached_input_tokens is not None and prompt_tokens is not None:
            cached_input_tokens = max(0, min(cached_input_tokens, prompt_tokens))
        uncached_input_tokens = (
            prompt_tokens - cached_input_tokens
            if prompt_tokens is not None and cached_input_tokens is not None
            else prompt_tokens
        )
        summary: dict[str, object] = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }
        if cached_input_tokens is not None:
            summary["cached_input_tokens"] = cached_input_tokens
        if uncached_input_tokens is not None:
            summary["uncached_input_tokens"] = uncached_input_tokens
        return summary
    return {}


def successful_attempt_model(metadata: dict[str, object]) -> str:
    attempts = metadata.get("attempts", [])
    for attempt in reversed(attempts) if isinstance(attempts, list) else []:
        attempt_dict = as_dict(attempt)
        if attempt_dict.get("status") == "completed" and attempt_dict.get("model"):
            return str(attempt_dict.get("model"))
    return str(metadata.get("model", ""))


def estimate_cost_from_metadata(metadata: dict[str, object], runtime: dict[str, object]) -> tuple[float | None, str | None]:
    direct_cost = as_float(metadata.get("estimated_cost_usd"))
    direct_source = metadata.get("pricing_source")
    if direct_cost is not None:
        return direct_cost, str(direct_source) if direct_source else None

    usage_summary = usage_summary_from_metadata(metadata)
    if not usage_summary:
        return None, None

    model = successful_attempt_model(metadata)
    pricing = model_pricing(runtime, model)
    input_rate = as_float(pricing.get("input_tokens"))
    cached_input_rate = as_float(pricing.get("cached_input_tokens"))
    output_rate = as_float(pricing.get("output_tokens"))
    if input_rate is None or cached_input_rate is None or output_rate is None:
        return None, None

    prompt_tokens = as_int(usage_summary.get("prompt_tokens"))
    completion_tokens = as_int(usage_summary.get("completion_tokens"))
    cached_input_tokens = as_int(usage_summary.get("cached_input_tokens")) or 0
    uncached_input_tokens = as_int(usage_summary.get("uncached_input_tokens"))
    if uncached_input_tokens is None and prompt_tokens is not None:
        uncached_input_tokens = max(0, prompt_tokens - cached_input_tokens)
    if uncached_input_tokens is None and completion_tokens is None:
        return None, None

    estimated_cost_usd = (
        ((uncached_input_tokens or 0) * input_rate)
        + (cached_input_tokens * cached_input_rate)
        + ((completion_tokens or 0) * output_rate)
    ) / 1_000_000
    return round(estimated_cost_usd, 8), str(pricing.get("source")) if pricing.get("source") else None


def run_analysis_payload(args: argparse.Namespace) -> dict[str, object]:
    runs_dir = Path(args.runs_dir)
    if not runs_dir.exists():
        raise FileNotFoundError(f"runs_dir_missing={runs_dir}")

    out_dir = Path(args.out_dir) if args.out_dir else runs_dir / "_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    runtime = load_runtime_config()

    runs: list[dict[str, object]] = []
    for run_dir in sorted(path for path in runs_dir.iterdir() if path.is_dir() and not path.name.startswith("_")):
        logs = read_jsonl(run_dir / "run_log.jsonl")
        if not logs:
            continue
        created_at = run_created_at(logs)
        if args.since and created_at and created_at < args.since:
            continue
        task_type = task_type_for(run_dir, logs)
        if args.task_type and task_type != args.task_type:
            continue
        report = read_json(run_dir / "validation_report.json")
        decision = read_json(run_dir / "revision_decision.json")
        selection = selection_for(run_dir)
        metadata = task_metadata_for(run_dir)
        runs.append(
            {
                "run_id": run_dir.name,
                "path": str(run_dir),
                "logs": logs,
                "report": report,
                "decision": decision,
                "selection": selection,
                "metadata": metadata,
                "task_type": task_type,
                "status": final_status(report, decision),
                "eligible_for_golden_case": eligible_for_golden_case(run_dir),
            }
        )

    status_counts = Counter(str(run["status"]) for run in runs)
    tier_usage: Counter[str] = Counter()
    profiles_used: Counter[str] = Counter()
    review_triggers: Counter[str] = Counter()
    missing_info: Counter[str] = Counter()
    missing_needs_review: Counter[str] = Counter()
    tier_by_risk: dict[str, Counter[str]] = defaultdict(Counter)
    tier_by_complexity_band: dict[str, Counter[str]] = defaultdict(Counter)
    status_by_tier: dict[str, Counter[str]] = defaultdict(Counter)
    review_trigger_by_tier: dict[str, Counter[str]] = defaultdict(Counter)
    prompt_by_tier: dict[str, Counter[str]] = defaultdict(Counter)
    confidence_by_task: dict[str, list[float]] = defaultdict(list)
    confidences: list[float] = []
    manual_handoff_count = 0
    response_captured_count = 0
    routing_feedback: dict[str, Counter[str]] = defaultdict(Counter)
    accepted_runs_total = 0
    accepted_by_recipe: Counter[str] = Counter()
    accepted_by_profile: Counter[str] = Counter()
    accepted_by_tier: Counter[str] = Counter()
    accepted_by_task_type: Counter[str] = Counter()
    public_outcomes: Counter[str] = Counter()
    quality_outcomes: Counter[str] = Counter()
    failure_reason_counts: Counter[str] = Counter()
    acceptance_by_recipe: dict[str, Counter[str]] = defaultdict(Counter)
    acceptance_by_profile: dict[str, Counter[str]] = defaultdict(Counter)
    acceptance_by_tier: dict[str, Counter[str]] = defaultdict(Counter)
    acceptance_by_quality_outcome: dict[str, Counter[str]] = defaultdict(Counter)
    outcome_by_recipe: dict[str, Counter[str]] = defaultdict(Counter)
    outcome_by_profile: dict[str, Counter[str]] = defaultdict(Counter)
    outcome_by_tier: dict[str, Counter[str]] = defaultdict(Counter)
    outcome_by_quality_outcome: dict[str, Counter[str]] = defaultdict(Counter)
    routing_candidate_outcomes: dict[str, Counter[str]] = defaultdict(Counter)
    routing_candidate_failure_reasons: dict[str, Counter[str]] = defaultdict(Counter)

    for run in runs:
        logs = run["logs"]
        report = run["report"]
        decision = run["decision"]
        selection = run["selection"]
        metadata = run["metadata"]
        task_type = str(run["task_type"])
        selected_tier = latest_tier(logs if isinstance(logs, list) else [], selection if isinstance(selection, dict) else {})
        run_status = str(run["status"])
        profile = str(report.get("profile", "unknown")) if isinstance(report, dict) else "unknown"
        recipe = recipe_for(
            metadata if isinstance(metadata, dict) else {},
            selection if isinstance(selection, dict) else {},
            report if isinstance(report, dict) else {},
            logs if isinstance(logs, list) else [],
        )
        gate_outcome = quality_gate_outcome(decision if isinstance(decision, dict) else {})
        accepted = accepted_by_validation_and_gate(
            report if isinstance(report, dict) else {},
            decision if isinstance(decision, dict) else {},
        )
        bucket = acceptance_bucket(report if isinstance(report, dict) else {}, decision if isinstance(decision, dict) else {})
        public_bucket = public_outcome_bucket(
            report if isinstance(report, dict) else {},
            decision if isinstance(decision, dict) else {},
        )
        risk = str(selection.get("risk", "unknown")) if isinstance(selection, dict) else "unknown"
        complexity_band = str(selection.get("complexity_band", "unknown")) if isinstance(selection, dict) else "unknown"
        # Backfill: when historical runs lack complexity scoring, use risk as a proxy.
        if complexity_band in {"unknown", "None", "none", "null"}:
            complexity_band = {"low": "easy", "medium": "moderate", "high": "hard"}.get(risk, "unknown")
        prompt_name = final_prompt_name(selection if isinstance(selection, dict) else {}, logs if isinstance(logs, list) else [])
        tier_by_risk[risk][selected_tier] += 1
        tier_by_complexity_band[complexity_band][selected_tier] += 1
        status_by_tier[selected_tier][run_status] += 1
        prompt_by_tier[selected_tier][prompt_name] += 1
        routing_key = f"{selected_tier}|{risk}|{complexity_band}"
        routing_feedback[routing_key][run_status] += 1
        quality_outcomes[gate_outcome] += 1
        public_outcomes[public_bucket] += 1
        acceptance_by_recipe[recipe][bucket] += 1
        acceptance_by_profile[profile][bucket] += 1
        acceptance_by_tier[selected_tier][bucket] += 1
        acceptance_by_quality_outcome[gate_outcome][bucket] += 1
        outcome_by_recipe[recipe][public_bucket] += 1
        outcome_by_profile[profile][public_bucket] += 1
        outcome_by_tier[selected_tier][public_bucket] += 1
        outcome_by_quality_outcome[gate_outcome][public_bucket] += 1
        routing_candidate_key = f"{recipe}|{profile}|{selected_tier}|{risk}|{complexity_band}"
        routing_candidate_outcomes[routing_candidate_key][public_bucket] += 1
        if accepted:
            accepted_runs_total += 1
            accepted_by_recipe[recipe] += 1
            accepted_by_profile[profile] += 1
            accepted_by_tier[selected_tier] += 1
            accepted_by_task_type[task_type] += 1
        else:
            for reason in failure_reasons(
                report if isinstance(report, dict) else {},
                decision if isinstance(decision, dict) else {},
            ):
                failure_reason_counts[reason] += 1
                routing_candidate_failure_reasons[routing_candidate_key][reason] += 1
        if isinstance(logs, list):
            for row in logs:
                tier = row.get("model_tier")
                if tier:
                    tier_usage[str(tier)] += 1
                if row.get("decision") == "model_handoff_required":
                    manual_handoff_count += 1
                if row.get("decision") == "model_response_captured":
                    response_captured_count += 1

        if isinstance(report, dict):
            profile = report.get("profile")
            if profile:
                profiles_used[str(profile)] += 1
            confidence = as_float(report.get("confidence"))
            if confidence is not None:
                confidences.append(confidence)
                confidence_by_task[task_type].append(confidence)

            notes = report.get("missing_context_notes", {})
            if isinstance(notes, dict):
                for note in notes.get("info", []) if isinstance(notes.get("info", []), list) else []:
                    missing_info[str(note)] += 1
                for note in notes.get("needs_review", []) if isinstance(notes.get("needs_review", []), list) else []:
                    missing_needs_review[str(note)] += 1

        if isinstance(decision, dict):
            loop_type = str(decision.get("loop_type", "none"))
            if loop_type and loop_type != "none":
                review_triggers[loop_type] += 1
                review_trigger_by_tier[selected_tier][loop_type] += 1

    confidence_by_task_result = {
        task_type: round(sum(values) / len(values), 2)
        for task_type, values in confidence_by_task.items()
        if values
    }
    average_confidence = round(sum(confidences) / len(confidences), 2) if confidences else 0.0
    eval_results = scan_eval_results(runs_dir)
    evals_by_tier: dict[str, Counter[str]] = defaultdict(Counter)
    bad_patterns_by_tier: dict[str, Counter[str]] = defaultdict(Counter)
    failures_by_prompt: Counter[str] = Counter()
    for result in eval_results:
        run_dir_text = str(result.get("_run_dir", ""))
        run_dir = Path(run_dir_text) if run_dir_text else runs_dir / str(result.get("_run_id", ""))
        selection = selection_for(run_dir)
        logs = read_jsonl(run_dir / "run_log.jsonl")
        tier = latest_tier(logs, selection)
        prompt = final_prompt_name(selection, logs)
        outcome = "passed" if result.get("overall_pass") is True else "failed"
        evals_by_tier[tier][outcome] += 1
        for pattern in result.get("bad_patterns_found", []) if isinstance(result.get("bad_patterns_found", []), list) else []:
            bad_patterns_by_tier[tier][str(pattern)] += 1
        if outcome == "failed":
            failures_by_prompt[prompt] += 1

    model_eval_results = scan_model_eval_results(runs_dir)
    model_eval_by_provider: Counter[str] = Counter()
    model_eval_by_model: Counter[str] = Counter()
    model_eval_by_case_type: Counter[str] = Counter()
    model_eval_by_difficulty: Counter[str] = Counter()
    model_eval_by_risk: Counter[str] = Counter()
    model_eval_outcomes_by_provider: dict[str, Counter[str]] = defaultdict(Counter)
    model_eval_outcomes_by_provider_model: dict[str, Counter[str]] = defaultdict(Counter)
    model_eval_scores_by_provider_model: dict[str, list[float]] = defaultdict(list)
    model_eval_status_by_provider: dict[str, Counter[str]] = defaultdict(Counter)
    model_eval_infra_failures_by_provider_model: Counter[str] = Counter()
    model_eval_failure_modes: Counter[str] = Counter()
    model_eval_case_outcomes: list[dict[str, object]] = []

    for result in model_eval_results:
        score_report = result.get("score_report", {})
        if not isinstance(score_report, dict):
            score_report = {}
        provider = str(score_report.get("provider") or result.get("provider") or "unknown")
        model = str(score_report.get("model") or result.get("model") or "unknown")
        provider_model = f"{provider}:{model}"
        case_name = str(score_report.get("case_name") or result.get("case_name") or result.get("_run_id", "unknown"))
        case_type = str(score_report.get("case_type") or "unknown")
        difficulty = str(score_report.get("difficulty") or "unknown")
        risk = str(score_report.get("risk") or "unknown")
        outcome = "passed" if score_report.get("passed") is True else "failed"
        execution_status = str(result.get("status") or "unknown")

        model_eval_by_provider[provider] += 1
        model_eval_by_model[model] += 1
        model_eval_by_case_type[case_type] += 1
        model_eval_by_difficulty[difficulty] += 1
        model_eval_by_risk[risk] += 1
        model_eval_outcomes_by_provider[provider][outcome] += 1
        model_eval_outcomes_by_provider_model[provider_model][outcome] += 1
        model_eval_status_by_provider[provider][execution_status] += 1

        overall_score = as_float(score_report.get("overall_score"))
        if overall_score is not None:
            model_eval_scores_by_provider_model[provider_model].append(overall_score)

        raw_failure_modes = score_report.get("failure_modes", [])
        failure_modes = [str(failure_mode) for failure_mode in raw_failure_modes] if isinstance(raw_failure_modes, list) else []
        if execution_status in {"provider_failed", "provider_timeout", "provider_missing"} or any(
            mode in {"provider_failed", "provider_timeout"} for mode in failure_modes
        ):
            model_eval_infra_failures_by_provider_model[provider_model] += 1

        for failure_mode in failure_modes:
            model_eval_failure_modes[failure_mode] += 1

        model_eval_case_outcomes.append(
            {
                "run_id": result.get("_run_id"),
                "case_name": case_name,
                "provider": provider,
                "model": model,
                "label": score_report.get("label", "unknown"),
                "passed": score_report.get("passed", False),
                "overall_score": score_report.get("overall_score"),
                "difficulty": difficulty,
                "risk": risk,
            }
        )

    model_eval_matrices = scan_model_eval_matrices(runs_dir)
    matrix_results_total = 0
    matrix_skipped_by_provider: dict[str, Counter[str]] = defaultdict(Counter)
    matrix_outcomes_by_provider: dict[str, Counter[str]] = defaultdict(Counter)
    for matrix in model_eval_matrices:
        results = matrix.get("results", [])
        if not isinstance(results, list):
            continue
        for result in results:
            if not isinstance(result, dict):
                continue
            matrix_results_total += 1
            provider = str(result.get("provider", "unknown"))
            status = str(result.get("status", "unknown"))
            if status == "skipped":
                matrix_skipped_by_provider[provider][str(result.get("reason", "skipped"))] += 1
                continue
            outcome = "passed" if result.get("passed") is True else "failed"
            matrix_outcomes_by_provider[provider][outcome] += 1

    prompt_normalizer_evals = scan_prompt_normalizer_evals(runs_dir)
    prompt_normalizer_cases_total = 0
    prompt_normalizer_contract_passed = 0
    prompt_normalizer_verdicts: Counter[str] = Counter()
    latest_prompt_normalizer_by_case: dict[str, dict[str, object]] = {}
    for eval_report in prompt_normalizer_evals:
        summary = eval_report.get("summary", {})
        if not isinstance(summary, dict):
            summary = {}
        cases_total = summary.get("cases_total")
        contract_passed = summary.get("contract_passed")
        if isinstance(cases_total, int):
            prompt_normalizer_cases_total += cases_total
        if isinstance(contract_passed, int):
            prompt_normalizer_contract_passed += contract_passed
        verdicts = summary.get("verdicts", {})
        if isinstance(verdicts, dict):
            for verdict, count in verdicts.items():
                if isinstance(count, int):
                    prompt_normalizer_verdicts[str(verdict)] += count

        generated_at = str(eval_report.get("generated_at", ""))
        results = eval_report.get("results", [])
        if not isinstance(results, list):
            continue
        for result in results:
            if not isinstance(result, dict):
                continue
            case_name = str(result.get("case_name", "")).strip()
            if not case_name:
                continue
            comparison = result.get("comparison", {})
            comparison = comparison if isinstance(comparison, dict) else {}
            normalizer_report = result.get("normalizer_report", {})
            normalizer_report = normalizer_report if isinstance(normalizer_report, dict) else {}
            default_path_action = str(
                result.get("default_path_action")
                or normalizer_report.get("default_path_action")
                or "use_normalized_prompt"
            )
            existing = latest_prompt_normalizer_by_case.get(case_name)
            existing_generated_at = str(existing.get("generated_at", "")) if isinstance(existing, dict) else ""
            if existing is None or generated_at >= existing_generated_at:
                latest_prompt_normalizer_by_case[case_name] = {
                    "generated_at": generated_at,
                    "case_name": case_name,
                    "verdict": str(comparison.get("verdict", "unknown")),
                    "default_path_action": default_path_action,
                }

    prompt_normalizer_latest_verdicts: Counter[str] = Counter()
    prompt_normalizer_latest_actions: Counter[str] = Counter()
    for latest_case in latest_prompt_normalizer_by_case.values():
        prompt_normalizer_latest_verdicts[str(latest_case.get("verdict", "unknown"))] += 1
        prompt_normalizer_latest_actions[str(latest_case.get("default_path_action", "use_normalized_prompt"))] += 1

    model_call_results = scan_model_call_metadata(runs_dir)
    total_tokens = 0
    token_runs = 0
    total_estimated_cost_usd = 0.0
    cost_runs = 0
    estimated_cost_by_provider: defaultdict[str, float] = defaultdict(float)
    estimated_cost_by_selected_tier: defaultdict[str, float] = defaultdict(float)
    priced_run_ids: list[str] = []
    pricing_sources_used: Counter[str] = Counter()
    provider_call_counts_by_provider: Counter[str] = Counter()
    provider_call_counts_by_tier: Counter[str] = Counter()

    for result in model_call_results:
        provider = str(result.get("provider", "unknown"))
        tier = str(result.get("tier", "unknown"))
        provider_call_counts_by_provider[provider] += 1
        provider_call_counts_by_tier[tier] += 1

        usage = usage_summary_from_metadata(result)
        tokens = as_int(usage.get("total_tokens"))
        if tokens is not None:
            total_tokens += tokens
            token_runs += 1

        estimated_cost, pricing_source = estimate_cost_from_metadata(result, runtime)
        if estimated_cost is not None:
            total_estimated_cost_usd += estimated_cost
            cost_runs += 1
            priced_run_ids.append(str(result.get("_path", result.get("_run_id", "unknown"))))
            estimated_cost_by_provider[provider] += estimated_cost
            estimated_cost_by_selected_tier[tier] += estimated_cost
            if pricing_source:
                pricing_sources_used[pricing_source] += 1

    metrics = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "runs_total": len(runs),
        "runs_passed": status_counts.get("passed", 0),
        "runs_failed": status_counts.get("failed", 0),
        "runs_needs_review": status_counts.get("needs_review", 0),
        "average_confidence": average_confidence,
        "workflow_signoff_pass_rate": round(status_counts.get("passed", 0) / max(1, len(runs)), 2) if runs else 0.0,
        "workflow_needs_review_rate": round(status_counts.get("needs_review", 0) / max(1, len(runs)), 2) if runs else 0.0,
        "accepted_runs_total": accepted_runs_total,
        "acceptance_rate": round(accepted_runs_total / max(1, len(runs)), 2) if runs else 0.0,
        "accepted_runs_by_recipe": dict(accepted_by_recipe),
        "accepted_runs_by_validation_profile": dict(accepted_by_profile),
        "accepted_runs_by_selected_tier": dict(accepted_by_tier),
        "accepted_runs_by_task_type": dict(accepted_by_task_type),
        "review_required_runs_total": public_outcomes.get("review_required", 0),
        "failed_runs_total": public_outcomes.get("failed", 0),
        "other_runs_total": public_outcomes.get("other", 0),
        "outcome_counts": dict(public_outcomes),
        "quality_gate_outcomes": dict(quality_outcomes),
        "failure_reasons": dict(failure_reason_counts.most_common(10)),
        "acceptance_breakdown": {
            "by_recipe": acceptance_breakdown(acceptance_by_recipe),
            "by_validation_profile": acceptance_breakdown(acceptance_by_profile),
            "by_selected_tier": acceptance_breakdown(acceptance_by_tier),
            "by_quality_gate_outcome": acceptance_breakdown(acceptance_by_quality_outcome),
        },
        "outcome_breakdown": {
            "by_recipe": outcome_breakdown(outcome_by_recipe),
            "by_validation_profile": outcome_breakdown(outcome_by_profile),
            "by_selected_tier": outcome_breakdown(outcome_by_tier),
            "by_quality_gate_outcome": outcome_breakdown(outcome_by_quality_outcome),
        },
        "routing_feedback_candidates": routing_feedback_candidates(
            routing_candidate_outcomes,
            routing_candidate_failure_reasons,
        ),
        "confidence_by_task_type": confidence_by_task_result,
        "model_tier_usage": dict(tier_usage),
        "validation_profiles_used": dict(profiles_used),
        "most_common_missing_context_info": dict(missing_info.most_common(10)),
        "most_common_missing_context_needs_review": dict(missing_needs_review.most_common(10)),
        "review_loop_triggers": dict(review_triggers),
        "selected_tier_by_risk": {key: dict(value) for key, value in tier_by_risk.items()},
        "selected_tier_by_complexity_band": {key: dict(value) for key, value in tier_by_complexity_band.items()},
        "final_status_by_selected_tier": {key: dict(value) for key, value in status_by_tier.items()},
        "review_loop_trigger_by_selected_tier": {key: dict(value) for key, value in review_trigger_by_tier.items()},
        "prompt_by_selected_tier": {key: dict(value.most_common(10)) for key, value in prompt_by_tier.items()},
        "eval_pass_rate_by_selected_tier": {
            tier: {
                "passed": counts.get("passed", 0),
                "failed": counts.get("failed", 0),
                "pass_rate": round(counts.get("passed", 0) / max(1, counts.get("passed", 0) + counts.get("failed", 0)), 2),
            }
            for tier, counts in evals_by_tier.items()
        },
        "common_bad_patterns_by_selected_tier": {
            tier: dict(counts.most_common(10)) for tier, counts in bad_patterns_by_tier.items()
        },
        "golden_case_failures_by_prompt": dict(failures_by_prompt.most_common(10)),
        "model_eval_runs_total": len(model_eval_results),
        "model_eval_runs_by_provider": dict(model_eval_by_provider),
        "model_eval_runs_by_model": dict(model_eval_by_model),
        "model_eval_runs_by_case_type": dict(model_eval_by_case_type),
        "model_eval_runs_by_difficulty": dict(model_eval_by_difficulty),
        "model_eval_runs_by_risk": dict(model_eval_by_risk),
        "model_eval_pass_rate_by_provider": {
            provider: {
                "passed": counts.get("passed", 0),
                "failed": counts.get("failed", 0),
                "pass_rate": round(counts.get("passed", 0) / max(1, counts.get("passed", 0) + counts.get("failed", 0)), 2),
            }
            for provider, counts in model_eval_outcomes_by_provider.items()
        },
        "model_eval_pass_rate_by_provider_model": {
            provider_model: {
                "passed": counts.get("passed", 0),
                "failed": counts.get("failed", 0),
                "pass_rate": round(counts.get("passed", 0) / max(1, counts.get("passed", 0) + counts.get("failed", 0)), 2),
                "average_score": round(
                    sum(model_eval_scores_by_provider_model.get(provider_model, []))
                    / max(1, len(model_eval_scores_by_provider_model.get(provider_model, []))),
                    2,
                ),
            }
            for provider_model, counts in model_eval_outcomes_by_provider_model.items()
        },
        "model_eval_execution_status_by_provider": {
            provider: dict(counts) for provider, counts in model_eval_status_by_provider.items()
        },
        "model_eval_infra_failures_by_provider_model": dict(model_eval_infra_failures_by_provider_model),
        "model_eval_common_failure_modes": dict(model_eval_failure_modes.most_common(10)),
        "model_eval_case_outcomes": model_eval_case_outcomes,
        "model_eval_matrix_reports_total": len(model_eval_matrices),
        "model_eval_matrix_results_total": matrix_results_total,
        "model_eval_matrix_outcomes_by_provider": {
            provider: dict(counts) for provider, counts in matrix_outcomes_by_provider.items()
        },
        "model_eval_matrix_skipped_by_provider": {
            provider: dict(counts) for provider, counts in matrix_skipped_by_provider.items()
        },
        "prompt_normalizer_eval_reports_total": len(prompt_normalizer_evals),
        "prompt_normalizer_eval_cases_total": prompt_normalizer_cases_total,
        "prompt_normalizer_contract_passed": prompt_normalizer_contract_passed,
        "prompt_normalizer_verdicts": dict(prompt_normalizer_verdicts),
        "prompt_normalizer_latest_cases_total": len(latest_prompt_normalizer_by_case),
        "prompt_normalizer_latest_verdicts": dict(prompt_normalizer_latest_verdicts),
        "prompt_normalizer_latest_default_path_actions": dict(prompt_normalizer_latest_actions),
        "golden_case_count": golden_case_count(Path(args.evals_dir)),
        "manual_handoff_count": manual_handoff_count,
        "response_captured_count": response_captured_count,
        "total_tokens_tracked": total_tokens,
        "runs_with_token_data": token_runs,
        "average_tokens_per_run": round(total_tokens / max(1, token_runs)) if token_runs else 0,
        "total_estimated_cost_usd": round(total_estimated_cost_usd, 8),
        "runs_with_cost_data": cost_runs,
        "average_estimated_cost_usd_per_priced_run": round(total_estimated_cost_usd / max(1, cost_runs), 8) if cost_runs else 0.0,
        "estimated_cost_usd_by_provider": {
            provider: round(amount, 8) for provider, amount in estimated_cost_by_provider.items()
        },
        "estimated_cost_usd_by_selected_tier": {
            tier: round(amount, 8) for tier, amount in estimated_cost_by_selected_tier.items()
        },
        "pricing_sources_used": dict(pricing_sources_used),
        "runs_with_cost_data_ids": priced_run_ids,
        "provider_calls_total": len(model_call_results),
        "provider_call_counts_by_provider": dict(provider_call_counts_by_provider),
        "provider_call_counts_by_tier": dict(provider_call_counts_by_tier),
        "runs_eligible_for_golden_cases": [
            str(run["run_id"]) for run in runs if run["eligible_for_golden_case"]
        ],
        "routing_feedback_matrix": {
            key: {
                "passed": counts.get("passed", 0),
                "needs_review": counts.get("needs_review", 0),
                "failed": counts.get("failed", 0),
                "total": sum(counts.values()),
                "pass_rate": round(
                    counts.get("passed", 0) / max(1, sum(counts.values())), 2
                ),
            }
            for key, counts in sorted(routing_feedback.items())
        },
        "workflow_kpis": {
            "runs_total": len(runs),
            "runs_passed": status_counts.get("passed", 0),
            "runs_failed": status_counts.get("failed", 0),
            "runs_needs_review": status_counts.get("needs_review", 0),
            "workflow_signoff_pass_rate": round(status_counts.get("passed", 0) / max(1, len(runs)), 2) if runs else 0.0,
            "workflow_needs_review_rate": round(status_counts.get("needs_review", 0) / max(1, len(runs)), 2) if runs else 0.0,
            "average_confidence": average_confidence,
            "accepted_runs_total": accepted_runs_total,
            "acceptance_rate": round(accepted_runs_total / max(1, len(runs)), 2) if runs else 0.0,
            "accepted_runs_by_recipe": dict(accepted_by_recipe),
            "accepted_runs_by_validation_profile": dict(accepted_by_profile),
            "accepted_runs_by_selected_tier": dict(accepted_by_tier),
            "review_required_runs_total": public_outcomes.get("review_required", 0),
            "failed_runs_total": public_outcomes.get("failed", 0),
            "outcome_counts": dict(public_outcomes),
            "quality_gate_outcomes": dict(quality_outcomes),
            "failure_reasons": dict(failure_reason_counts.most_common(10)),
            "manual_handoff_count": manual_handoff_count,
            "response_captured_count": response_captured_count,
            "review_loop_triggers": dict(review_triggers),
            "runs_eligible_for_golden_cases": len([run for run in runs if run["eligible_for_golden_case"]]),
            "golden_case_count": golden_case_count(Path(args.evals_dir)),
        },
        "cost_tracking": {
            "total_tokens_tracked": total_tokens,
            "runs_with_token_data": token_runs,
            "average_tokens_per_run": round(total_tokens / max(1, token_runs)) if token_runs else 0,
            "total_estimated_cost_usd": round(total_estimated_cost_usd, 8),
            "runs_with_cost_data": cost_runs,
            "average_estimated_cost_usd_per_priced_run": round(total_estimated_cost_usd / max(1, cost_runs), 8) if cost_runs else 0.0,
            "estimated_cost_usd_by_provider": {
                provider: round(amount, 8) for provider, amount in estimated_cost_by_provider.items()
            },
            "estimated_cost_usd_by_selected_tier": {
                tier: round(amount, 8) for tier, amount in estimated_cost_by_selected_tier.items()
            },
            "pricing_sources_used": dict(pricing_sources_used),
            "runs_with_cost_data_ids": priced_run_ids,
            "provider_calls_total": len(model_call_results),
            "provider_call_counts_by_provider": dict(provider_call_counts_by_provider),
            "provider_call_counts_by_tier": dict(provider_call_counts_by_tier),
        },
        "model_eval_kpis": {
            "model_eval_runs_total": len(model_eval_results),
            "model_eval_runs_by_provider": dict(model_eval_by_provider),
            "model_eval_runs_by_case_type": dict(model_eval_by_case_type),
            "model_eval_pass_rate_by_provider": {
                provider: {
                    "passed": counts.get("passed", 0),
                    "failed": counts.get("failed", 0),
                    "pass_rate": round(counts.get("passed", 0) / max(1, counts.get("passed", 0) + counts.get("failed", 0)), 2),
                }
                for provider, counts in model_eval_outcomes_by_provider.items()
            },
            "model_eval_pass_rate_by_provider_model": {
                provider_model: {
                    "passed": counts.get("passed", 0),
                    "failed": counts.get("failed", 0),
                    "pass_rate": round(counts.get("passed", 0) / max(1, counts.get("passed", 0) + counts.get("failed", 0)), 2),
                    "average_score": round(
                        sum(model_eval_scores_by_provider_model.get(provider_model, []))
                        / max(1, len(model_eval_scores_by_provider_model.get(provider_model, []))),
                        2,
                    ),
                }
                for provider_model, counts in model_eval_outcomes_by_provider_model.items()
            },
            "model_eval_execution_status_by_provider": {
                provider: dict(counts) for provider, counts in model_eval_status_by_provider.items()
            },
            "model_eval_common_failure_modes": dict(model_eval_failure_modes.most_common(10)),
        },
        "prompt_normalizer_kpis": {
            "prompt_normalizer_eval_reports_total": len(prompt_normalizer_evals),
            "prompt_normalizer_eval_cases_total": prompt_normalizer_cases_total,
            "prompt_normalizer_contract_passed": prompt_normalizer_contract_passed,
            "prompt_normalizer_verdicts": dict(prompt_normalizer_verdicts),
            "prompt_normalizer_latest_cases_total": len(latest_prompt_normalizer_by_case),
            "prompt_normalizer_latest_verdicts": dict(prompt_normalizer_latest_verdicts),
            "prompt_normalizer_latest_default_path_actions": dict(prompt_normalizer_latest_actions),
        },
    }

    metrics_path = out_dir / "run_metrics.json"
    summary_path = out_dir / "run_summary.md"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Run Analysis Summary",
        "",
        f"Generated: `{metrics['generated_at']}`",
        "",
        "## Workflow KPIs",
        "",
        f"- Runs total: {metrics['runs_total']}",
        f"- Passed: {metrics['runs_passed']}",
        f"- Failed: {metrics['runs_failed']}",
        f"- Needs review: {metrics['runs_needs_review']}",
        f"- Workflow sign-off pass rate: {metrics['workflow_signoff_pass_rate']}",
        f"- Workflow needs-review rate: {metrics['workflow_needs_review_rate']}",
        f"- Average confidence: {metrics['average_confidence']}",
        f"- Accepted runs total: {metrics['accepted_runs_total']}",
        f"- Review-required runs total: {metrics['review_required_runs_total']}",
        f"- Failed runs total: {metrics['failed_runs_total']}",
        f"- Acceptance rate: {metrics['acceptance_rate']}",
        "",
        "## Acceptance Outcomes",
        "",
        f"- Outcome counts: {metrics['outcome_counts']}",
        f"- Quality-gate outcomes: {metrics['quality_gate_outcomes']}",
        f"- Failure reasons: {metrics['failure_reasons']}",
        "",
        "## Acceptance Analytics",
        "",
        f"- Accepted runs by recipe: {metrics['accepted_runs_by_recipe']}",
        f"- Accepted runs by validation profile: {metrics['accepted_runs_by_validation_profile']}",
        f"- Accepted runs by selected tier: {metrics['accepted_runs_by_selected_tier']}",
        "",
        "### Public Outcomes By Recipe",
        "",
        "| Recipe | Accepted | Review Required | Failed | Other | Total | Acceptance Rate | Review Rate | Failure Rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    recipe_breakdown = as_dict(as_dict(metrics.get("outcome_breakdown")).get("by_recipe"))
    for recipe, data in recipe_breakdown.items():
        data = as_dict(data)
        lines.append(
            f"| {recipe} | {data.get('accepted', 0)} | {data.get('review_required', 0)} | {data.get('failed', 0)} | {data.get('other', 0)} | {data.get('total', 0)} | {data.get('acceptance_rate', 0.0)} | {data.get('review_rate', 0.0)} | {data.get('failure_rate', 0.0)} |"
        )
    lines.extend([
        "",
        "## Workflow Signals",
        "",
        f"- Manual handoff count: {manual_handoff_count}",
        f"- Response captured count: {response_captured_count}",
        f"- Review loop triggers: {dict(review_triggers)}",
        f"- Runs eligible for golden cases: {len(metrics['runs_eligible_for_golden_cases'])}",
        f"- Golden cases available: {metrics['golden_case_count']}",
        "",
        "## Cost Tracking",
        "",
        "Cost tracking is optional provider metadata; zero or empty values mean no provider cost evidence was found.",
        f"- Total tokens tracked: {metrics['total_tokens_tracked']}",
        f"- Runs with token data: {metrics['runs_with_token_data']}",
        f"- Average tokens per run: {metrics['average_tokens_per_run']}",
        f"- Provider calls scanned: {metrics['provider_calls_total']}",
        f"- Total estimated cost (USD): {metrics['total_estimated_cost_usd']}",
        f"- Runs with cost data: {metrics['runs_with_cost_data']}",
        f"- Average estimated cost per priced run (USD): {metrics['average_estimated_cost_usd_per_priced_run']}",
        f"- Estimated cost by provider: {metrics['estimated_cost_usd_by_provider']}",
        f"- Estimated cost by selected tier: {metrics['estimated_cost_usd_by_selected_tier']}",
        "",
        "## Routing Evidence",
        "",
        f"- Selected tier by risk: {metrics['selected_tier_by_risk']}",
        f"- Selected tier by complexity band: {metrics['selected_tier_by_complexity_band']}",
        f"- Final status by selected tier: {metrics['final_status_by_selected_tier']}",
        f"- Review triggers by selected tier: {metrics['review_loop_trigger_by_selected_tier']}",
        f"- Eval pass rate by selected tier: {metrics['eval_pass_rate_by_selected_tier']}",
        "",
        "## Routing Feedback Candidates",
        "",
        "| Recipe | Profile | Tier | Risk | Complexity | Accepted | Review Required | Failed | Total | Acceptance Rate | Review Rate | Failure Rate | Top Failure Reasons |",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ])
    candidates = metrics.get("routing_feedback_candidates", {})
    for _key, data in (candidates.items() if isinstance(candidates, dict) else []):
        data = as_dict(data)
        top_reasons = as_dict(data.get("top_failure_reasons"))
        reason_text = ", ".join(f"{reason}={count}" for reason, count in top_reasons.items()) or ""
        lines.append(
            f"| {data.get('recipe', 'unknown')} | {data.get('validation_profile', 'unknown')} | {data.get('selected_tier', 'unknown')} | {data.get('risk', 'unknown')} | {data.get('complexity_band', 'unknown')} | {data.get('accepted', 0)} | {data.get('review_required', 0)} | {data.get('failed', 0)} | {data.get('total', 0)} | {data.get('acceptance_rate', 0.0)} | {data.get('review_rate', 0.0)} | {data.get('failure_rate', 0.0)} | {reason_text} |"
        )
    lines.extend([
        "",
        "## Routing Feedback Matrix (tier|risk|complexity → pass rate)",
        "",
        "| Tier | Risk | Complexity | Passed | Needs Review | Failed | Total | Pass Rate |",
        "|---|---|---|---:|---:|---:|---:|---:|",
    ])
    rfm = metrics.get("routing_feedback_matrix", {})
    for key, data in (rfm.items() if isinstance(rfm, dict) else []):
        parts = str(key).split("|")
        tier, risk, complexity = (parts + ["?", "?", "?"])[:3]
        lines.append(
            f"| {tier} | {risk} | {complexity} | {data.get('passed', 0)} | {data.get('needs_review', 0)} | {data.get('failed', 0)} | {data.get('total', 0)} | {data.get('pass_rate', 0.0)} |"
        )
    lines.extend([
        "",
        "## Model Eval Evidence",
        "",
        f"- Model eval runs total: {metrics['model_eval_runs_total']}",
        f"- Runs by provider: {metrics['model_eval_runs_by_provider']}",
        f"- Runs by case type: {metrics['model_eval_runs_by_case_type']}",
        f"- Pass rate by provider/model: {metrics['model_eval_pass_rate_by_provider_model']}",
        f"- Execution status by provider: {metrics['model_eval_execution_status_by_provider']}",
        f"- Infrastructure failures by provider/model: {metrics['model_eval_infra_failures_by_provider_model']}",
        f"- Common failure modes: {metrics['model_eval_common_failure_modes']}",
        f"- Matrix reports total: {metrics['model_eval_matrix_reports_total']}",
        f"- Matrix skipped by provider: {metrics['model_eval_matrix_skipped_by_provider']}",
        "",
        "## Prompt Normalizer Evidence",
        "",
        f"- Prompt normalizer eval reports total: {metrics['prompt_normalizer_eval_reports_total']}",
        f"- Prompt normalizer cases total: {metrics['prompt_normalizer_eval_cases_total']}",
        f"- Prompt normalizer contract passed: {metrics['prompt_normalizer_contract_passed']}",
        f"- Prompt normalizer verdicts (historical aggregate): {metrics['prompt_normalizer_verdicts']}",
        f"- Prompt normalizer latest cases tracked: {metrics['prompt_normalizer_latest_cases_total']}",
        f"- Prompt normalizer latest verdicts by case: {metrics['prompt_normalizer_latest_verdicts']}",
        f"- Prompt normalizer latest default-path actions: {metrics['prompt_normalizer_latest_default_path_actions']}",
        "",
        "## Runs",
        "",
        "| Run ID | Status | Task Type | Golden Eligible |",
        "|---|---|---|---|",
    ])
    for run in runs:
        lines.append(
            f"| {run['run_id']} | {run['status']} | {run['task_type']} | {str(run['eligible_for_golden_case']).lower()} |"
        )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return metrics


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        metrics = run_analysis_payload(args)
    except FileNotFoundError as exc:
        print(str(exc))
        return 1

    runs_dir = Path(args.runs_dir)
    out_dir = Path(args.out_dir) if args.out_dir else runs_dir / "_reports"
    metrics_path = out_dir / "run_metrics.json"
    summary_path = out_dir / "run_summary.md"

    print(f"run_metrics={metrics_path}")
    print(f"run_summary={summary_path}")
    print(f"runs_total={metrics['runs_total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
