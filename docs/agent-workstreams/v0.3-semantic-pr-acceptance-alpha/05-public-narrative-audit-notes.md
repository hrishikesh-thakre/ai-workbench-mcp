# Stream 05 Public Narrative Audit Notes

Date: 2026-05-18
Mode: audit-only / draft
Write scope: this file only

## Scope

Audited:

- `README.md`
- `docs/ai/START_HERE.md`
- `docs/ai/DECISIONS.md`
- `docs/ai/PROJECT_MAP.md`
- `docs/ai/ROADMAP_STATUS.md`
- `docs/github/launch-issues.md`
- `docs/github/issue-drafts/*.md`

Context also read:

- `AGENTS.md`
- `docs/concepts/how-acceptance-works.md`
- `docs/contracts/v0.2-contract-baseline.md`
- `docs/github/pr-gate.md`
- `docs/agent-workstreams/v0.3-semantic-pr-acceptance-alpha/05-public-narrative-issue-hygiene.md`

No public docs, issue drafts, source files, tests, workflows, or configs were edited.

## Executive Summary

The public narrative is mostly consistent about the core acceptance rule: do not call a run accepted without `validation_report.json` plus `revision_decision.json`. The stale area is the current/next story. Several surfaces still frame semantic PR acceptance as future work after routing-policy experiments, while the v0.3 workstream is specifically the Semantic PR Acceptance Alpha.

The final doc pass should reposition v0.3 around:

- GitHub PR acceptance consuming real Workbench run evidence.
- Exactly one PR gate outcome: `accept`, `needs_review`, or `block`.
- Scaffold-only CI evidence always blocking.
- PR comments answering decision, why, required next action, and evidence-artifact presence.
- Goose staying the default execution surface.
- Workbench core staying runtime-agnostic.
- No broadening into GEPA, extra host integrations, provider plumbing, Checks API enforcement, or Codex cloud export in this milestone.

## Proposed Public Doc Edits

### `README.md`

Findings:

- Lines around the Roadmap still say the current work is the CI gate prototype plus docs-only routing, and semantic PR acceptance is next.
- The Examples list calls the PR surface a "CI gate prototype" where "semantic PR acceptance comes later".
- The opening host narrative emphasizes Codex local/IDE as the first second host. That support is real, but the v0.3 public headline should stay Goose-first and PR-acceptance-focused.

Proposed edits after Streams 01, 02, 03, 04, and 06 settle:

- Add a short "GitHub PR Acceptance Alpha" section after "What Decides Acceptance" or near the GitHub examples:
  - PR gate reads Workbench acceptance evidence for a PR.
  - Required evidence is `validation_report.json` and `revision_decision.json`.
  - Outcome vocabulary is `accept`, `needs_review`, and `block`.
  - `runs/ci_scaffold` fallback is visibility evidence only and blocks with `pr_gate.acceptance_evidence_missing`.
  - Sticky PR comments are a visibility surface, not a replacement for the evidence artifacts.
- Update the Examples link currently labeled "CI gate prototype" to "GitHub PR acceptance alpha" once the stream lands.
- Update Roadmap bullets:
  - Current: `v0.3 Semantic PR Acceptance Alpha: PR gate consumes real Workbench evidence, reports accept/needs_review/block, and blocks scaffold-only fallback evidence.`
  - Next: `Checks API integration, enforcement policy, fork-comment strategy, cost/time evidence, and stable v1 contract packaging.`
- Keep the PyPI note clear: the current published wheel is still code/server only unless Stream 04 changes the package boundary.

### `docs/ai/START_HERE.md`

Findings:

- Status and current-state language still says `v0.2 alpha release candidate`.
- The pivot banner includes "Codex local/IDE first-class as the first second host"; useful, but too prominent for the v0.3 public direction.
- Section 8 says the next product pass is "one narrow routing-policy experiment at a time, plus the GitHub-native PR acceptance gate", which underplays the active v0.3 PR acceptance milestone.
- Validation expectations do not mention PR gate rendering/comment evidence.

