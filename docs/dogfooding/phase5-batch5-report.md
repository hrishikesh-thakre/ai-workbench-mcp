# Phase 5 Batch 5 Report

Batch 5 exercised deterministic validation-failure evidence. Raw run folders stayed under ignored `runs/`; this report contains only aggregate, sanitized facts.

## Scope

The batch used an isolated detached worktree from `adc717f Document Phase 5 Batch 4 review evidence`. Goose was `1.34.1` and used the configured default `gemini_oauth / gemini-3-flash-preview` runtime with no provider or model overrides for the accepted control.

The run parent was analyzed with:

```bash
python tools/run_analyze.py --runs-dir runs/dogfood-batch5 --out-dir runs/dogfood-batch5-analytics --evidence-scope complete
```

## Run Mix

| Workflow | Recipe | Profile | Host / Source | Outcome |
|---|---|---|---|---|
| Docs-only complete-scope wording control | `workbench-docs-only-acceptance.yaml` | `docs_only` | `goose` / `goose` | accepted |
| Underreported docs diff negative control | `workbench-docs-only-acceptance.yaml` | `docs_only` | `ci` / `deterministic_control` | review_required |
| Focused test command negative control | `workbench-test-fix-acceptance.yaml` | `test_fix` | `ci` / `deterministic_control` | review_required |

The docs-only control was a live Goose run. The two negative controls used Workbench core lifecycle calls to generate the standard artifacts: run setup, model selection, execution capture, deterministic validation, and quality gate. No validation or quality-gate artifacts were edited manually.

Tracked diffs in the isolated worktree were restored between runs after evidence was recorded, keeping each run's exact changed-file evidence independent.

## Analytics Summary

Workbench analytics reported:

- `evidence_scope`: `complete`
- `runs_total`: `3`
- `excluded_runs_total`: `0`
- `outcome_counts`: `accepted=1`, `review_required=2`
- `quality_gate_outcomes`: `accepted=1`, `review_required=2`
- `execution_host_counts`: `goose=1`, `ci=2`
- `response_source_counts`: `goose=1`, `deterministic_control=2`

Failure reasons:

| Reason | Count |
|---|---:|
| `validation_overall:failed` | 2 |
| `validation_not_sign_off_ready` | 2 |
| `quality_gate:review_required` | 2 |
| `quality_loop:alternate_model_review` | 2 |
| `artifact_checks:failed:changed_file_policy` | 1 |
| `command_failed:task_test_command` | 1 |
| `command_failed:full_test_suite` | 1 |

Public outcomes by recipe:

| Recipe | Accepted | Review Required | Failed |
|---|---:|---:|---:|
| `workbench-docs-only-acceptance.yaml` | 1 | 1 | 0 |
| `workbench-test-fix-acceptance.yaml` | 0 | 1 | 0 |

## Validation Notes

- The accepted docs-only control passed deterministic validation and the quality gate.
- The changed-file policy negative control intentionally created two Markdown diffs but reported only one changed file. Validation failed with `artifact_checks:failed:changed_file_policy` and the quality gate routed the failed validation to review.
- The focused test command negative control reported its tracked diff exactly, so `changed_file_policy` passed. Validation failed because the intentionally broken fixture command failed, producing `command_failed:task_test_command`; the broader full suite also failed in that run.
- Analytics buckets these failed-validation runs as `review_required` because the quality gate returned `review_required` for failed validation. The detailed validation failure reasons remain visible in `failure_reasons` and routing feedback candidates.

## Interpretation

Batch 5 fills the deterministic validation-failure gap left after Batch 4. It shows that complete-scope analytics preserves specific validation reasons even when the public outcome bucket is review-required.

Do not mutate routing policy from Batch 5. The deterministic controls are policy and analytics evidence, not live model capability evidence. The next pass should increase live Goose complete-run volume, especially low-risk coding and real test-fix repairs, while keeping deterministic controls clearly labeled when used.
