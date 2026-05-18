# Agent 04: Package Assets Or Bootstrap

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

Reduce adoption friction caused by repo assets living outside the installed wheel. Choose a conservative package-assets or bootstrap path after policy-pack asset paths are known.

Run after:

- Agent 02 policy-pack product assets

Owned files:

- `pyproject.toml`
- `MANIFEST.in` if introduced
- `src/ai_workbench_mcp/assets/**` if package resources are introduced
- new bootstrap command module if introduced, preferably `src/ai_workbench_mcp/tools/bootstrap_assets.py`
- `tools/bootstrap_assets.py` if a compatibility wrapper is introduced
- focused packaging tests, preferably `tests/test_package_assets.py`
- `docs/publishing/pypi.md`
- focused install/bootstrap docs under `docs/publishing/` or `docs/configuration/`

Do not edit:

- PR gate decision logic
- policy pack semantics
- GitHub workflow templates
- sample run evidence
- README broad narrative until the narrative stream integrates final wording

Deliverables:

- Either package the core repo assets needed for PR acceptance or provide a bootstrap command that fetches or materializes them.
- Make clear which assets are included:
  - configs
  - policy packs
  - prompts
  - recipes
  - examples or sample evidence, if any
- Do not invent provider setup or host-specific plumbing.
- Keep package behavior compatible with the existing `ai-workbench-mcp` console script.

Suggested slices:

1. Decide package-assets versus bootstrap. Prefer the smallest approach that makes the GitHub PR gate template usable.
2. Add resource loading or bootstrap command with tests.
3. Update packaging metadata and docs.
4. Run build and package checks.

Suggested verification:

```bash
python -m pytest tests/test_package_assets.py tests/test_public_hygiene.py -q -p no:cacheprovider
python -m build
python -m twine check dist/*
```
