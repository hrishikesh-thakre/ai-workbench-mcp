# Agent 06: Demo PR Evidence

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

Create public demo evidence for accepted, needs-review, and blocked PR gate outcomes without committing private run history.

Run after:

- Agent 01 semantic PR gate
- Agent 03 GitHub Actions template

Owned files:

- new sanitized PR gate examples under `examples/pr-gate-outcomes/`
- new proof docs under `docs/proof/`
- focused example tests if needed, preferably `tests/test_examples.py`
- sample evidence index docs if needed

Do not edit:

- PR gate implementation
- workflow templates
- policy pack definitions
- package metadata
- broad README or roadmap narrative except for a link requested by Agent 05

Deliverables:

- At least three reproducible demo surfaces:
  - accepted outcome
  - needs-review outcome
  - blocked outcome
- Each demo includes the generated `pr_comment.md` and `pr_decision.json` or public PR links if actual public PRs were created.
- Demo docs explain why each outcome happened based on Workbench evidence, not model prose.
- No raw provider logs, private paths, secrets, or local `runs/` evidence are committed.

Suggested slices:

1. Pick committed sanitized evidence sources or create sanitized synthetic fixtures.
2. Generate PR gate artifacts from those sources.
3. Add proof documentation for the three outcomes.
4. Add tests that examples do not contain raw model output, provider logs, secrets, or local absolute paths.
5. Run focused docs/example tests.

Suggested verification:

```bash
python -m pytest tests/test_examples.py tests/test_public_hygiene.py -q -p no:cacheprovider
python tools/pr_gate.py --run-dir examples/sample-runs/accepted-tiny-python-fix --out runs/demo-pr-gate/pr_comment.md --json-out runs/demo-pr-gate/pr_decision.json
```
