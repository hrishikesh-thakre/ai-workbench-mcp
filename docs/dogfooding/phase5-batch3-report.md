# Phase 5 Batch 3 Report

Batch 3 exercised the newly added complete-evidence analytics scope against a small live Goose dogfood set. Raw run folders stayed under ignored `runs/`; this report contains only aggregate, sanitized facts.

## Scope

The batch used an isolated detached worktree from `cec3eb9 Add complete evidence analytics scope`. Goose was `1.34.1` and used the configured default `gemini_oauth / gemini-3-flash-preview` runtime with no provider or model overrides.

The run parent was analyzed with:

```bash
python tools/run_analyze.py --runs-dir runs/dogfood-batch3 --out-dir runs/dogfood-batch3-analytics --evidence-scope complete
```

## Run Mix

| Workflow | Recipe | Profile | Outcome |
|---|---|---|---|
| Docs-only analytics dashboard note | `workbench-docs-only-acceptance.yaml` | `docs_only` | accepted |
| Low-risk analytics dashboard rendering change | `workbench-engineering-acceptance.yaml` | `low_risk_coding` | accepted |
| Package metadata maintenance | `workbench-python-package-maintenance.yaml` | `python_package_maintenance` | accepted |
| Seeded exclusion-reason regression repair | `workbench-test-fix-acceptance.yaml` | `test_fix` | accepted |

The test-fix run started from an isolated local baseline commit that added a failing regression test. Goose repaired the production helper with a minimal source change, passed the focused command, and then passed the full `test_fix` validation profile.

## Analytics Summary

Workbench analytics reported:

- `evidence_scope`: `complete`
- `runs_total`: `4`
- `excluded_runs_total`: `0`
- `outcome_counts`: `accepted=4`
- `quality_gate_outcomes`: `accepted=4`
- `accepted_runs_by_execution_host`: `goose=4`
- `accepted_runs_by_response_source`: `goose=4`
- `accepted_runs_by_selected_tier`: `local_coding=4`

Accepted runs by validation profile:

| Profile | Accepted |
|---|---:|
| `docs_only` | 1 |
| `low_risk_coding` | 1 |
| `python_package_maintenance` | 1 |
| `test_fix` | 1 |

Routing feedback candidates were generated for all four recipe/profile buckets. Each candidate has only one run, so this is directional evidence, not enough volume for routing-policy changes.

## Validation Notes

- The docs-only run accepted a single Markdown documentation change.
- The low-risk coding run passed `pytest_collection`, `full_test_suite`, and `workbench_tool_help_smoke`.
- The package-maintenance run passed package metadata checks, import smoke, and the full test suite.
- The test-fix run first observed the focused failing command, then passed `python -m pytest tests/test_run_analyze.py -q -p no:cacheprovider` after repair and passed the full `test_fix` profile.

## Interpretation

This batch confirms that complete-scope analytics can summarize a mixed workflow batch without relying on raw `runs/` promotion. It also shows that the current configured Goose runtime can produce accepted evidence across four low-risk local-coding routes.

Do not mutate routing policy from Batch 3. The sample is still small, all runs are low-risk, and every candidate has only one observation. Use it as clean Batch 3 evidence and continue toward the 20-50 complete-run Phase 5 target before proposing policy experiments.
