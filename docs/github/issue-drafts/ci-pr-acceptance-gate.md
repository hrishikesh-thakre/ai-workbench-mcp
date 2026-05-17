# Goal

Prototype running Workbench validation and quality-gate reporting as a pull-request acceptance check.

# Background

The current GitHub Actions workflow is a repo self-validation gate. The first PR gate slice renders an artifact-only Markdown comment and JSON decision from prepared Workbench evidence. Posting the comment to GitHub should come later, after the artifact renderer is credible.

# Acceptance Criteria

- The prototype can read a prepared evidence folder or create one from a PR workflow.
- It reports deterministic validation status and quality-gate status separately.
- It does not require committing local `runs/` history.
- It uploads `pr_comment.md` and `pr_decision.json` as workflow artifacts.
- It does not add a PR comment bot, PR write permission, or GitHub Checks API integration until the artifact-only prototype is credible.

# References

- `docs/github/pr-gate.md`
