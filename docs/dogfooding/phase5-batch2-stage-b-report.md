# Phase 5 Dogfood Batch 2 Stage B Report

Generated: 2026-05-15

Stage B collected four additional Goose-first dogfood runs after focused-profile exact-diff hardening. Raw evidence stayed in an ignored `runs/dogfood-batch2-stage-b/` ledger in the temporary worktree; this report records only sanitized aggregate facts.

## Scope

- Workflows: docs-only, low-risk coding, package maintenance, and seeded test-fix.
- Profiles: `docs_only`, `low_risk_coding`, `python_package_maintenance`, and `test_fix`.
- Execution host recorded by Workbench evidence: `goose`.
- Selected provider/model recorded by Workbench evidence: `goose` / `unsloth/gemma-4-E4B-it-GGUF:Q4_K_M`.
- Routing policy changes: none. This batch is evidence only.

## Outcome Summary

| Outcome | Count |
|---|---:|
| Accepted | 0 |
| Review required | 4 |
| Failed | 0 |

Workbench analytics reported:

- Runs total: 4
- Workflow sign-off pass rate: 0.0
- Review-required rate: 1.0
- Quality-gate outcomes: `review_required`: 4
- Validation failure reason present in all runs: `artifact_checks:failed:changed_file_policy`

## Run Summary

| Run | Profile | Recipe | Public outcome | Primary signal |
|---|---|---|---|---|
| `dogfood-20260515-docs-exact-diff-note` | `docs_only` | `workbench-docs-only-acceptance.yaml` | Review required | Claimed docs file had no worktree diff. |
| `dogfood-20260515-low-risk-diff-test` | `low_risk_coding` | `workbench-engineering-acceptance.yaml` | Review required | Claimed docs and test files had no worktree diff. |
| `dogfood-20260515-package-publish-prereq-test` | `python_package_maintenance` | `workbench-python-package-maintenance.yaml` | Review required | Claimed publishing docs and package hygiene test files had no worktree diff. |
| `dogfood-20260515-seeded-exact-diff-test-fix` | `test_fix` | `workbench-test-fix-acceptance.yaml` | Review required | Seeded test command failed and exact-diff validation found an unreported seeded test file. |

## Exact-Diff Signals

- No-op or claimed-without-diff blocked: 3 runs.
- Underreported worktree diff blocked: 1 run.
- Exact changed-file evidence accepted: 0 runs.
- Focused test failure also surfaced: 1 run.

The seeded test-fix run produced validation evidence through Goose, but Goose stopped after failed validation instead of invoking the quality gate. The deterministic Workbench quality-loop CLI was run against the same canonical artifacts to write `revision_decision.json` before batch analytics. The final outcome remained `review_required`.

## Interpretation

Stage B confirms that focused profiles now block claimed changes that do not match actual worktree evidence. The most important regression from earlier dogfooding is closed: a model response that claims files were changed cannot become accepted evidence unless the reported file list is non-empty and matches the real worktree diff.

This batch does not justify routing-policy mutation by itself. It supports the next dogfood step: collect provider-backed or stronger-model runs that attempt the same tasks and compare whether exact changed-file evidence is produced rather than merely claimed.
