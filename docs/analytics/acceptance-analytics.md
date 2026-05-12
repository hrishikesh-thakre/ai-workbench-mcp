# Acceptance Analytics

`workbench_analyze_runs` turns local evidence ledgers into acceptance and routing feedback. It does not decide whether a single run is accepted; it summarizes already-recorded validation and quality-gate artifacts across runs.

Run analytics against the committed samples:

```bash
python tools/run_analyze.py --runs-dir examples/sample-runs --out-dir runs/sample-run-analytics
```

This writes:

- `run_metrics.json`: machine-readable metrics for routing, reporting, and future policy work.
- `run_summary.md`: human-readable tables for reviewing acceptance outcomes.

## Outcome Buckets

The public outcome buckets are mutually exclusive:

- `accepted`: deterministic validation passed and the quality gate accepted the run.
- `review_required`: the quality gate returned `review_required` or `revision_required`.
- `failed`: deterministic validation failed and there is no review or revision quality-gate path.

Detailed failure reasons remain available even when the public bucket is `review_required`. For example, a run can be counted as `review_required` and still report `command_failed:full_test_suite`.

## Key Metrics

Use these fields in `run_metrics.json` first:

- `runs_total`: number of run folders scanned.
- `outcome_counts`: accepted, review-required, failed, and other counts.
- `accepted_runs_total`: accepted count preserved for existing consumers.
- `review_required_runs_total`: public review-required count.
- `failed_runs_total`: public failed count.
- `acceptance_breakdown`: backward-compatible accepted/needs-review/failed breakdown.
- `outcome_breakdown`: public accepted/review-required/failed breakdown by recipe, validation profile, selected tier, and quality-gate outcome.
- `failure_reasons`: most common deterministic validation and quality-gate reasons.

## Routing Feedback Candidates

`routing_feedback_candidates` is report-ready data for later model-selection policy work. Each entry is keyed by:

```text
recipe | validation_profile | selected_tier | risk | complexity_band
```

Each candidate includes:

- total runs
- accepted count
- review-required count
- failed count
- acceptance rate
- review rate
- failure rate
- top failure reasons

Use this data to identify which recipe/profile/tier combinations are producing accepted work and which combinations need stronger routing, validation, or human review.

## Cost Tracking

Cost tracking is optional provider metadata. Empty or zero cost fields mean no provider cost evidence was found in the scanned run folders. They do not mean the run was free.

Cost fields are populated only when real `model_call_metadata.json` artifacts contain token or cost data.

## Reading The Summary

Open `run_summary.md` when you want a quick human review:

- `Workflow KPIs` shows high-level run counts.
- `Acceptance Outcomes` shows the public outcome totals and failure reasons.
- `Public Outcomes By Recipe` shows which recipes are producing accepted or review-required runs.
- `Routing Feedback Candidates` shows the future policy input shape.
- `Cost Tracking` states whether provider cost evidence was available.
