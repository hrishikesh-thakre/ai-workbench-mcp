# Agent 02: Policy Packs As Product Assets

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

Turn policy packs into first-class product assets while preserving validation-profile compatibility.

Owned files:

- `configs/validation_profiles.yaml`
- new policy-pack asset files if introduced, preferably under `configs/` or `policy_packs/`
- new policy-pack loader module if needed, preferably `src/ai_workbench_mcp/tools/policy_packs.py`
- `src/ai_workbench_mcp/tools/validate_run.py`
- `tests/test_validate_run.py`
- `tests/test_recipes.py`
- focused policy-pack docs under `docs/policy-packs/` if introduced

Do not edit:

- `src/ai_workbench_mcp/tools/pr_gate.py`
- `src/ai_workbench_mcp/tools/pr_gate_comment.py`
- `.github/workflows/*`
- packaging files unless the packaging stream asks for final asset paths
- README or roadmap narrative except a small link to policy-pack docs

Deliverables:

- Exactly five first-class policy packs:
  - `docs_only`
  - `low_risk_bug_fix`
  - `test_fix`
  - `api_contract_change`
  - `security_privacy_sensitive`
- Do not add more packs in this stream.
- Preserve existing profile names used by recipes.
- Each pack has machine-readable:
  - allowed files
  - required tests
  - required evidence
  - review triggers
  - blocker rules
  - reason codes
- Validation reports continue to include `policy_pack`, `reason_sources`, and `reason_codes`.
- Existing committed sample runs remain tolerated by consumers.

Suggested slices:

1. Decide representation. Prefer compatibility: profiles may reference first-class pack metadata, but recipe-facing profile names should remain stable.
2. Add or refactor loader logic with clear fallback for existing v0.2 embedded metadata.
3. Restrict the documented product pack catalog to the five target packs.
4. Strengthen tests for pack discovery, pack-to-profile linkage, required tests, required evidence, and reason-code emission.
5. Run focused validation and recipe tests.

Suggested verification:

```bash
python -m pytest tests/test_validate_run.py tests/test_recipes.py -q -p no:cacheprovider
python tools/validate_run.py --project ai_workbench_mcp --profile scaffold --out-dir runs/policy-pack-scaffold
```
