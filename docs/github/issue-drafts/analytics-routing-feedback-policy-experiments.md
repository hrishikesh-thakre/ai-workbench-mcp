# Goal

Use real `routing_feedback_candidates` from `run_metrics.json` to propose bounded model-selection policy experiments.

# Background

The selector can record advisory routing feedback today. Actual routing rule changes should wait until real dogfood evidence shows stable acceptance, review, or failure patterns.

The first bounded docs-only current-tier policy pass is implemented from six isolated low-risk `docs_only` Goose runs on `local_coding`, all accepted. That evidence supports only the narrow `docs_only_current_tier_when_accepted` advisory behavior. It does not justify routing changes for medium-risk work, code changes, `test_fix`, API/contract work, security/privacy-sensitive work, or PR acceptance.

# Acceptance Criteria

- Candidate groups are reviewed by recipe, validation profile, selected tier, risk, and complexity band.
- Proposed policy changes cite acceptance rate, review rate, failure rate, and top failure reasons.
- Golden-case eval reports are considered where relevant.
- No routing rule is changed solely from synthetic sample data.
- Routing feedback remains advisory and does not mutate `selected_tier` by itself.

# References

- `docs/analytics/acceptance-analytics.md`
- `docs/evals/golden-case-harness.md`
- `docs/dogfooding/targeted-docs-only-current-tier-report.md`
- `docs/routing/docs-only-current-tier-policy-design.md`
