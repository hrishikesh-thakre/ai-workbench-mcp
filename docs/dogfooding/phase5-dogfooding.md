# Phase 5 Dogfooding Protocol

Phase 5 is about proving that Workbench analytics can improve routing decisions from real accepted artifacts. Do this with local Goose runs first, then commit only sanitized examples when they are useful as public documentation.

## Goal

Collect 20-50 real Goose acceptance runs with complete Workbench evidence:

- accepted runs
- review-required or revision-required runs
- deterministic validation failures
- enough variation across recipe, validation profile, selected tier, risk, and complexity band to make `routing_feedback_candidates` meaningful

## Task Mix

Start with a balanced set:

| Workflow | Recipe | Profile |
|---|---|---|
| Documentation accuracy or docs-only edits | `workbench-docs-only-acceptance.yaml` | `docs_only` |
| Low-risk implementation | `workbench-engineering-acceptance.yaml` | `low_risk_coding` |
| Python package maintenance | `workbench-python-package-maintenance.yaml` | `python_package_maintenance` |
| Failing test repair | `workbench-test-fix-acceptance.yaml` | `test_fix` |
| Intentionally broken fixture repair proof | `workbench-test-fix-acceptance.yaml` | `fixture_repair_proof` |

Use real tasks, but keep them bounded. Avoid tasks that require private services, credentials, or broad product rewrites.

## Run Naming

Keep dogfood evidence under ignored local `runs/` folders:

```text
runs/dogfood-batchN/
  dogfood-YYYYMMDD-<short-task-slug>/
```

The committed repo should contain only sanitized examples under `examples/sample-runs/`.

## Evidence Rules

Every dogfood run should contain the standard evidence artifacts:

- `task_metadata.json`
- `final_prompt.md`
- `model_selection.json`
- `model_output.md`
- `validation_report.json`
- `revision_decision.json`
- `run_log.jsonl`

A run is accepted only when deterministic validation passed and the quality gate returned `accepted`. Goose prose by itself is not acceptance evidence.

Focused change profiles require non-empty changed-file evidence that exactly matches the current worktree diff. The agent should pass the same exact file list to `workbench_record_execution(files_touched=...)` and `workbench_validate_run(changed_files=...)`; no-op or underreported diffs should become review-blocking validation failures. Artifact-only smoke profiles such as `scaffold` are not change-producing sign-off profiles.

For `test_fix` runs, pass an exact focused Python pytest or unittest command through the recipe's `task_test_command` parameter. The `test_fix` profile treats that focused command as required evidence before broader profile-level validation. Use `fixture_repair_proof` instead when the proof target is an intentionally broken demo fixture and the Workbench repo's self-tests intentionally assert that the checked-in fixture remains broken.

## Outcome Buckets

Use the public analytics buckets:

- `accepted`: validation passed and quality gate accepted
- `review_required`: quality gate returned `review_required` or `revision_required`
- `failed`: deterministic validation failed with no review or revision quality-gate path

Preserve detailed failure reasons such as `command_failed:full_test_suite` even when the public bucket is `review_required`.

## Analytics Command

After collecting a batch, run:

```bash
python tools/run_analyze.py --runs-dir runs/dogfood-batchN --out-dir runs/dogfood-batchN-analytics --evidence-scope complete
```

Use `--evidence-scope complete` for dogfood batches so routing feedback is generated only from folders with `run_log.jsonl`, `validation_report.json`, and `revision_decision.json`. Connectivity or tool-smoke runs can live beside acceptance runs in the same parent, but routing feedback should come from complete lifecycle evidence only.

Do not analyze the whole `runs/` directory for dogfooding reports. Local smoke, scaffold, abandoned, and one-off outputs can pollute the aggregate.

For the committed synthetic samples, run:

```bash
python tools/run_analyze.py --runs-dir examples/sample-runs --out-dir runs/sample-run-analytics
```

Review `run_metrics.json` and `run_summary.md` with `docs/analytics/acceptance-analytics.md` open.

## Routing Feedback Review

Use `routing_feedback_candidates` to identify candidate policy changes. Review each candidate by:

- recipe
- validation profile
- selected tier
- risk
- complexity band
- acceptance rate
- review rate
- failure rate
- top failure reasons

Do not wire candidates into `model_select.py` until enough real runs exist to justify the rule. Synthetic sample runs can verify report shape, but they should not drive routing policy.

In the current advisory loop, `workbench_select_model` may read `routing_feedback_candidates` and persist a `routing_feedback` advisory. That advisory can recommend collecting more evidence, keeping the current tier, escalating, or requiring human review, but it does not change the selected tier.

## Batch 1 Report

The first isolated Goose dogfood batch is summarized in `docs/dogfooding/phase5-batch1-report.md`. It contains only aggregate sanitized facts; raw run folders remain ignored under `runs/`.

## Batch 2 Reports

Batch 2 is summarized in two sanitized reports:

- `docs/dogfooding/phase5-batch2-stage-a-report.md`: four post-hardening Goose runs across the focused workflows, with one accepted outcome and three review-required outcomes.
- `docs/dogfooding/phase5-batch2-stage-b-report.md`: four exact-diff hardening runs after non-empty, exact changed-file evidence became required, with all four outcomes review-required.

Stage B is evidence only. It confirms that focused profiles block no-op or underreported changed-file claims, but it does not justify routing-policy mutation by itself.

## Sanitized Samples

Only promote a dogfood run into `examples/sample-runs/` when it teaches a public behavior. Before committing a sample, remove:

- local machine paths
- provider secrets
- private target-repo names
- raw provider logs
- real cost values unless they are intentionally public provider metadata

Keep cost tracking optional. Empty or zero cost metrics mean no provider cost evidence was captured, not free execution.

## Exit Criteria

Phase 5 dogfooding is ready to feed routing-policy work when:

- at least 20 real runs have complete evidence
- outcome buckets include accepted and review-required examples
- repeated failure reasons are visible in analytics
- routing feedback candidates show stable enough patterns to propose a bounded policy experiment
