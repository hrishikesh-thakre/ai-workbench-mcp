# PR Gate Outcome Examples

This folder contains sanitized, synthetic PR gate fixtures for the three public
PR-facing outcomes:

| Outcome | Fixture | Source evidence | Generated artifacts |
|---|---|---|---|
| Accepted | `accepted/` | `accepted/evidence/` | `accepted/pr_comment.md`, `accepted/pr_decision.json` |
| Needs review | `needs-review/` | `needs-review/evidence/` | `needs-review/pr_comment.md`, `needs-review/pr_decision.json` |
| Blocked | `blocked/` | `blocked/evidence/` | `blocked/pr_comment.md`, `blocked/pr_decision.json` |

The fixtures are not private local `runs/` history. They are committed
synthetic evidence records built to exercise the public PR gate contract.

Regenerate the artifacts from the repository root:

```bash
python tools/pr_gate.py --run-dir examples/pr-gate-outcomes/accepted/evidence --out examples/pr-gate-outcomes/accepted/pr_comment.md --json-out examples/pr-gate-outcomes/accepted/pr_decision.json
python tools/pr_gate.py --run-dir examples/pr-gate-outcomes/needs-review/evidence --out examples/pr-gate-outcomes/needs-review/pr_comment.md --json-out examples/pr-gate-outcomes/needs-review/pr_decision.json
python tools/pr_gate.py --run-dir examples/pr-gate-outcomes/blocked/evidence --out examples/pr-gate-outcomes/blocked/pr_comment.md --json-out examples/pr-gate-outcomes/blocked/pr_decision.json
```

Read the outcome from `pr_decision.json`, then use `pr_comment.md` as the
PR-facing surface. The comment is generated from Workbench evidence only and
does not embed raw model output or provider logs.
