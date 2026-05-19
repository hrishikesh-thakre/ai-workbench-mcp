# Goal

Capture real provider token and cost metadata when providers expose that evidence.

# Background

Cost fields exist in analytics, but empty fields must not be interpreted as free execution. Do not invent or infer costs without provider-backed metadata or token metadata plus configured pricing data.

No v0.3 semantic PR acceptance change is proposed here. Cost/time evidence should remain decoupled from PR acceptance until provider-backed metadata exists and is documented.

# Acceptance Criteria

- Cost amount fields remain empty or zero when evidence is unavailable, with separate status metadata marking the evidence as missing.
- `model_call_metadata.json` is documented with the minimum accepted shape.
- Sample data stays synthetic unless real provider metadata is intentionally public.
- Analytics continues to distinguish no provider cost evidence from free execution.
- PR gate decisions do not depend on missing provider cost metadata.

# Implementation Note

Analytics may expose additive status fields such as `missing`, `zero_cost`, and `priced` for local review. These fields must remain aggregate/provider identity metadata and must not embed raw provider logs, prompts, secrets, or private run history.

# References

- `docs/analytics/acceptance-analytics.md`
