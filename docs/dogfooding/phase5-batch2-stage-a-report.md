# Phase 5 Dogfood Batch 2 Stage A Report

Batch label: 2026-05-14

## Scope

This report summarizes a four-run Goose dogfooding batch after the focused-validation hardening work. Raw evidence remains under ignored local `runs/` folders and is not committed.

The batch used one run per workflow:

- docs-only
- low-risk coding
- Python package maintenance
- seeded test fix

All four runs had complete Workbench evidence before analytics were run. No PyPI upload, MCP Registry submission, GitHub mutation, or routing-policy change was performed.

## Attribution

| Layer | Value |
|---|---|
| Agent host | Goose |
| Selected tier | `local_coding` |
| Evidence-captured provider | `goose` |
| Evidence-captured model | `unsloth/gemma-4-E4B-it-GGUF:Q4_K_M` |
| Acceptance layer | AI Workbench MCP |

These results should be read as Goose-agent runs with Workbench deciding whether the resulting evidence is accepted or review-required. MCP connects Goose to the Workbench server; it does not decide correctness.

## Evidence Completeness

Each completed run contained the standard evidence set:

- `task_metadata.json`
- `final_prompt.md`
- `model_selection.json`
- `model_output.md`
- `validation_report.json`
- `revision_decision.json`
- `run_log.jsonl`

The seeded test-fix fixture was created only in the isolated dogfood worktree and was not added to the main repository.

## Aggregate Result

| Metric | Count |
|---|---:|
| Runs analyzed | 4 |
| Accepted | 1 |
| Review required | 3 |
| Failed | 0 |
| Acceptance rate | 0.25 |
| Review-required rate | 0.75 |
| Average confidence | 0.66 |
| Response captured | 4 |

## Outcomes By Workflow

| Workflow | Recipe | Validation profile | Accepted | Review Required | Failed | Notes |
|---|---|---|---:|---:|---:|---|
| Docs-only | `workbench-docs-only-acceptance.yaml` | `docs_only` | 0 | 1 | 0 | Validation failed because the changed-file policy did not find the claimed docs edit in the actual diff. |
| Low-risk coding | `workbench-engineering-acceptance.yaml` | `low_risk_coding` | 1 | 0 | 0 | Validation passed and the quality gate accepted the run. |
| Python package maintenance | `workbench-python-package-maintenance.yaml` | `python_package_maintenance` | 0 | 1 | 0 | Validation passed, but medium-risk local-tier output required alternate-model review. |
| Seeded test fix | `workbench-test-fix-acceptance.yaml` | `test_fix` | 0 | 1 | 0 | Validation failed because the focused `task_test_command` and full suite failed. |

## Failure And Review Signals

| Signal | Count |
|---|---:|
| `quality_gate:review_required` | 3 |
| `quality_loop:alternate_model_review` | 3 |
| `validation_overall:failed` | 2 |
| `validation_not_sign_off_ready` | 2 |
| `artifact_checks:failed:changed_file_policy` | 1 |
| `command_failed:task_test_command` | 1 |
| `command_failed:full_test_suite` | 1 |

The strongest signal is that Workbench preserved deterministic failure reasons while still routing non-accepted runs into review-required outcomes instead of treating Goose prose as sufficient acceptance.

## Routing Feedback Candidates

| Recipe | Profile | Tier | Risk | Complexity | Accepted | Review Required | Total | Signal |
|---|---|---|---|---|---:|---:|---:|---|
| `workbench-docs-only-acceptance.yaml` | `docs_only` | `local_coding` | low | easy | 0 | 1 | 1 | Keep collecting evidence; this run shows changed-file enforcement catching a no-op outcome. |
| `workbench-engineering-acceptance.yaml` | `low_risk_coding` | `local_coding` | low | easy | 1 | 0 | 1 | Positive low-risk signal under the focused profile. |
| `workbench-python-package-maintenance.yaml` | `python_package_maintenance` | `local_coding` | medium | easy | 0 | 1 | 1 | Medium-risk local-tier output should continue to require review. |
| `workbench-test-fix-acceptance.yaml` | `test_fix` | `local_coding` | medium | easy | 0 | 1 | 1 | Focused test-fix evidence correctly preserved failed task-test and full-suite commands. |

## Routing Matrix

| Tier | Risk | Complexity | Passed | Needs Review | Failed | Total | Pass Rate |
|---|---|---|---:|---:|---:|---:|---:|
| `local_coding` | low | easy | 1 | 1 | 0 | 2 | 0.50 |
| `local_coding` | medium | easy | 0 | 2 | 0 | 2 | 0.00 |

## Decision

Do not change routing policy from this Stage A batch. The useful outcome is confirmation that focused profiles are recorded, complete evidence is available for all four workflows, and review-required outcomes preserve why validation or quality gates blocked acceptance.

Stage B should expand only after reviewing whether to tighten low-risk changed-file evidence and whether medium-risk local-tier work should continue to require alternate-model review by default.