Proposed edits:

- Distinguish package version from active milestone. Example: `Status: v0.3 semantic PR acceptance alpha in progress; latest published alpha remains 0.2.0a0 until release.`
- Restore the top direction to the AGENTS.md wording:
  - `Goose-first distribution.`
  - `Workbench-owned acceptance and audit layer.`
  - `Runtime-agnostic core.`
- Keep Codex local/IDE in its own support paragraph, not as the headline direction.
- Replace the post-Phase 5 next-step paragraph with v0.3 priorities:
  - make PR acceptance real from Workbench evidence
  - keep routing feedback advisory
  - keep the five core policy profiles clear and usable
  - do not broaden to GEPA, extra integrations, Checks API, or Codex cloud export
- Add PR gate artifact rendering to validation expectations once Stream 01/03 settle.

### `docs/ai/DECISIONS.md`

Findings:

- Status remains `v0.2 alpha release candidate`.
- Decision 7 says profile growth should be revisited before v0.3. The v0.3 workstream now needs a concrete policy packaging decision or a clear deferral.
- The document correctly says Goose-first, not Goose-only, and should keep that framing.

Proposed edits:

- Add or update a decision for v0.3 policy packaging after Stream 02 settles:
  - If policy packs stay in `configs/validation_profiles.yaml`, say so explicitly and state why.
  - If first-class assets are introduced, record the compatibility rule that existing profile names remain stable.
- Avoid saying the five core policy profiles are pending. The current v0.2 forms already exist: `docs_only`, `low_risk_bug_fix`, `test_fix`, `api_contract_change`, and `security_privacy_sensitive`.
- Keep "do not rebuild broad MCP/provider plumbing" and "do not create a Codex-specific server" unchanged.

### `docs/ai/PROJECT_MAP.md`

Findings:

- The file map does not list the PR gate renderer or sticky PR comment helper, although they are central to v0.3:
  - `src/ai_workbench_mcp/tools/pr_gate.py`
  - `tools/pr_gate.py`
  - `src/ai_workbench_mcp/tools/pr_gate_comment.py`
  - `tools/pr_gate_comment.py`
- The workflow row still describes only a public repo self-validation CI gate prototype.

Proposed edits:

- Add the PR gate renderer and sticky comment helper to the file map.
- Add a small PR gate boundary section:
  - input: Workbench run evidence or explicit scaffold fallback
  - required artifacts for acceptance: `validation_report.json`, `revision_decision.json`
  - outputs: `runs/pr_gate/pr_comment.md`, `runs/pr_gate/pr_decision.json`
  - allowed outcomes: `accept`, `needs_review`, `block`
  - scaffold-only fallback always blocks
- Keep the non-goals list unchanged, and add "GEPA or extra host integrations for v0.3" only if the final public docs need that explicit warning.

### `docs/ai/ROADMAP_STATUS.md`

Findings:

- Status remains `v0.2 alpha release candidate`.
- The status matrix currently marks the PR gate as a GitHub-native prototype and says semantic enforcement remains future work.
- Current Next Step is still the docs-only current-tier advisory policy branch and another routing experiment, not v0.3 semantic PR acceptance.

Proposed edits:

- Add a new matrix row for `v0.3 Semantic PR Acceptance Alpha`.
- Update or split the `Public CI gate prototype` row:
  - historical prototype: repo self-validation plus artifact rendering and guarded sticky comments
  - v0.3 alpha: real Workbench evidence PR gate with `accept`/`needs_review`/`block`, scaffold-only blocking, and required next-action reporting
- Replace Current Next Step with:
  - land semantic PR gate evidence consumption
  - finalize policy-pack metadata display for the five core profiles
  - add or document copy-paste GitHub Actions integration
  - publish demo PR evidence
  - finalize contract docs last
