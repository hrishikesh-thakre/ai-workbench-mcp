# Phase 5 Batch 4 Report

Batch 4 exercised review-required evidence and complete-scope exclusion hygiene. Raw run folders stayed under ignored `runs/`; this report contains only aggregate, sanitized facts.

## Scope

The batch used an isolated detached worktree from `228e0bc Document Phase 5 Batch 3 dogfood run`. Goose was `1.34.1` and used the configured default `gemini_oauth / gemini-3-flash-preview` runtime with no provider or model overrides.

The run parent was analyzed with:

```bash
python tools/run_analyze.py --runs-dir runs/dogfood-batch4 --out-dir runs/dogfood-batch4-analytics --evidence-scope complete
```

## Run Mix

| Workflow | Recipe | Profile | Outcome |
|---|---|---|---|
| Tool-smoke connectivity | `workbench-mcp-tool-smoke.yaml` | n/a | excluded from complete scope |
| Docs-only exclusion wording control | `workbench-docs-only-acceptance.yaml` | `docs_only` | accepted |
| Medium-risk package metadata control | `workbench-python-package-maintenance.yaml` | `python_package_maintenance` | review_required |

The tool-smoke run intentionally stopped after `workbench_open_run` and `workbench_select_model`, so it had `run_log.jsonl` but no validation or quality-gate artifacts. The docs-only and package-maintenance runs both produced complete lifecycle evidence. A deterministic changed-file negative-control fallback was not needed because the medium-risk package-maintenance run produced the required review-required outcome.

Tracked diffs in the isolated worktree were restored between complete runs after evidence was recorded, keeping each run's exact changed-file evidence independent.

## Analytics Summary

Workbench analytics reported:

- `evidence_scope`: `complete`
- `runs_total`: `2`
- `excluded_runs_total`: `1`
- `excluded_runs_by_reason`: `missing_validation_report=1`, `missing_revision_decision=1`
- `outcome_counts`: `accepted=1`, `review_required=1`
- `quality_gate_outcomes`: `accepted=1`, `review_required=1`
- `accepted_runs_by_execution_host`: `goose=1`
- `accepted_runs_by_response_source`: `goose=1`

Public outcomes by recipe:

| Recipe | Accepted | Review Required | Failed |
|---|---:|---:|---:|
| `workbench-docs-only-acceptance.yaml` | 1 | 0 | 0 |
| `workbench-python-package-maintenance.yaml` | 0 | 1 | 0 |

Routing feedback candidates were generated for the two complete recipe/profile buckets. Each candidate still has only one Batch 4 observation, so this remains evidence collection rather than a routing-policy signal.

## Validation Notes

- The docs-only run accepted a single Markdown documentation change and passed the `docs_only` changed-file policy.
- The package-maintenance run passed deterministic validation, including the package metadata checks, but the quality gate returned `review_required`.
- The review-required reasons were `quality_gate:review_required` and `quality_loop:alternate_model_review`.
- The excluded smoke folder confirmed that `--evidence-scope complete` removes logged folders missing lifecycle artifacts from acceptance metrics.

## Interpretation

Batch 4 confirms that dogfood batches can keep connectivity smoke beside acceptance runs without polluting complete-scope routing feedback. It also adds a clean review-required Goose example where deterministic validation passed but policy required manual review because a medium-risk task used the local-coding tier.

Do not mutate routing policy from Batch 4. The sample remains small, and the review-required outcome is useful as quality-gate evidence rather than proof of a stable routing pattern. The next pass should continue increasing complete-run volume and add more deterministic validation-failure examples.
