# PR Gate Outcome Demos

Status: sanitized synthetic proof fixtures
Last reviewed: 2026-05-18

## Purpose

These fixtures provide public, reproducible PR gate evidence for the three
PR-facing outcomes:

- `accept`
- `needs_review`
- `block`

No public PRs were created for this proof. The committed artifacts are generated
from sanitized synthetic Workbench evidence under `examples/pr-gate-outcomes/`.
They are not private local `runs/` history.

## Evidence Set

| PR gate outcome | Source evidence | Generated comment | Generated decision |
|---|---|---|---|
| Accepted | `examples/pr-gate-outcomes/accepted/evidence/` | `examples/pr-gate-outcomes/accepted/pr_comment.md` | `examples/pr-gate-outcomes/accepted/pr_decision.json` |
| Needs review | `examples/pr-gate-outcomes/needs-review/evidence/` | `examples/pr-gate-outcomes/needs-review/pr_comment.md` | `examples/pr-gate-outcomes/needs-review/pr_decision.json` |
| Blocked | `examples/pr-gate-outcomes/blocked/evidence/` | `examples/pr-gate-outcomes/blocked/pr_comment.md` | `examples/pr-gate-outcomes/blocked/pr_decision.json` |

Each source evidence folder includes:

```text
validation_report.json
revision_decision.json
model_output.md
run_log.jsonl
task_metadata.json
```

The PR comment does not embed `model_output.md` or provider logs. It displays
the decision, reason, required next action, and whether the validation and
quality-gate artifacts are present.

## Accepted Demo

The accepted fixture uses `profile="docs_only"`.

Decisive evidence:

```text
validation_report.json: overall_status = passed
validation_report.json: sign_off_ready = true
revision_decision.json: final_status = accepted
```

The generated PR decision is:

```text
outcome = accept
reason = Validation passed and the quality gate accepted the documentation-only run.
required_next_action = No Workbench action required before merge.
```

Reason codes:

```text
docs_only.accepted
quality_gate.accepted
```

## Needs-Review Demo

The needs-review fixture uses `profile="api_contract_change"`.

Decisive evidence:

```text
validation_report.json: overall_status = needs_review
validation_report.json: sign_off_ready = false
revision_decision.json: final_status = review_required
```

The deterministic contract check passed, but the policy requires a
contract-owner review. No blocker-severity reason source is present, so the PR
gate outcome is `needs_review` rather than `block`.

The generated PR decision is:

```text
outcome = needs_review
reason = Policy requires contract-owner review before merge.
required_next_action = Record contract-owner approval, then regenerate the PR gate artifact.
```

Reason codes:

```text
api_contract_change.review_required
quality_gate.review_required
```

## Blocked Demo

The blocked fixture uses `profile="docs_only"` and records a
blocker-severity changed-file policy finding.

Decisive evidence:

```text
validation_report.json: overall_status = needs_review
validation_report.json: sign_off_ready = false
validation_report.json: reason_sources[0].severity = blocker
revision_decision.json: final_status = review_required
```

The quality gate has a review status, but blocker-severity evidence prevents the
PR gate from presenting this as ordinary review work.

The generated PR decision is:

```text
outcome = block
reason = Source file changed in docs-only policy.
required_next_action = Move source-code edits to an implementation profile or remove them, rerun validation, and regenerate the PR gate artifact.
```

Reason codes:

```text
docs_only.source_file_blocked
quality_gate.blocker_present
```

## Reproduction

Run from the repository root:

```bash
python tools/pr_gate.py --run-dir examples/pr-gate-outcomes/accepted/evidence --out examples/pr-gate-outcomes/accepted/pr_comment.md --json-out examples/pr-gate-outcomes/accepted/pr_decision.json
python tools/pr_gate.py --run-dir examples/pr-gate-outcomes/needs-review/evidence --out examples/pr-gate-outcomes/needs-review/pr_comment.md --json-out examples/pr-gate-outcomes/needs-review/pr_decision.json
python tools/pr_gate.py --run-dir examples/pr-gate-outcomes/blocked/evidence --out examples/pr-gate-outcomes/blocked/pr_comment.md --json-out examples/pr-gate-outcomes/blocked/pr_decision.json
```

The expected outcomes are:

```text
accepted/pr_decision.json: outcome = accept
needs-review/pr_decision.json: outcome = needs_review
blocked/pr_decision.json: outcome = block
```

## Hygiene Boundary

These fixtures intentionally avoid:

- raw provider logs
- provider credentials or tokens
- private target-repo names
- local absolute paths
- unreviewed `runs/` ledgers

They are public demo artifacts for the PR gate renderer, not live acceptance
claims for an unpublished private run.
