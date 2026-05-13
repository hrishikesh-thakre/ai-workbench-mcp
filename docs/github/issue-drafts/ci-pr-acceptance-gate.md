# Goal

Prototype running Workbench validation and quality-gate reporting as a pull-request acceptance check.

# Background

The current GitHub Actions workflow is a repo self-validation gate. Semantic PR acceptance should come later, after more dogfood evidence.

# Acceptance Criteria

- The prototype can read a prepared evidence folder or create one from a PR workflow.
- It reports deterministic validation status and quality-gate status separately.
- It does not require committing local `runs/` history.
- It does not add a PR comment bot or GitHub Checks API integration until the local prototype is credible.

# References

- `docs/github/pr-gate.md`
