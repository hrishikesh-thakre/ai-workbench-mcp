# Agent 01: Semantic PR Gate And Comment Surface

## Common Packet

You are working on `v0.3 - Semantic PR Acceptance Alpha`.

Read first:

- `AGENTS.md`
- `docs/ai/START_HERE.md`
- `docs/ai/DECISIONS.md`
- `docs/ai/PROJECT_MAP.md`
- `docs/ai/ROADMAP_STATUS.md`
- `docs/concepts/how-acceptance-works.md`
- `docs/contracts/v0.2-contract-baseline.md`
- `README.md`

Current repo facts:

- The PR gate renderer lives in `src/ai_workbench_mcp/tools/pr_gate.py` with a wrapper at `tools/pr_gate.py`.
- Sticky PR comment posting lives in `src/ai_workbench_mcp/tools/pr_gate_comment.py` with a wrapper at `tools/pr_gate_comment.py`.
- `.github/workflows/ci.yml` currently renders from `runs/ci_scaffold` as fallback scaffold evidence.
- Scaffold-only evidence must block. It is visibility evidence, not semantic acceptance evidence.
- Complete Workbench acceptance requires `validation_report.json` and `revision_decision.json`.
- The five requested core policy profiles already exist in v0.2 form: `docs_only`, `low_risk_bug_fix`, `test_fix`, `api_contract_change`, and `security_privacy_sensitive`.
- The current PyPI wheel is code/server only; repo assets still require a checkout.

Milestone goal:

- PR gate consumes real Workbench acceptance evidence for a PR.
- PR gate reports exactly one of `accept`, `needs_review`, or `block`.
- PR comment answers in 10 seconds: decision, why, required next action, and whether `validation_report.json` and `revision_decision.json` are present.
- Scaffold-only evidence always blocks.
- Goose remains the default execution surface. Workbench remains runtime-agnostic.

Shared rules:

- Do not claim accepted without deterministic validation and a quality-gate decision.
- Do not commit local `runs/` evidence.
- Do not add private paths, provider secrets, or personal target-repo config.
- Do not broaden into new host integrations.
- Keep changes within your ownership packet.
- If you need a file owned by another stream, stop and write a handoff note instead of editing it.

Required execution cycle for every slice:

1. Plan the slice, including exact files to touch.
2. Review the plan for gaps, repo inconsistency, and ownership violations.
3. Implement only that slice.
4. Review the implementation, correct mistakes, and run relevant checks.
5. Mark the slice complete before moving to the next slice.

Minimum handoff format:

- Files changed
- Behavior changed
- Tests or checks run
- Remaining risks
- Any cross-stream needs

## Agent-Specific Packet

Mission:

Make the PR gate semantic and make the comment the main merge-facing surface.

This stream owns both priority 1 and priority 5 because the decision mapping and comment rendering currently live in the same module. Do not split these across agents unless the renderer is first extracted into a separate owned file.

Owned files:

- `src/ai_workbench_mcp/tools/pr_gate.py`
- `tools/pr_gate.py`
- `tests/test_pr_gate.py`
- `src/ai_workbench_mcp/tools/pr_gate_comment.py` only if sticky comment behavior must change
- `tools/pr_gate_comment.py` only if wrapper behavior must change
- new focused PR gate fixtures under `tests/fixtures/` if needed

Do not edit:

- `.github/workflows/*`
- `configs/validation_profiles.yaml`
- future policy-pack asset files
- `src/ai_workbench_mcp/tools/validate_run.py`
- `src/ai_workbench_mcp/tools/quality_loop.py`
- public narrative docs except for a small note requested by the integration stream

Deliverables:

- Real acceptance evidence maps to:
  - `accept` when validation passed, `sign_off_ready=true`, and quality gate accepted.
  - `needs_review` when validation or quality gate requires review and no blocker severity exists.
  - `block` when evidence is missing, unreadable, failed, revision-required, blocker-severity, or scaffold-only.
- Fallback scaffold evidence always blocks with `pr_gate.acceptance_evidence_missing`.
- Comment top section uses this order:
  - `Decision: Accept|Needs Review|Block`
  - `Why: <concise reason>`
  - `Required next action: <action>`
  - `Evidence present: validation_report yes/no, revision_decision yes/no`
- Comment must not embed raw `model_output.md`, provider logs, or private evidence contents.
- JSON decision remains machine-readable and backward-compatible with v0.2 consumers where reasonable.

Suggested slices:

1. Inventory current PR gate behavior and tests.
2. Tighten decision mapping around real evidence, missing evidence, failed validation, review-required evidence, and blocker reason sources.
3. Rework the comment top section for 10-second scanability.
4. Add tests for accepted, needs-review, blocked, scaffold-only, missing `validation_report.json`, missing `revision_decision.json`, invalid JSON, and raw-output non-disclosure.
5. Run focused tests and then the full suite if decision schema changed.

Suggested verification:

```bash
python -m pytest tests/test_pr_gate.py -q -p no:cacheprovider
python tools/pr_gate.py --run-dir examples/sample-runs/accepted-tiny-python-fix --out runs/pr_gate/pr_comment.md --json-out runs/pr_gate/pr_decision.json --fail-on-block
python tools/pr_gate.py --fallback-run-dir runs/ci_scaffold --out runs/pr_gate/pr_comment.md --json-out runs/pr_gate/pr_decision.json
```
