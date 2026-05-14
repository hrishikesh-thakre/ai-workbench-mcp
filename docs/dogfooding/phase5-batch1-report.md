# Phase 5 Dogfood Batch 1 Report

Date: 2026-05-14

## Scope

This report summarizes the first isolated local Goose dogfooding batch for the Workbench acceptance loop. Raw evidence remains under ignored `runs/` folders and is not committed.

The clean analytics input was an ignored eight-run batch copy containing only the intended completed runs. An older partial test-fix attempt was excluded from this report because it did not contain a complete quality-gate decision.

## Attribution

| Layer | Value |
|---|---|
| Agent host | Goose |
| Selected tier | `local_coding` |
| Backing model | `unsloth/gemma-4-E4B-it-GGUF:Q4_K_M` |
| Acceptance layer | AI Workbench MCP |

These results should be read as Goose-agent runs backed by the local Gemma model above, with Workbench deciding whether the resulting evidence is accepted, review-required, or failed.

## Aggregate Result

| Metric | Count |
|---|---:|
| Runs analyzed | 8 |
| Accepted | 4 |
| Review required | 4 |
| Failed | 0 |
| Acceptance rate | 0.50 |
| Review-required rate | 0.50 |

## Outcomes By Workflow

| Workflow | Recipe | Recorded validation profile | Accepted | Review Required | Failed | Notes |
|---|---|---|---:|---:|---:|---|
| Docs-only | `workbench-docs-only-acceptance.yaml` | `docs_only` | 2 | 0 | 0 | Both low-risk docs runs passed validation and quality gate. |
| Low-risk coding | `workbench-engineering-acceptance.yaml` | `scaffold` | 2 | 0 | 0 | Both low-risk runs were accepted, but the recorded validation profile was scaffold instead of `low_risk_coding`. |
| Python package maintenance | `workbench-python-package-maintenance.yaml` | `scaffold` | 0 | 2 | 0 | Medium-risk local-tier output triggered alternate-model review. The recorded validation profile was scaffold instead of `python_package_maintenance`. |
| Test fix | `workbench-test-fix-acceptance.yaml` | `test_fix` | 0 | 2 | 0 | Both runs required review; one preserved a deterministic full-test failure reason. |

## Failure And Review Signals

| Signal | Count |
|---|---:|
| `quality_gate:review_required` | 4 |
| `quality_loop:alternate_model_review` | 4 |
| `validation_overall:failed` | 1 |
| `validation_not_sign_off_ready` | 1 |
| `command_failed:full_test_suite` | 1 |

The clean routing signal is that `local_coding` handled low-risk work well in this small batch, but every medium-risk run required review. This is useful directional evidence, not enough for automatic routing-policy mutation.

## Routing Feedback Candidates

| Recipe | Profile | Tier | Risk | Complexity | Accepted | Review Required | Total | Signal |
|---|---|---|---|---|---:|---:|---:|---|
| `workbench-docs-only-acceptance.yaml` | `docs_only` | `local_coding` | low | easy | 2 | 0 | 2 | Keep collecting evidence; early low-risk docs signal is positive. |
| `workbench-engineering-acceptance.yaml` | `scaffold` | `local_coding` | low | easy | 2 | 0 | 2 | Positive low-risk signal, but profile fidelity needs correction before using it for policy. |
| `workbench-python-package-maintenance.yaml` | `scaffold` | `local_coding` | medium | easy | 0 | 2 | 2 | Medium-risk local-tier output should continue to require review. |
| `workbench-test-fix-acceptance.yaml` | `test_fix` | `local_coding` | medium | moderate | 0 | 2 | 2 | Medium-risk test repair needs stronger validation and review. |

## Validation Findings

Two profile-fidelity issues were exposed:

- Low-risk and package-maintenance runs recorded scaffold validation even though model selection recorded the intended focused profiles.
- One test-fix run showed that repository-wide pytest validation can miss the toy fixture's direct test command. The fixture-specific command still failed, while the broader profile could pass without collecting that example test.

Recommended follow-up before routing-policy changes:

- Make focused Goose recipes pass the intended validation profile deterministically in every validation call.
- Strengthen `test_fix` so task-specific test commands are first-class evidence, or add a validation artifact that records the exact user-requested failing test command.
- Keep medium-risk `local_coding` outputs in review-required territory until at least 20 complete dogfood runs show stable candidate groups.

Follow-up status: the focused-validation hardening pass after this report made `workbench_validate_run` fall back to the profile recorded in `model_selection.json` when no explicit profile is provided, and made `test_fix` require a focused `task_test_command`.

## Cost Evidence

No provider token or cost metadata was captured. Empty cost metrics mean no provider cost evidence was available, not free execution.

## Decision

Do not change routing policy from this batch. The useful outcome is the evidence loop itself: Workbench accepted low-risk runs, forced review for medium-risk local-tier runs, preserved deterministic failure reasons, and exposed validation-profile gaps that should be fixed before broader policy experiments.
