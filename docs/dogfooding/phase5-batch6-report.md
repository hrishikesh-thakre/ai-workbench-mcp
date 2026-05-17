# Phase 5 Batch 6 Report

Batch 6 completed the final live Goose volume pass for Phase 5 evidence collection. Raw run folders stayed under ignored `runs/`; this report contains only aggregate, sanitized facts.

## Scope

The batch used an isolated detached worktree from `cf691bf Document Phase 5 Batch 5 validation failures`. Goose was `1.34.1` and used the configured default `gemini_oauth / gemini-3-flash-preview` runtime with no provider or model overrides.

The run parent was analyzed with:

```bash
python tools/run_analyze.py --runs-dir runs/dogfood-batch6 --out-dir runs/dogfood-batch6-analytics --evidence-scope complete
```

All six counted runs were live Goose runs. No deterministic controls were used in Batch 6, and no routing policy was changed.

## Run Mix

| Workflow | Recipe | Profile | Outcome |
|---|---|---|---|
| Docs-only closeout wording note | `workbench-docs-only-acceptance.yaml` | `docs_only` | accepted |
| Low-risk analytics regression test note | `workbench-engineering-acceptance.yaml` | `low_risk_coding` | accepted |
| Low-risk package metadata keyword | `workbench-python-package-maintenance.yaml` | `python_package_maintenance` | accepted |
| Medium-risk package metadata classifier | `workbench-python-package-maintenance.yaml` | `python_package_maintenance` | review_required |
| Intentionally broken fixture repair | `workbench-test-fix-acceptance.yaml` | `fixture_repair_proof` | accepted |
| Seeded complete-scope test repair | `workbench-test-fix-acceptance.yaml` | `test_fix` | accepted |

The seeded `test_fix` run started from an isolated local seed commit that intentionally made `missing_complete_evidence` require an extra artifact. Goose repaired the seeded failure and passed the focused command `python -m pytest tests/test_run_analyze.py -q -p no:cacheprovider`. The repair stayed local to the proof worktree and was not promoted into the main branch.

Tracked diffs in the isolated worktree were restored between runs after evidence was recorded, keeping each run's exact changed-file evidence independent.

## Analytics Summary

Workbench analytics reported:

- `evidence_scope`: `complete`
- `runs_total`: `6`
- `excluded_runs_total`: `0`
- `outcome_counts`: `accepted=5`, `review_required=1`
- `quality_gate_outcomes`: `accepted=5`, `review_required=1`
- `execution_host_counts`: `goose=6`
- `response_source_counts`: `goose=6`
- `accepted_runs_total`: `5`
- `review_required_runs_total`: `1`
- `failed_runs_total`: `0`
- `acceptance_rate`: `0.83`

Accepted runs by validation profile:

| Profile | Accepted |
|---|---:|
| `docs_only` | 1 |
| `low_risk_coding` | 1 |
| `python_package_maintenance` | 1 |
| `fixture_repair_proof` | 1 |
| `test_fix` | 1 |

Public outcomes by recipe:

| Recipe | Accepted | Review Required | Failed |
|---|---:|---:|---:|
| `workbench-docs-only-acceptance.yaml` | 1 | 0 | 0 |
| `workbench-engineering-acceptance.yaml` | 1 | 0 | 0 |
| `workbench-python-package-maintenance.yaml` | 1 | 1 | 0 |
| `workbench-test-fix-acceptance.yaml` | 2 | 0 | 0 |

## Validation Notes

- The docs-only, low-risk coding, low-risk package, fixture repair, and seeded test-fix runs passed deterministic validation and the quality gate.
- The medium-risk package-maintenance run passed deterministic validation but the quality gate returned `review_required` with `quality_loop:alternate_model_review`.
- The fixture repair run first observed the focused unittest failure, changed only `examples/tiny-python-fix/calculator.py`, then passed the focused unittest command.
- The seeded `test_fix` run first observed the focused pytest failure, then passed `python -m pytest tests/test_run_analyze.py -q -p no:cacheprovider` after repair. It produced accepted evidence for the `test_fix` lifecycle. The live repair also added a same-file tool-smoke skip while fixing the seeded artifact requirement; that extra behavior was preserved as evidence only and not promoted.

## Interpretation

Batch 6 adds the final live Goose volume needed for Phase 5 closeout. It covers all targeted focused profiles in one complete-scope batch, confirms zero analytics exclusions for complete lifecycle evidence, and repeats the expected medium-risk local-coding review-required signal.

Do not mutate routing policy from Batch 6 alone. Its value is as the final evidence-collection batch feeding the Phase 5 closeout decision.
