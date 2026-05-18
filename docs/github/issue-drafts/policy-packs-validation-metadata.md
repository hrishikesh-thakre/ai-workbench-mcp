# Goal

Keep validation policy metadata first-class while preserving validation profile names and recipe compatibility.

# Background

Validation profiles cover commands, artifacts, review checks, and changed-file policies. v0.3 adds a first-class policy-pack catalog so PR gate comments and downstream surfaces can explain decisions from machine-readable metadata without parsing prose.

# Current v0.3 Shape

Policy packs live in `configs/policy_packs.yaml` and are loaded into validation profiles by `src/ai_workbench_mcp/tools/policy_packs.py`. Recipes still select validation profiles, so existing profile names remain backward compatible.

The current core packs are:

- `docs_only`
- `low_risk_bug_fix`
- `test_fix`
- `api_contract_change`
- `security_privacy_sensitive`

Each core pack declares allowed files, required tests, required evidence, review triggers, blocker rules, and machine-readable reason codes. Validation reports and quality-gate decisions now include additive `reason_sources` and `reason_codes` fields so downstream surfaces can explain blocked, review-required, and accepted outcomes without parsing prose.

This is not a frozen v1 contract. Future policy-pack composition, inheritance, and runtime-specific packaging should be handled as later expansion work.

# Acceptance Criteria

- Existing validation profile names remain backward compatible.
- A migration plan preserves current recipe references.
- The proposal explains what cannot be represented cleanly in the current catalog and validation-profile shape.
- The proposal does not break the v0.2 recipe and profile workflow.

# Migration Notes

- Keep recipe references pointed at validation profile names.
- Keep sign-off profiles command-backed.
- Keep the five core policy pack names stable: `docs_only`, `low_risk_bug_fix`, `test_fix`, `api_contract_change`, and `security_privacy_sensitive`.
- Treat future composition, inheritance, or runtime-specific packaging as a later issue, not v0.3 scope.
- Treat `reason_sources` as display-ready evidence fields, not as a replacement for deterministic validation and quality-gate decisions.

# References

- `configs/policy_packs.yaml`
- `configs/validation_profiles.yaml`
- `recipes/`
