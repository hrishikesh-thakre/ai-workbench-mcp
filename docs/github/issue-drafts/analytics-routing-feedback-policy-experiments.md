# Goal

Use real `routing_feedback_candidates` from `run_metrics.json` to propose bounded model-selection policy experiments.

# Background

The selector can record advisory routing feedback today. Actual routing rule changes should wait until real dogfood evidence shows stable acceptance, review, or failure patterns.

# Acceptance Criteria

- Candidate groups are reviewed by recipe, validation profile, selected tier, risk, and complexity band.
- Proposed policy changes cite acceptance rate, review rate, failure rate, and top failure reasons.
- Golden-case eval reports are considered where relevant.
- No routing rule is changed solely from synthetic sample data.

# References

- `docs/analytics/acceptance-analytics.md`
- `docs/evals/golden-case-harness.md`
