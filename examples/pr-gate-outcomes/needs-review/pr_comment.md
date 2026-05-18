# AI Workbench PR Gate: Needs Review

Decision: Needs Review
Why: Policy requires contract-owner review before merge.
Required next action: Record contract-owner approval, then regenerate the PR gate artifact.
Evidence present: validation_report yes, revision_decision yes

## Details

**Run ID:** `pr-gate-demo-needs-review`
**Evidence source:** `acceptance_run`
**Source run dir:** `examples/pr-gate-outcomes/needs-review/evidence`

## Status

| Check | Status |
|---|---|
| Validation | `needs_review` |
| Quality gate | `review_required` |

## Evidence

| Artifact | Path | Present |
|---|---|---|
| validation_report | `validation_report.json` | yes |
| revision_decision | `revision_decision.json` | yes |
| model_output | `model_output.md` | yes |
| run_log | `run_log.jsonl` | yes |

## Reason Codes

- `api_contract_change.review_required`
- `quality_gate.review_required`

This artifact is generated from Workbench evidence only. It does not embed raw model output or provider logs.
