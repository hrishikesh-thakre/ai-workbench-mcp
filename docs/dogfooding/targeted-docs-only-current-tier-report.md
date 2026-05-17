# Targeted Docs-Only Current-Tier Report

Status: complete targeted evidence batch.

This report summarizes the first bounded routing-policy experiment batch after Phase 5 closeout. It is public-safe and aggregate-only. Raw evidence remains in ignored `runs/` folders and should not be committed.

## Experiment Question

Can low-risk `docs_only` Goose tasks stay on the current recommended `local_coding` tier when deterministic validation passes exact changed-file policy and the quality gate accepts the run?

This report is advisory routing input, not a routing-policy change. It does not mutate `model_select.py`, validation profiles, recipes, quality-gate policy, or routing thresholds.

## Batch Design

| Field | Actual value |
|---|---|
| Run parent | `runs/targeted-docs-only-current-tier/` |
| Analytics output | `runs/targeted-docs-only-current-tier-analytics/` |
| Host | Goose |
| Response source | Goose |
| Recipe | `workbench-docs-only-acceptance.yaml` |
| Validation profile | `docs_only` |
| Risk | `low` |
| Selected tier | `local_coding` |
| Complete live runs | 6 |
| Deterministic controls | 0 |

Each run changed one Markdown file, recorded the exact changed file list in execution capture and validation, then restored the tracked docs edit before the next isolated run. Raw run evidence and analytics artifacts stayed local under ignored `runs/`.

The isolated parent was analyzed with:

```bash
python tools/run_analyze.py --runs-dir runs/targeted-docs-only-current-tier --out-dir runs/targeted-docs-only-current-tier-analytics --evidence-scope complete
```

## Outcome Summary

| Outcome | Fresh count |
|---|---:|
| Accepted | 6 |
| Review required | 0 |
| Blocked or failed | 0 |

Workbench analytics reported:

| Metric | Value |
|---|---:|
| `runs_total` | 6 |
| `excluded_runs_total` | 0 |
| `accepted_runs_total` | 6 |
| `review_required_runs_total` | 0 |
| `failed_runs_total` | 0 |
| `acceptance_rate` | 1.0 |

All six runs had deterministic validation `passed`, `sign_off_ready=true`, and quality gate `final_status="accepted"`.

## Routing Feedback Candidate

Final isolated analytics produced one candidate:

| Recipe | Profile | Tier | Risk | Complexity | Accepted | Review Required | Failed | Total | Acceptance Rate |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| `workbench-docs-only-acceptance.yaml` | `docs_only` | `local_coding` | `low` | `easy` | 6 | 0 | 0 | 6 | 1.0 |

Per-run selector feedback during collection remained advisory. The first run saw `source_missing` because no prior report existed; later runs saw `no_candidates` / `collect_more_evidence` until the isolated batch was analyzed. That is expected and does not change the selected tier.

## Reason Codes

Observed accepted reason codes:

| Source | Reason code | Count |
|---|---|---:|
| Validation | `docs_only.accepted` | 6 |
| Quality gate | `quality_gate.accepted` | 6 |

No blocker or review reason codes were observed. In particular, this batch did not repeat `docs_only.claimed_file_without_worktree_diff`, `docs_only.unreported_worktree_diff`, `docs_only.changed_file_evidence_missing`, or `quality_loop:alternate_model_review`.

## Threshold Result

The planned threshold was at least five complete live runs and at least 80% accepted, with no repeated validation failure outside task-quality issues.

Result: threshold met. The fresh isolated batch has six complete live runs, 100% accepted, and no repeated validation or quality-gate failures.

Recommendation: use `docs/routing/docs-only-current-tier-policy-design.md` as the design boundary for a later policy branch that keeps low-risk `docs_only` work on the current tier when deterministic validation passes exact changed-file policy and the quality gate accepts. Keep the change advisory until that branch is explicitly implemented and verified.

## Boundaries

- Do not commit raw `runs/` evidence, provider logs, model output bodies, or local paths.
- Do not treat this batch as a provider benchmark.
- Do not broaden the result to medium-risk work, code changes, `test_fix`, or security/privacy-sensitive changes.
- Do not change routing defaults from this report alone; use it to justify the next bounded policy branch.
