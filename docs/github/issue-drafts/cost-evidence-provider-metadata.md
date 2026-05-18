# Goal

Capture real provider token and cost metadata when providers expose that evidence.

# Background

Cost fields exist in analytics, but empty or zero values currently mean no provider cost evidence was found. Do not invent or infer costs without provider-backed metadata.

No v0.3 semantic PR acceptance change is proposed here. Cost/time evidence should remain decoupled from PR acceptance until provider-backed metadata exists and is documented.

# Acceptance Criteria

- Cost fields remain empty or zero when evidence is unavailable.
- `model_call_metadata.json` is documented with the minimum accepted shape.
- Sample data stays synthetic unless real provider metadata is intentionally public.
- Analytics continues to distinguish no provider cost evidence from free execution.
- PR gate decisions do not depend on missing provider cost metadata.

# References

- `docs/analytics/acceptance-analytics.md`
