# Acceptance Policy Model

`AI Workbench` uses a policy-pack model to define what evidence is required before accepting AI-generated work.

## Workbench Outcomes

| Outcome | Meaning |
|---|---|
| `accept` | Required evidence exists, deterministic validation passed, and the quality gate accepted the run. |
| `needs_review` | Evidence exists, but warnings, coverage gaps, or policy follow-ups require human review. |
| `block` | Required evidence is missing, validation failed or was skipped for a code change, or blocker findings are present. |

The supervisor may also write a supporting local acceptance report from the
imported evidence-gate engine. That report is not the final product contract.
The final authority is always the Workbench pair:

- `validation_report.json`
- `revision_decision.json`

## Policy Pack Structure

A policy pack is a YAML file that defines:

```yaml
name: policy_name
description: What this policy covers
applies_to:
  - task_type_1
  - task_type_2

required_checks:
  - check_name_1
  - check_name_2

required_evidence:
  - evidence_item_1

reject_if:
  - condition_1

block_if:
  - condition_1

confidence_thresholds:
  high: 0.90
  heuristic_cap: 0.75

risk_tier: medium
```

## Supervisor-Check Profiles

| Policy | Task Types | Key Checks |
|---|---|---|
| `read_only_audit.yml` | audit, review, listing, evaluation, signoff | Transcript truncation, workspace hygiene, no-repo-modification, confidence, scope completeness |
| `code_change.yml` | code_change, bugfix, feature, refactor, dependency_update | Transcript truncation, workspace hygiene, changed-files summary, confidence, scope completeness |
| `corpus_audit.yml` | corpus_audit, inventory, extraction, data_audit, compliance_scan | Transcript truncation, deterministic evidence, workspace hygiene, confidence, scope completeness, heuristic extraction |

## Confidence Discipline

- Confidence above `0.90` requires deterministic evidence artifacts
- Heuristic extraction caps confidence at `0.75`
- "Complete" or "100%" claims require scoped corpus evidence
- These thresholds are configurable per policy pack via `confidence_thresholds`

## Human Review Triggers

Human review is required when:

- Outcome is `needs_review` or `block`
- Task is classified as high-risk (security, auth, data migration, etc.)
- Confidence gap exceeds policy threshold
- Policy explicitly requires human sign-off

Low-risk tasks that pass all checks with `accept` require no human review by default.
