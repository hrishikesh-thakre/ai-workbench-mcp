# Goal

Move the pull-request gate from a repo self-validation prototype to the v0.3 Semantic PR Acceptance Alpha.

# Background

The current GitHub Actions workflow is a repo self-validation gate. The first PR gate slice renders Markdown and JSON artifacts from prepared Workbench evidence. After the artifact renderer became credible enough for a GitHub-native surface, CI added guarded same-repository sticky comment posting while keeping the artifacts as the source of truth.

v0.3 narrows the PR-facing story: the gate should consume real Workbench acceptance evidence for a PR and report exactly one of `accept`, `needs_review`, or `block`. Green CI, sticky comments, and scaffold evidence are not acceptance.

# Acceptance Criteria

- The gate can read a prepared Workbench evidence folder for a PR.
- It reports exactly one of `accept`, `needs_review`, or `block`.
- It reports deterministic validation status and quality-gate status separately.
- It reports whether `validation_report.json` and `revision_decision.json` are present.
- It states why the decision happened and gives the required next action.
- It blocks scaffold-only fallback evidence with `pr_gate.acceptance_evidence_missing`.
- It does not require committing local `runs/` history.
- It uploads `pr_comment.md` and `pr_decision.json` as workflow artifacts.
- It posts or updates one marker-based PR comment only for same-repository pull requests.
- It skips comment posting for fork pull requests.
- It does not add `issues: write`, raw `gh pr comment`, or GitHub Checks API integration.

# Out Of Scope

- Running live Goose inside the template.
- Treating green CI as Workbench acceptance.
- GitHub Checks API enforcement.
- Fork-comment strategy changes.
- GEPA, provider plumbing, or extra host integrations.

# References

- `docs/github/pr-gate.md`
- `docs/github/pr-gate-workflow-template.md`
- `docs/proof/pr-gate-outcome-demos.md`
