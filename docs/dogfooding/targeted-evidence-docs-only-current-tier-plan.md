# Targeted Evidence Plan: Low-Risk Docs-Only Current-Tier Routing

Status: completed plan; the fresh isolated batch is summarized in `docs/dogfooding/targeted-docs-only-current-tier-report.md`.

This report names the first targeted evidence batch after Phase 5 closeout. It is public-safe and aggregate-only. Raw evidence remains in ignored `runs/` folders and should not be committed.

## Experiment Question

Can low-risk `docs_only` Goose tasks stay on the current recommended `local_coding` tier when deterministic validation passes exact changed-file policy and the quality gate accepts the run?

This is a routing-policy experiment input, not a policy change. The result should inform a later policy branch only after fresh isolated evidence exists.

## Current Evidence Position

Fresh run count for this pass: 6.

The completed follow-up report records six fresh isolated live Goose runs. This plan remains as the batch design and threshold reference.

Historical public aggregate input from Phase 5 docs-only/profile evidence:

| Evidence source | Complete docs-only runs | Live Goose runs | Deterministic controls | Accepted | Review required | Failed |
|---|---:|---:|---:|---:|---:|---:|
| Phase 5 public reports | 9 | 8 | 1 | 6 | 3 | 0 |

The historical accepted count is useful for selecting the experiment, but it is not enough to mutate routing policy. The new batch must use fresh isolated evidence.

## Target Batch Design

| Field | Planned value |
|---|---|
| Run parent | `runs/targeted-docs-only-current-tier/` |
| Analytics output | `runs/targeted-docs-only-current-tier-analytics/` |
| Host | Goose |
| Response source | Goose |
| Recipe | `workbench-docs-only-acceptance.yaml` |
| Validation profile | `docs_only` |
| Risk | `low` |
| Expected selected tier | `local_coding` |
| Target complete runs | 6 live runs |
| Deterministic controls | 0 in the primary batch |

Each run should be a bounded documentation-only task with one to two Markdown files changed. The run should record the exact changed file list in both `workbench_record_execution` and `workbench_validate_run`.

Analyze only the isolated parent:

```bash
python tools/run_analyze.py --runs-dir runs/targeted-docs-only-current-tier --out-dir runs/targeted-docs-only-current-tier-analytics --evidence-scope complete
```

## Outcome Table

The completed batch produced:

| Outcome | Fresh count |
|---|---:|
| Accepted | 6 |
| Review required | 0 |
| Blocked or failed | 0 |

Do not count a run as accepted unless `validation_report.json` passes, the report is sign-off ready, and `revision_decision.json` records an accepted quality-gate decision.

## Common Failure Reasons To Track

The Phase 5 docs-only evidence used older aggregate reason strings, while the current v0.2 validation and quality-gate artifacts also emit `reason_codes`. Track both forms during the targeted batch so the report stays comparable with Phase 5 while exercising the new reason schema.

| Reason | Meaning for this experiment |
|---|---|
| `docs_only.source_file_blocked` | A source or non-doc file changed under the docs-only policy. |
| `docs_only.claimed_file_without_worktree_diff` | The run claimed a changed file that did not appear in the actual worktree diff. |
| `docs_only.unreported_worktree_diff` | The worktree had an extra diff that was not reported to execution capture or validation. |
| `docs_only.changed_file_evidence_missing` | The run did not provide the required changed-file evidence. |
| `quality_loop.validation_failed` | The quality gate routed failed validation to review instead of acceptance. |
| `artifact_checks:failed:changed_file_policy` | Goose claimed or omitted docs changes that did not exactly match the worktree diff. |
| `validation_overall:failed` | Deterministic validation did not produce sign-off-ready evidence. |
| `validation_not_sign_off_ready` | The run should remain review-required even if the agent response sounded complete. |
| `quality_gate:review_required` | The quality gate did not accept the run. |
| `quality_loop:alternate_model_review` | A policy-level review path was selected; for this low-risk docs-only experiment, this would need investigation. |

## Useful Blocker Explanations

Use concise blocker explanations in the future aggregate report. Examples:

- Claimed docs file had no matching worktree diff, so exact changed-file validation blocked acceptance.
- The changed-file list underreported the actual Markdown diff, so the run required review.
- Deterministic validation did not mark the evidence sign-off ready, so Goose prose could not be treated as acceptance.

## Decision Thresholds

Use the fresh batch only as advisory routing input:

| Fresh result | Recommendation |
|---|---|
| At least 5 complete live runs and at least 80% accepted, with no repeated validation failure outside task-quality issues | Consider a later policy branch that keeps low-risk `docs_only` on the current tier when deterministic validation passes. |
| Repeated `changed_file_policy` failures | Improve run instructions or execution discipline before any routing-policy change. |
| Deterministic validation passes but quality gate still routes low-risk docs-only runs to review | Investigate quality-gate policy behavior before routing changes. |
| Fewer than 5 complete live runs | Collect more evidence; do not draw a policy conclusion. |

## Recommendations

- Keep routing feedback advisory until the completed batch is reviewed in `docs/dogfooding/targeted-docs-only-current-tier-report.md`.
- Do not mutate `model_select.py`, validation profiles, recipes, or quality-gate policy from Phase 5 aggregate evidence alone.
- Keep deterministic controls out of the primary docs-only current-tier batch; use controls only if a separate policy-failure question needs proof.
- Preserve raw run evidence locally under ignored `runs/` and commit only the sanitized aggregate follow-up report.
