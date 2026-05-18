# Agent 07: Contract Finalization And Integration

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

Finalize the v0.3 alpha contract and integrate documentation after all schema-affecting streams have landed.

Run after:

- Agent 01 semantic PR gate
- Agent 02 policy packs
- Agent 03 GitHub Actions template
- Agent 04 package/bootstrap
- Agent 05 public narrative
- Agent 06 demo evidence

Owned files:

- `docs/contracts/v0.3-contract-baseline.md`
- `docs/contracts/v0.2-contract-baseline.md` only for a forward link or compatibility note
- `src/ai_workbench_mcp/contracts.py`
- `tests/test_contracts.py`
- `docs/github/pr-gate.md`
- final integration notes in `docs/ai/PROJECT_MAP.md` or `docs/ai/ROADMAP_STATUS.md` if coordinated with Agent 05

Do not edit:

- policy behavior except contract normalization
- PR gate behavior except schema naming fixes agreed with Agent 01
- packaging behavior
- workflow behavior
- sample evidence content

Deliverables:

- v0.3 alpha contract baseline covering:
  - complete run evidence
  - `validation_report.json`
  - `revision_decision.json`
  - policy pack asset schema
  - PR decision JSON
  - PR comment surface
  - GitHub workflow template boundary
  - packaging or bootstrap boundary
  - backward compatibility with v0.2 sample runs
- Contract tests for the final agreed machine-readable shapes.
- `docs/github/pr-gate.md` reflects semantic PR acceptance rather than prototype-only visibility.

Suggested slices:

1. Inventory final schemas from merged streams.
2. Draft v0.3 contract baseline with explicit compatibility notes.
3. Add or update contract tests.
4. Update PR gate docs to point to the v0.3 contract.
5. Run focused and full tests.

Suggested verification:

```bash
python -m pytest tests/test_contracts.py tests/test_pr_gate.py tests/test_validate_run.py -q -p no:cacheprovider
python -m pytest -q -p no:cacheprovider
```
