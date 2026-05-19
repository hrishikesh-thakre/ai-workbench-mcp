from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
from pathlib import Path

from .run_cost_time import (
    as_dict,
    as_float,
    as_int,
    duration_ms_from_metadata,
    estimate_cost_from_metadata,
    format_duration_ms,
    format_usd,
    load_runtime_config,
    selected_model_parts,
    successful_attempt_model,
    usage_summary_from_metadata,
    validation_duration_ms,
)
from .run_dashboard import (
    run_failure_reason_text,
    write_dashboard,
)
from .run_evidence import (
    eligible_for_golden_case,
    evidence_scope_for,
    exclusion_reason_for_missing_artifact,
    execution_host_for,
    final_prompt_name,
    golden_case_count,
    latest_tier,
    missing_complete_evidence,
    read_json,
    read_jsonl,
    response_source_for,
    run_created_at,
    scan_eval_results,
    scan_model_call_metadata,
    scan_model_eval_matrices,
    scan_model_eval_results,
    scan_prompt_normalizer_evals,
    selection_for,
    task_metadata_for,
    task_type_for,
)
from .run_metrics import (
    acceptance_breakdown,
    acceptance_bucket,
    accepted_by_validation_and_gate,
    failure_reasons,
    final_status,
    outcome_breakdown,
    public_outcome_bucket,
    quality_gate_outcome,
    recipe_for,
    routing_feedback_candidates,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Analyze local runs folders for Phase 2 metrics.")
    parser.add_argument("--runs-dir", default="runs", help="Directory containing run folders.")
    parser.add_argument("--task-type", help="Optional task type filter.")
    parser.add_argument("--since", help="Optional ISO timestamp/date lower bound.")
    parser.add_argument("--out-dir", help="Report directory. Defaults to <runs-dir>/_reports.")
    parser.add_argument("--evals-dir", default="evals/golden_cases", help="Directory containing golden cases.")
    parser.add_argument(
        "--evidence-scope",
        choices=("all", "complete"),
        default="all",
        help=(
            "Run evidence scope. 'all' preserves legacy behavior and counts any folder with run_log.jsonl. "
            "'complete' counts only folders with run_log.jsonl, validation_report.json, and revision_decision.json."
        ),
    )
    return parser


def run_analysis_payload(args: argparse.Namespace) -> dict[str, object]:
    runs_dir = Path(args.runs_dir)
    if not runs_dir.exists():
        raise FileNotFoundError(f"runs_dir_missing={runs_dir}")

    out_dir = Path(args.out_dir) if args.out_dir else runs_dir / "_reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    runtime = load_runtime_config()
    evidence_scope = evidence_scope_for(args)
    excluded_runs_total = 0
    excluded_runs_by_reason: Counter[str] = Counter()

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
        missing_evidence = missing_complete_evidence(run_dir)
        if evidence_scope == "complete" and missing_evidence:
            excluded_runs_total += 1
            for artifact_name in missing_evidence:
                excluded_runs_by_reason[exclusion_reason_for_missing_artifact(artifact_name)] += 1
            continue
        report = read_json(run_dir / "validation_report.json")
        decision = read_json(run_dir / "revision_decision.json")
        selection = selection_for(run_dir)
        metadata = task_metadata_for(run_dir)
        validation_time_ms = validation_duration_ms(report)
        execution_host = execution_host_for(metadata)
        response_source = response_source_for(run_dir)
        runs.append(
            {
                "run_id": run_dir.name,
                "path": str(run_dir),
                "logs": logs,
                "report": report,
                "decision": decision,
                "selection": selection,
                "metadata": metadata,
                "execution_host": execution_host,
                "response_source": response_source,
                "task_type": task_type,
                "status": final_status(report, decision),
                "validation_duration_ms": validation_time_ms,
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
    accepted_by_execution_host: Counter[str] = Counter()
    accepted_by_response_source: Counter[str] = Counter()
    accepted_by_profile: Counter[str] = Counter()
    accepted_by_tier: Counter[str] = Counter()
    accepted_by_task_type: Counter[str] = Counter()
    public_outcomes: Counter[str] = Counter()
    quality_outcomes: Counter[str] = Counter()
    execution_host_counts: Counter[str] = Counter()
    response_source_counts: Counter[str] = Counter()
    failure_reason_counts: Counter[str] = Counter()
    acceptance_by_recipe: dict[str, Counter[str]] = defaultdict(Counter)
    acceptance_by_profile: dict[str, Counter[str]] = defaultdict(Counter)
    acceptance_by_tier: dict[str, Counter[str]] = defaultdict(Counter)
    acceptance_by_quality_outcome: dict[str, Counter[str]] = defaultdict(Counter)
    outcome_by_recipe: dict[str, Counter[str]] = defaultdict(Counter)
    outcome_by_execution_host: dict[str, Counter[str]] = defaultdict(Counter)
    outcome_by_response_source: dict[str, Counter[str]] = defaultdict(Counter)
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
        execution_host = str(run.get("execution_host") or "goose")
        response_source = str(run.get("response_source") or "unknown")
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
        execution_host_counts[execution_host] += 1
        response_source_counts[response_source] += 1
        acceptance_by_recipe[recipe][bucket] += 1
        acceptance_by_profile[profile][bucket] += 1
        acceptance_by_tier[selected_tier][bucket] += 1
        acceptance_by_quality_outcome[gate_outcome][bucket] += 1
        outcome_by_recipe[recipe][public_bucket] += 1
        outcome_by_execution_host[execution_host][public_bucket] += 1
        outcome_by_response_source[response_source][public_bucket] += 1
        outcome_by_profile[profile][public_bucket] += 1
        outcome_by_tier[selected_tier][public_bucket] += 1
        outcome_by_quality_outcome[gate_outcome][public_bucket] += 1
        routing_candidate_key = f"{recipe}|{profile}|{selected_tier}|{risk}|{complexity_band}"
        routing_candidate_outcomes[routing_candidate_key][public_bucket] += 1
        if accepted:
            accepted_runs_total += 1
            accepted_by_recipe[recipe] += 1
            accepted_by_execution_host[execution_host] += 1
            accepted_by_response_source[response_source] += 1
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
    provider_calls_with_time_data = 0
    total_provider_duration_ms = 0
    provider_duration_ms_by_provider: defaultdict[str, int] = defaultdict(int)
    provider_duration_ms_by_tier: defaultdict[str, int] = defaultdict(int)
    raw_run_cost_time: dict[str, dict[str, object]] = {}

    for result in model_call_results:
        provider = str(result.get("provider", "unknown"))
        tier = str(result.get("tier", "unknown"))
        run_id = str(result.get("_run_id", "unknown"))
        provider_call_counts_by_provider[provider] += 1
        provider_call_counts_by_tier[tier] += 1
        run_cost_time = raw_run_cost_time.setdefault(
            run_id,
            {
                "provider_calls": 0,
                "providers": Counter(),
                "models": Counter(),
                "tiers": Counter(),
                "total_tokens": 0,
                "has_token_data": False,
                "estimated_cost_usd": 0.0,
                "has_cost_data": False,
                "provider_duration_ms": 0,
                "has_provider_time_data": False,
            },
        )
        run_cost_time["provider_calls"] = int(run_cost_time.get("provider_calls", 0)) + 1
        providers = run_cost_time.get("providers")
        if isinstance(providers, Counter):
            providers[provider] += 1
        model = str(result.get("model") or successful_attempt_model(result) or "unknown")
        models = run_cost_time.get("models")
        if isinstance(models, Counter):
            models[model] += 1
        tiers = run_cost_time.get("tiers")
        if isinstance(tiers, Counter):
            tiers[tier] += 1

        usage = usage_summary_from_metadata(result)
        tokens = as_int(usage.get("total_tokens"))
        if tokens is not None:
            total_tokens += tokens
            token_runs += 1
            run_cost_time["total_tokens"] = int(run_cost_time.get("total_tokens", 0)) + tokens
            run_cost_time["has_token_data"] = True

        estimated_cost, pricing_source = estimate_cost_from_metadata(result, runtime)
        if estimated_cost is not None:
            total_estimated_cost_usd += estimated_cost
            cost_runs += 1
            priced_run_ids.append(run_id)
            estimated_cost_by_provider[provider] += estimated_cost
            estimated_cost_by_selected_tier[tier] += estimated_cost
            run_cost_time["estimated_cost_usd"] = float(run_cost_time.get("estimated_cost_usd", 0.0)) + estimated_cost
            run_cost_time["has_cost_data"] = True
            if pricing_source:
                pricing_sources_used[pricing_source] += 1

        provider_duration_ms = duration_ms_from_metadata(result)
        if provider_duration_ms is not None:
            provider_calls_with_time_data += 1
            total_provider_duration_ms += provider_duration_ms
            provider_duration_ms_by_provider[provider] += provider_duration_ms
            provider_duration_ms_by_tier[tier] += provider_duration_ms
            run_cost_time["provider_duration_ms"] = int(run_cost_time.get("provider_duration_ms", 0)) + provider_duration_ms
            run_cost_time["has_provider_time_data"] = True

    total_validation_duration_ms = 0
    validation_runs_with_time_data = 0
    run_cost_time_by_run: dict[str, dict[str, object]] = {}
    for run in runs:
        run_id = str(run.get("run_id", "unknown"))
        source = raw_run_cost_time.get(run_id, {})
        validation_time_ms = as_int(run.get("validation_duration_ms"))
        has_validation_time_data = validation_time_ms is not None
        if validation_time_ms is not None:
            total_validation_duration_ms += validation_time_ms
            validation_runs_with_time_data += 1

        providers = source.get("providers")
        models = source.get("models")
        tiers = source.get("tiers")
        normalized_cost_time = {
            "provider_calls": int(source.get("provider_calls", 0)),
            "providers": dict(providers) if isinstance(providers, Counter) else {},
            "models": dict(models) if isinstance(models, Counter) else {},
            "tiers": dict(tiers) if isinstance(tiers, Counter) else {},
            "has_token_data": bool(source.get("has_token_data", False)),
            "total_tokens": int(source.get("total_tokens", 0)),
            "has_cost_data": bool(source.get("has_cost_data", False)),
            "estimated_cost_usd": round(float(source.get("estimated_cost_usd", 0.0)), 8),
            "has_provider_time_data": bool(source.get("has_provider_time_data", False)),
            "provider_duration_ms": int(source.get("provider_duration_ms", 0)),
            "has_validation_time_data": has_validation_time_data,
            "validation_duration_ms": validation_time_ms if validation_time_ms is not None else 0,
        }
        run["cost_time"] = normalized_cost_time
        run_cost_time_by_run[run_id] = normalized_cost_time

    metrics = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "evidence_scope": evidence_scope,
        "excluded_runs_total": excluded_runs_total,
        "excluded_runs_by_reason": dict(excluded_runs_by_reason),
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
        "accepted_runs_by_execution_host": dict(accepted_by_execution_host),
        "accepted_runs_by_response_source": dict(accepted_by_response_source),
        "accepted_runs_by_validation_profile": dict(accepted_by_profile),
        "accepted_runs_by_selected_tier": dict(accepted_by_tier),
        "accepted_runs_by_task_type": dict(accepted_by_task_type),
        "execution_host_counts": dict(execution_host_counts),
        "response_source_counts": dict(response_source_counts),
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
            "by_execution_host": outcome_breakdown(outcome_by_execution_host),
            "by_response_source": outcome_breakdown(outcome_by_response_source),
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
        "time_tracking": {
            "provider_calls_with_time_data": provider_calls_with_time_data,
            "total_provider_duration_ms": total_provider_duration_ms,
            "average_provider_duration_ms_per_timed_call": (
                round(total_provider_duration_ms / max(1, provider_calls_with_time_data))
                if provider_calls_with_time_data
                else 0
            ),
            "runs_with_provider_time_data": len(
                [
                    run_id
                    for run_id, summary in run_cost_time_by_run.items()
                    if summary.get("has_provider_time_data") is True
                ]
            ),
            "provider_duration_ms_by_provider": dict(provider_duration_ms_by_provider),
            "provider_duration_ms_by_selected_tier": dict(provider_duration_ms_by_tier),
            "validation_runs_with_time_data": validation_runs_with_time_data,
            "total_validation_duration_ms": total_validation_duration_ms,
            "average_validation_duration_ms_per_timed_run": (
                round(total_validation_duration_ms / max(1, validation_runs_with_time_data))
                if validation_runs_with_time_data
                else 0
            ),
        },
        "run_cost_time": run_cost_time_by_run,
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
            "evidence_scope": evidence_scope,
            "excluded_runs_total": excluded_runs_total,
            "excluded_runs_by_reason": dict(excluded_runs_by_reason),
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
            "accepted_runs_by_execution_host": dict(accepted_by_execution_host),
            "accepted_runs_by_response_source": dict(accepted_by_response_source),
            "accepted_runs_by_validation_profile": dict(accepted_by_profile),
            "accepted_runs_by_selected_tier": dict(accepted_by_tier),
            "execution_host_counts": dict(execution_host_counts),
            "response_source_counts": dict(response_source_counts),
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
            "provider_calls_with_time_data": provider_calls_with_time_data,
            "runs_with_provider_time_data": len(
                [
                    run_id
                    for run_id, summary in run_cost_time_by_run.items()
                    if summary.get("has_provider_time_data") is True
                ]
            ),
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
    dashboard_path = out_dir / "run_dashboard.html"
    metrics_path.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Run Analysis Summary",
        "",
        f"Generated: `{metrics['generated_at']}`",
        "",
        "## Workflow KPIs",
        "",
        f"- Evidence scope: {metrics['evidence_scope']}",
        f"- Excluded runs total: {metrics['excluded_runs_total']}",
        f"- Excluded runs by reason: {metrics['excluded_runs_by_reason']}",
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
        f"- Accepted runs by execution host: {metrics['accepted_runs_by_execution_host']}",
        f"- Accepted runs by response source: {metrics['accepted_runs_by_response_source']}",
        f"- Execution host counts: {metrics['execution_host_counts']}",
        f"- Response source counts: {metrics['response_source_counts']}",
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
        "### Public Outcomes By Execution Host",
        "",
        "| Execution Host | Accepted | Review Required | Failed | Other | Total | Acceptance Rate | Review Rate | Failure Rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    host_breakdown = as_dict(as_dict(metrics.get("outcome_breakdown")).get("by_execution_host"))
    for execution_host, data in host_breakdown.items():
        data = as_dict(data)
        lines.append(
            f"| {execution_host} | {data.get('accepted', 0)} | {data.get('review_required', 0)} | {data.get('failed', 0)} | {data.get('other', 0)} | {data.get('total', 0)} | {data.get('acceptance_rate', 0.0)} | {data.get('review_rate', 0.0)} | {data.get('failure_rate', 0.0)} |"
        )
    lines.extend([
        "",
        "### Public Outcomes By Response Source",
        "",
        "| Response Source | Accepted | Review Required | Failed | Other | Total | Acceptance Rate | Review Rate | Failure Rate |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ])
    source_breakdown = as_dict(as_dict(metrics.get("outcome_breakdown")).get("by_response_source"))
    for response_source, data in source_breakdown.items():
        data = as_dict(data)
        lines.append(
            f"| {response_source} | {data.get('accepted', 0)} | {data.get('review_required', 0)} | {data.get('failed', 0)} | {data.get('other', 0)} | {data.get('total', 0)} | {data.get('acceptance_rate', 0.0)} | {data.get('review_rate', 0.0)} | {data.get('failure_rate', 0.0)} |"
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
        "## Time Tracking",
        "",
        f"- Provider calls with time data: {metrics['time_tracking']['provider_calls_with_time_data']}",
        f"- Total provider duration (ms): {metrics['time_tracking']['total_provider_duration_ms']}",
        f"- Average provider duration per timed call (ms): {metrics['time_tracking']['average_provider_duration_ms_per_timed_call']}",
        f"- Runs with provider time data: {metrics['time_tracking']['runs_with_provider_time_data']}",
        f"- Validation runs with time data: {metrics['time_tracking']['validation_runs_with_time_data']}",
        f"- Total validation duration (ms): {metrics['time_tracking']['total_validation_duration_ms']}",
        f"- Average validation duration per timed run (ms): {metrics['time_tracking']['average_validation_duration_ms_per_timed_run']}",
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
        "## Run Details",
        "",
        "| Run ID | Outcome | Host | Source | Provider | Model | Profile | Gate | Failure Reasons | Tokens | Estimated Cost | Provider Time | Validation Time |",
        "|---|---|---|---|---|---|---|---|---|---:|---:|---:|---:|",
    ])
    for run in runs:
        report = as_dict(run.get("report"))
        decision = as_dict(run.get("decision"))
        selection = as_dict(run.get("selection"))
        cost_time = as_dict(run.get("cost_time"))
        provider, model = selected_model_parts(selection, cost_time)
        token_text = (
            str(as_int(cost_time.get("total_tokens")))
            if cost_time.get("has_token_data") is True and as_int(cost_time.get("total_tokens")) is not None
            else "not recorded"
        )
        lines.append(
            f"| {run['run_id']} | {public_outcome_bucket(report, decision)} | {run.get('execution_host', 'goose')} | {run.get('response_source', 'unknown')} | {provider} | {model} | {report.get('profile', 'unknown')} | {quality_gate_outcome(decision)} | {run_failure_reason_text(report, decision)} | {token_text} | {format_usd(cost_time.get('estimated_cost_usd'), cost_time.get('has_cost_data') is True)} | {format_duration_ms(cost_time.get('provider_duration_ms'), cost_time.get('has_provider_time_data') is True)} | {format_duration_ms(cost_time.get('validation_duration_ms'), cost_time.get('has_validation_time_data') is True)} |"
        )
    lines.extend([
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
    write_dashboard(metrics, runs, out_dir)
    if not dashboard_path.exists():
        raise RuntimeError(f"run_dashboard_missing={dashboard_path}")
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
    dashboard_path = out_dir / "run_dashboard.html"

    print(f"run_metrics={metrics_path}")
    print(f"run_summary={summary_path}")
    print(f"run_dashboard={dashboard_path}")
    print(f"runs_total={metrics['runs_total']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