- Keep routing feedback advisory and keep docs-only current-tier policy described as bounded, not the main current direction.

### `docs/github/launch-issues.md`

Findings:

- The top paragraph still says the issues should gather real evidence before adding more recipes or broadening provider integrations. Issue `#1` has already met the Phase 5 target.
- Issue `#5` is titled as a PR acceptance gate prototype, but its current criteria mostly describe the already existing renderer/comment prototype. It does not yet capture the v0.3 semantic acceptance alpha criteria.
- Issue `#6` asks for a five-minute Goose demo. The repo now has a recording-ready walkthrough and proof/demo script docs, but the issue should clarify whether a published recording is still required.

Proposed edits:

- Mark the launch issue list as a historical launch backlog plus current status.
- Mark `#1` complete/historical and point to `docs/dogfooding/phase5-final-report.md`.
- Update `#5` to v0.3 alpha criteria:
  - consumes a real Workbench acceptance run for a PR
  - reports exactly one of `accept`, `needs_review`, or `block`
  - shows validation and quality-gate status separately
  - reports whether `validation_report.json` and `revision_decision.json` are present
  - blocks scaffold-only fallback evidence
  - posts or updates one sticky same-repo PR comment when available
  - leaves Checks API enforcement and fork strategy out of scope
- Update `#6` status to distinguish written runbook/proof pack from an actual recorded video.

### `docs/github/issue-drafts/*.md`

Findings and proposed updates:

- `dogfooding-collect-goose-runs.md`: stale as an active issue body. Add a completion note or retire the draft.
- `analytics-routing-feedback-policy-experiments.md`: still valid, but should mention the first docs-only current-tier advisory policy as the first bounded experiment if merged.
- `cost-evidence-provider-metadata.md`: still valid and not v0.3-blocking.
- `policy-packs-validation-metadata.md`: mostly current. Update after Stream 02 to reflect the settled policy-pack packaging decision.
- `ci-pr-acceptance-gate.md`: needs the biggest update. The current draft is prototype-shaped; v0.3 should be real evidence acceptance alpha-shaped.
- `docs-five-minute-goose-demo.md`: clarify whether remaining work is publishing a recording or whether the written walkthrough/proof pack closes it.

## Proposed GitHub Issue Comments

### Issue `#1`: dogfooding: collect 20-50 Goose acceptance runs

```md
Phase 5 evidence collection is complete. `docs/dogfooding/phase5-final-report.md` records 31 complete evidence runs, including 29 live Goose runs and 2 deterministic controls. The closeout records 16 accepted outcomes, 15 review-required outcomes, and 0 failed public outcomes, with raw `runs/` evidence kept out of git.

Recommended disposition: close this issue as complete/historical. Follow-up routing work should use bounded, evidence-backed policy experiments rather than more broad dogfood collection.
```

### Issue `#2`: analytics: promote routing feedback candidates into policy experiments

```md
Status update for routing feedback: the repo now records the first bounded docs-only current-tier policy pass. The supporting evidence is six isolated low-risk `docs_only` Goose runs on `local_coding`, all accepted, with no review-required or failed outcomes, recorded in `docs/dogfooding/targeted-docs-only-current-tier-report.md`.

Keep this issue open only for the next bounded routing-policy experiment. Please keep routing feedback advisory, do not broaden from this evidence to medium-risk work, code changes, `test_fix`, or security/privacy-sensitive work, and do not change default selected tiers without fresh isolated evidence.
```

### Issue `#3`: cost evidence: capture provider token and cost metadata

```md
No v0.3 semantic PR acceptance change proposed here. Cost/time evidence remains useful, but it should stay decoupled from PR acceptance until provider-backed metadata exists. Analytics should continue to distinguish "no provider cost evidence" from free execution, and sample data should not invent provider costs.
```

### Issue `#4`: policy packs: design first-class validation policy metadata

