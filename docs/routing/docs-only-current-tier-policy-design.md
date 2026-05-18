# Docs-Only Current-Tier Policy Design

Status: implemented as advisory selector behavior; routing defaults are unchanged.

This document defines the smallest routing-policy candidate supported by the targeted docs-only evidence batch. It is intentionally narrow so implementation can be reviewed without broadening scope again.

## Candidate Policy

Name: `docs_only_current_tier_when_accepted`

Policy question: when low-risk docs-only work already selects `local_coding`, can Workbench treat the current tier as supported by evidence when validation and the quality gate both accept?

Minimum eligible route bucket:

| Field | Required value |
|---|---|
| Recipe | `workbench-docs-only-acceptance.yaml` |
| Validation profile | `docs_only` |
| Risk | `low` |
| Complexity band | `easy` |
| Selected tier | `local_coding` |
| Evidence source | Fresh isolated live runs, not committed synthetic samples |

Minimum eligible acceptance evidence:

- `validation_report.json` has `overall_status="passed"`.
- `validation_report.json` has `sign_off_ready=true`.
- `revision_decision.json` has `final_status="accepted"`.
- The `docs_only` changed-file policy passed with non-empty exact changed-file evidence.
- No blocker or review reason code appears in validation or quality-gate artifacts.

## Implemented Behavior

The implementation keeps the behavior advisory:

- do not change selector default rules
- do not auto-promote or auto-demote model tiers
- do not bypass deterministic validation or the quality gate
- return `prefer_current_tier` only when the route bucket has enough accepted evidence under the configured routing-feedback thresholds and matches this exact bounded policy

In current v0.2 terms, this means a matching `routing_feedback_candidates` entry with at least `min_runs=5` and `acceptance_rate>=0.8` may support `prefer_current_tier` only for `docs_only|local_coding|low|easy`, while `selected_tier` remains deterministic from `configs/model_selector.yaml`.

## Blockers

The policy candidate must not apply when any of these are true:

- risk is `medium` or `high`
- validation profile is not `docs_only`
- recipe is not `workbench-docs-only-acceptance.yaml`
- complexity band is not `easy`
- source, test, config, recipe, package, or private files changed
- changed-file evidence is missing, empty, underreported, overreported, or unavailable
- validation failed or is not sign-off ready
- quality gate returned `review_required` or `revision_required`
- evidence source is PR-gate fallback scaffold evidence
- evidence source is a deterministic control or committed synthetic sample

## Test Fixture Coverage

Focused selector tests cover:

- accepted `docs_only|local_coding|low|easy` feedback returns advisory `prefer_current_tier`
- the same candidate does not mutate `selected_tier`
- fewer than five runs returns `collect_more_evidence`
- review-heavy or failure-heavy candidates do not return `prefer_current_tier`
- medium-risk, non-docs profiles, and non-easy complexity buckets do not match this policy
- missing or fallback PR scaffold evidence never counts as acceptance evidence

## Evidence Basis

The design is based on `docs/dogfooding/targeted-docs-only-current-tier-report.md`, which records six fresh isolated live Goose runs:

- accepted: 6
- review required: 0
- failed: 0
- selected tier: `local_coding`
- validation profile: `docs_only`
- observed accepted reason codes: `docs_only.accepted`, `quality_gate.accepted`

This evidence is enough to design a bounded policy branch. It is not enough to broaden routing behavior beyond low-risk docs-only work.
