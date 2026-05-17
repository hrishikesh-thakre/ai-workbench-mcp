# Phase 5 Final Report

Phase 5 evidence collection is complete for the current Goose-first acceptance and audit loop. Raw evidence remained in ignored `runs/` folders; committed reports contain only aggregate, sanitized facts.

## Scope

Phase 5 covered Batches 1 through 6, including early local Gemma Goose runs, later `gemini_oauth / gemini-3-flash-preview` Goose runs, Codex proof evidence outside the dogfood batch totals, complete-scope analytics hardening, review-required examples, deterministic validation-failure controls, and the final live Goose volume batch.

This closeout does not change routing policy. It decides whether the evidence is sufficient to move into bounded routing-policy experiments.

## Evidence Totals

| Batch | Complete Evidence Runs | Live Goose Runs | Deterministic Controls | Accepted | Review Required | Failed |
|---|---:|---:|---:|---:|---:|---:|
| Batch 1 | 8 | 8 | 0 | 4 | 4 | 0 |
| Batch 2 Stage A | 4 | 4 | 0 | 1 | 3 | 0 |
| Batch 2 Stage B | 4 | 4 | 0 | 0 | 4 | 0 |
| Batch 3 | 4 | 4 | 0 | 4 | 0 | 0 |
| Batch 4 | 2 | 2 | 0 | 1 | 1 | 0 |
| Batch 5 | 3 | 1 | 2 | 1 | 2 | 0 |
| Batch 6 | 6 | 6 | 0 | 5 | 1 | 0 |
| Total | 31 | 29 | 2 | 16 | 15 | 0 |

The Phase 5 target was at least 20 real Goose runs with complete evidence. The final set contains 31 complete runs: 29 live Goose runs, plus 2 deterministic controls used only for validation and analytics hygiene.

## Coverage

Recipes represented:

- `workbench-docs-only-acceptance.yaml`
- `workbench-engineering-acceptance.yaml`
- `workbench-python-package-maintenance.yaml`
- `workbench-test-fix-acceptance.yaml`

Profiles represented after focused-profile hardening:

- `docs_only`
- `low_risk_coding`
- `python_package_maintenance`
- `test_fix`
- `fixture_repair_proof`

Early Batch 1 evidence also exposed historical profile-fidelity issues where some runs recorded `scaffold`; that gap was fixed before later batches and should not be used as a current routing signal.

## Repeated Signals

The strongest repeated signals are:

- Medium-risk `local_coding` work repeatedly routes to `review_required` through `quality_loop:alternate_model_review`.
- Low-risk complete Goose runs under the later focused profiles can become accepted when deterministic validation and exact changed-file policy pass.
- No-op and underreported diffs are blocked by `artifact_checks:failed:changed_file_policy`.
- Focused test repairs require explicit `task_test_command` evidence; failing focused commands surface as `command_failed:task_test_command`.
- `--evidence-scope complete` prevents incomplete tool-smoke or lifecycle-partial folders from polluting routing feedback candidates.

Batch 5's two deterministic controls are policy evidence, not model capability evidence. They prove failure reasons and analytics buckets behave correctly when Workbench validation fails.

## Routing Feedback Interpretation

The evidence is now sufficient to plan bounded routing-policy experiments, but not to broadly auto-route or remove quality gates.

Reasonable next experiments:

- Keep medium-risk `local_coding` outputs behind review or alternate-model review by policy.
- Test whether low-risk `docs_only`, `low_risk_coding`, `fixture_repair_proof`, and simple `test_fix` tasks can stay on the current Goose default when exact changed-file and focused-command validation pass.
- Use routing feedback candidates as advisory input first, then compare a small policy branch against new dogfood runs before changing defaults.

Do not use deterministic controls to justify live model capability routing. Use them only to validate Workbench failure handling, analytics, and public outcome buckets.

## Closeout Decision

Phase 5 evidence collection is complete. The exit criteria are met:

- At least 20 real Goose runs have complete evidence: 29 live Goose runs are counted.
- Outcome buckets include accepted and review-required examples: 16 accepted and 15 review-required outcomes are recorded.
- Repeated failure reasons are visible in analytics, including changed-file policy failures, focused test command failures, and alternate-model review triggers.
- Routing feedback candidates show stable enough patterns to propose bounded policy experiments.

The next phase should be routing-policy experiment planning. It should use new isolated evidence batches to compare candidate policy changes, and it should keep Workbench acceptance based on deterministic validation plus quality-gate decisions.
