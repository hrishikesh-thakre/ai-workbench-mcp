# Agent 03: GitHub Actions Copy-Paste Template

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

Create an installable GitHub Actions workflow template users can copy into any repository.

Owned files:

- `.github/workflows/ai-workbench-pr-gate.yml`
- new workflow-template tests, preferably `tests/test_github_workflow_template.py`
- new docs under `docs/github/`, preferably `docs/github/pr-gate-workflow-template.md`

Do not edit:

- `.github/workflows/ci.yml` unless explicitly asked by the integration stream
- `src/ai_workbench_mcp/tools/pr_gate.py`
- `src/ai_workbench_mcp/tools/pr_gate_comment.py`
- validation profiles or policy-pack files
- README or roadmap narrative except a link owned by the narrative stream

Deliverables:

- A copy-paste workflow template named `.github/workflows/ai-workbench-pr-gate.yml`.
- Same-repository PR sticky comment support.
- Fork PRs render/upload artifacts but avoid unsafe comment posting.
- Template can consume a real Workbench acceptance run directory when provided.
- Template falls back to a blocking scaffold or missing-evidence message when real evidence is absent.
- The workflow does not treat green CI as semantic acceptance.

Design constraints:

- Use existing PR gate CLI flags. If a new flag is needed, record the need for Agent 01 instead of editing PR gate code.
- Keep permissions minimal: `contents: read`, `pull-requests: write` only when comments are posted.
- Do not require committing `runs/`.
- Prefer artifact upload for `pr_comment.md` and `pr_decision.json`.
- The template should be understandable without reading this whole repository.

Suggested slices:

1. Draft workflow inputs and environment variables for evidence run directory, run id, and fallback behavior.
2. Add the workflow template without changing existing CI.
3. Add static tests that assert the template uses safe permissions, guarded comments, artifact upload, and blocking fallback.
4. Add copy-paste documentation.
5. Run focused tests.

Suggested verification:

```bash
python -m pytest tests/test_github_workflow_template.py tests/test_public_hygiene.py -q -p no:cacheprovider
```
