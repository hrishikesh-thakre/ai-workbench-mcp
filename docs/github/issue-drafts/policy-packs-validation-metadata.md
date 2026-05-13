# Goal

Design first-class validation policy metadata when `configs/validation_profiles.yaml` becomes too limited.

# Background

Validation profiles currently cover commands, artifacts, review checks, and changed-file policies. A policy-pack shape may become useful when profile metadata needs versioning, risk labels, or richer artifact rules.

# Acceptance Criteria

- Existing validation profile names remain backward compatible.
- A migration plan preserves current recipe references.
- The proposal explains what cannot be represented cleanly in the current YAML shape.
- The proposal does not break the v0.2 recipe and profile workflow.

# References

- `configs/validation_profiles.yaml`
- `recipes/`
