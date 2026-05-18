# Agent 05: Public Narrative And Issue Hygiene

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

Align the public repo narrative and issue hygiene with the v0.3 semantic PR acceptance milestone.

Run timing:

- Audit and draft can run early.
- Final edits to shared docs should run after Agents 01, 02, 03, 04, and 06 have settled.

Owned files:

- `README.md`
- `docs/ai/START_HERE.md`
- `docs/ai/DECISIONS.md`
- `docs/ai/PROJECT_MAP.md`
- `docs/ai/ROADMAP_STATUS.md`
- `docs/github/launch-issues.md`
- `docs/github/issue-drafts/*.md`
- new release or milestone notes under `docs/releases/`
- new hygiene report under `docs/github/` if useful

Do not edit:

- core source files
- policy pack definitions
- workflow YAML
- PR gate tests
- package metadata
- sample evidence

Deliverables:

- Public docs no longer say stale work is still pending when the repo says it is complete.
- Current direction says:
  - stop broadening
  - do not add GEPA or extra integrations now
  - make GitHub PR acceptance real
  - make five policy packs clear and usable
  - keep Goose first
- Launch issue docs are updated or clearly marked as historical if the issue is complete.
- If authenticated GitHub access is available, update or close stale public issues with evidence-backed comments. If not, write exact proposed issue comments in docs.

Suggested slices:

1. Audit README, roadmap, launch issues, and issue drafts for stale claims.
2. Draft issue update comments for issues whose docs say the milestone is complete.
3. Update narrative docs after code streams land.
4. Run public hygiene and example docs tests.

Suggested verification:

```bash
python -m pytest tests/test_examples.py tests/test_public_hygiene.py -q -p no:cacheprovider
```
