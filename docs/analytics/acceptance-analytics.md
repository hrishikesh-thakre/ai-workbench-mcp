# Acceptance Analytics

`workbench_analyze_runs` turns local evidence ledgers into acceptance and routing feedback. It does not decide whether a single run is accepted; it summarizes already-recorded validation and quality-gate artifacts across runs.

Run analytics against the committed samples:

```bash
python tools/run_analyze.py --runs-dir examples/sample-runs --out-dir runs/sample-run-analytics
```

The committed sample set includes legacy Goose evidence, explicit Codex local/IDE evidence, and a revision-required run so host/source breakdowns and outcome buckets are visible without provider setup.

For mixed local parents that include connectivity checks, tool-smoke folders, or interrupted attempts beside full acceptance runs, use complete-evidence scope:

```bash
python tools/run_analyze.py --runs-dir runs/dogfood-batchN --out-dir runs/dogfood-batchN-analytics --evidence-scope complete
```

`--evidence-scope all` is the default and preserves legacy behavior: any child folder with `run_log.jsonl` is counted. `--evidence-scope complete` counts only child folders that also contain `validation_report.json` and `revision_decision.json`. Excluded logged folders are summarized in `excluded_runs_total` and `excluded_runs_by_reason`.

This writes:

- `run_metrics.json`: machine-readable metrics for routing, reporting, and future policy work.
- `run_summary.md`: human-readable tables for reviewing acceptance outcomes.
- `run_dashboard.html`: static local dashboard for scanning outcomes, failure reasons, routing candidates, and evidence links.

## Outcome Buckets

The public outcome buckets are mutually exclusive:

- `accepted`: deterministic validation passed and the quality gate accepted the run.
- `review_required`: the quality gate returned `review_required` or `revision_required`.
- `failed`: deterministic validation failed and there is no review or revision quality-gate path.

Detailed failure reasons remain available even when the public bucket is `review_required`. For example, a run can be counted as `review_required` and still report `command_failed:full_test_suite`.

## Key Metrics

Use these fields in `run_metrics.json` first:

- `evidence_scope`: `all` or `complete`.
- `excluded_runs_total`: logged child folders excluded by complete-evidence scope.
- `excluded_runs_by_reason`: missing-artifact reasons for excluded folders, such as `missing_validation_report` or `missing_revision_decision`.
- `runs_total`: number of run folders scanned.
- `outcome_counts`: accepted, review-required, failed, and other counts.
- `accepted_runs_total`: accepted count preserved for existing consumers.
- `accepted_runs_by_execution_host`: accepted count by host, such as `goose` or `codex`.
- `accepted_runs_by_response_source`: accepted count by captured response source.
- `execution_host_counts`: scanned run count by execution host. Missing historical host metadata is counted as `goose`.
- `response_source_counts`: scanned run count by response source. Missing model output source metadata is counted as `unknown`.
- `review_required_runs_total`: public review-required count.
- `failed_runs_total`: public failed count.
- `acceptance_breakdown`: backward-compatible accepted/needs-review/failed breakdown.
- `outcome_breakdown`: public accepted/review-required/failed breakdown by execution host, response source, recipe, validation profile, selected tier, and quality-gate outcome.
- `failure_reasons`: most common deterministic validation and quality-gate reasons.
- `cost_tracking`: provider token and estimated-cost aggregate fields when `model_call_metadata.json` evidence exists.
- `time_tracking`: provider-call and validation-command duration aggregates when explicit duration evidence exists.
- `run_cost_time`: per-run cost/time metadata keyed by run id, including booleans that distinguish missing evidence from zero values.

## Host And Source Metrics

`execution_host` is read from `task_metadata.json`. Older runs that do not have this field are treated as `goose` so existing samples and private ledgers remain valid.

`response_source` is read from `model_output.md` metadata when available. If the metadata is missing, analytics reports `unknown`.

These fields let Workbench compare host outcomes without changing routing feedback keys. `routing_feedback_candidates` still uses only:

```text
recipe | validation_profile | selected_tier | risk | complexity_band
```

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

## Advisory Routing Feedback

`workbench_select_model` can read either a full `run_metrics.json` report or a raw `routing_feedback_candidates` JSON object. The selector writes a `routing_feedback` object into `model_selection.json` with:

- `status`: `not_provided`, `source_missing`, `source_invalid`, `no_candidates`, `no_match`, `insufficient_evidence`, or `advisory`
- `candidate_key`: `recipe|validation_profile|selected_tier|risk|complexity_band`
- `candidate`: matched totals, rates, and top failure reasons when evidence exists
- `policy`: the thresholds used for the advisory
- `recommendation`: `no_change`, `prefer_current_tier`, `consider_escalation`, `require_human_review`, or `collect_more_evidence`

The selector does not mutate `selected_tier`. Synthetic samples should normally return `insufficient_evidence` because the default policy requires at least five runs before producing a real advisory.

## Cost Tracking

Cost tracking is optional provider metadata. Empty or zero cost fields mean no provider cost evidence was found in the scanned run folders. They do not mean the run was free.

Cost fields are populated only when real `model_call_metadata.json` artifacts contain token or cost data.

`model_call_metadata.json` may live directly inside a run folder. The minimum accepted shape is:

```json
{
  "provider": "litellm",
  "tier": "local_coding",
  "model": "provider-model-id",
  "usage_summary": {
    "prompt_tokens": 1000,
    "completion_tokens": 250,
    "total_tokens": 1250,
    "cached_input_tokens": 0,
    "uncached_input_tokens": 1000
  },
  "estimated_cost_usd": 0.00123,
  "pricing_source": "provider_reported",
  "duration_ms": 2400
}
```

Notes:

- `provider`, `tier`, and `model` identify the provider call. `model` may also be read from a completed attempt when attempts are recorded.
- `usage_summary.total_tokens` is enough to count token evidence. Prompt, completion, cached, and uncached token fields improve cost estimates when direct provider cost is unavailable.
- `estimated_cost_usd` should be provider-reported when available. If it is missing, analytics can estimate cost only from real token metadata plus configured pricing data.
- `duration_ms` is optional provider-call time evidence. Analytics also accepts explicit `elapsed_ms`, `latency_ms`, `wall_time_ms`, or their `_seconds` equivalents. Attempt-level duration fields can be summed when top-level duration is absent.
- Missing cost or time fields stay missing in interpretation. They are not treated as free or zero-duration execution.

Validation time is separate from provider-call time. It is summed from explicit `duration_ms` fields in `validation_report.json.commands_run`.

## Reading The Summary

Open `run_summary.md` when you want a quick human review:

- `Workflow KPIs` shows high-level run counts.
- `Acceptance Outcomes` shows the public outcome totals and failure reasons.
- `Public Outcomes By Recipe` shows which recipes are producing accepted or review-required runs.
- `Public Outcomes By Execution Host` shows Goose, Codex, CI, or other host outcomes.
- `Public Outcomes By Response Source` shows captured-output provenance outcomes.
- `Routing Feedback Candidates` shows the future policy input shape.
- `Cost Tracking` states whether provider cost evidence was available.

Open `run_dashboard.html` when you want a single-file visual scan of the same evidence. The dashboard links to standard run artifacts by relative path and does not embed raw model output or provider logs. See `docs/analytics/evidence-dashboard.md` for the dashboard hygiene boundary.