```md
v0.3 policy-pack hygiene note: the five requested core policy profiles already exist in v0.2 form: `docs_only`, `low_risk_bug_fix`, `test_fix`, `api_contract_change`, and `security_privacy_sensitive`.

The remaining product question is packaging and display, not inventing new broad policy families. For the semantic PR acceptance alpha, please preserve existing profile names, keep sign-off profiles command-backed, and make the policy metadata clear enough for PR gate comments to explain blocked, review-required, and accepted outcomes without parsing prose.
```

### Issue `#5`: ci: prototype PR acceptance gate

```md
Recommended v0.3 retitle/scope update: this has moved beyond "prototype PR acceptance gate" into "semantic PR acceptance alpha".

The alpha acceptance surface should consume real Workbench acceptance evidence for a PR and report exactly one outcome: `accept`, `needs_review`, or `block`. It should show validation status and quality-gate status separately, report whether `validation_report.json` and `revision_decision.json` are present, state why the decision happened, and give the required next action. Scaffold-only fallback evidence must block with `pr_gate.acceptance_evidence_missing`.

Out of scope for this issue: GitHub Checks API integration, broad enforcement policy, fork-comment strategy changes, GEPA, provider plumbing, and extra host integrations.
```

### Issue `#6`: docs: record a five-minute Goose acceptance demo

```md
Status check: the repo now includes a recording-ready Goose walkthrough (`docs/walkthroughs/goose-acceptance-demo.md`) plus proof/demo material under `docs/proof/`. If the issue requires a published video, the remaining work should be narrowed to recording and linking that artifact. If a written public demo path is sufficient, this can be closed as complete.

Any recorded demo should use committed sample evidence or a sanitized toy task and must not publish raw local `runs/` evidence, provider secrets, or private target-repo paths.
```

## Cross-Stream Handoffs

- Stream 01: final README and roadmap wording should reflect the settled PR gate decision/comment shape and any CLI flag changes.
- Stream 02: final policy-pack wording depends on whether policy metadata stays embedded in validation profiles or moves to first-class package assets.
- Stream 03: final GitHub issue `#5` wording should match the copy-paste workflow template and same-repo/fork behavior.
- Stream 04: README install/package boundary wording depends on whether repo assets remain checkout-only or become packaged/bootstrap-installed.
- Stream 06: demo issue `#6` status depends on the final demo PR evidence and whether any public recording/link is created.
- Stream 07: contract wording should be the final source for v0.3 artifact fields and compatibility rules.

## Audit Checks Run

- Read common packet, AGENTS instructions, required `docs/ai/*` read-first files, acceptance concept doc, v0.2 contract baseline, README, launch issue docs, issue drafts, and PR gate guide.
- Ran targeted `rg` scans for stale status, v0.2/v0.3 references, PR acceptance language, scaffold/fallback evidence, policy profile names, and GitHub issue hygiene markers.
- No pytest suite was run during this audit because the requested deliverable is a draft notes file and public docs were not changed.

## Remaining Risks

- Line references from the audit scans may drift before final doc edits.
- Other streams are editing disjoint files in parallel, so any proposed wording that describes implementation details must be rechecked after Streams 01, 02, 03, 04, and 06 settle.
- GitHub issue state was inferred from local docs only; no authenticated GitHub issue status check or live comment update was performed.
- The public version/package status may still be `0.2.0a0`; final docs should avoid implying a v0.3 package release before publication.

## Minimum Handoff

Files changed:

- `docs/agent-workstreams/v0.3-semantic-pr-acceptance-alpha/05-public-narrative-audit-notes.md`

Behavior changed:

- None. Audit notes only.

Tests or checks run:

- Read-only file review and targeted `rg` scans listed above.

Remaining risks:

- Revalidate implementation-dependent language after the code, policy, packaging, workflow-template, demo, and contract streams land.

Cross-stream needs:

- See Cross-Stream Handoffs above.
