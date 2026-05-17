# Goal

Design first-class validation policy metadata when `configs/validation_profiles.yaml` becomes too limited.

# Background

Validation profiles currently cover commands, artifacts, review checks, and changed-file policies. A policy-pack shape may become useful when profile metadata needs versioning, risk labels, or richer artifact rules.

# Current v0.2 Shape

Policy packs still live as named profiles in `configs/validation_profiles.yaml`.

The current core packs are:

- `docs_only`
- `low_risk_bug_fix`
- `test_fix`
- `api_contract_change`
- `security_privacy_sensitive`

Each core pack declares `policy_pack` metadata with allowed files, required tests, required evidence, review triggers, blocker rules, and machine-readable reason codes. Validation reports and quality-gate decisions now include additive `reason_sources` and `reason_codes` fields so downstream surfaces can explain blocked, review-required, and accepted outcomes without parsing prose.

This is not a frozen contract. Agent F owns final contract packaging after policy, PR gate, dashboard, and analytics branches settle.

# Acceptance Criteria

- Existing validation profile names remain backward compatible.
- A migration plan preserves current recipe references.
- The proposal explains what cannot be represented cleanly in the current YAML shape.
- The proposal does not break the v0.2 recipe and profile workflow.

# Migration Notes

- Keep recipe references pointed at validation profile names.
- Keep sign-off profiles command-backed.
- Promote a first-class policy-pack directory only when this YAML shape cannot cleanly express metadata, composition, inheritance, or runtime-specific packaging.
- Treat `reason_sources` as display-ready evidence fields, not as a replacement for deterministic validation and quality-gate decisions.

# References

- `configs/validation_profiles.yaml`
- `recipes/`
