# Goal

Prototype running Workbench validation and quality-gate reporting as a pull-request acceptance check.

# Background

The current GitHub Actions workflow is a repo self-validation gate. The first PR gate slice renders Markdown and JSON artifacts from prepared Workbench evidence. After the artifact renderer became credible enough for a GitHub-native surface, CI added guarded same-repository sticky comment posting while keeping the artifacts as the source of truth.

# Acceptance Criteria

- The prototype can read a prepared evidence folder or create one from a PR workflow.
- It reports deterministic validation status and quality-gate status separately.
- It does not require committing local `runs/` history.
- It uploads `pr_comment.md` and `pr_decision.json` as workflow artifacts.
- It posts or updates one marker-based PR comment only for same-repository pull requests.
- It skips comment posting for fork pull requests.
- It does not add `issues: write`, raw `gh pr comment`, or GitHub Checks API integration.

# References

- `docs/github/pr-gate.md`
