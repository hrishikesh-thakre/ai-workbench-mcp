# AI Workbench PR Gate: Block

Decision: Block
Why: Source file changed in docs-only policy.
Required next action: Move source-code edits to an implementation profile or remove them, rerun validation, and regenerate the PR gate artifact.
Evidence present: validation_report yes, revision_decision yes

## Details

**Run ID:** `pr-gate-demo-blocked`
**Evidence source:** `acceptance_run`
**Source run dir:** `examples/pr-gate-outcomes/blocked/evidence`
**Policy pack:** `docs_only`
**Validation profile:** `docs_only`
**Selection mode:** `unknown`

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

- `docs_only.source_file_blocked`
- `quality_gate.blocker_present`

This artifact is generated from Workbench evidence only. It does not embed raw model output or provider logs.
