# Goal

Run the Phase 5 dogfooding protocol across real Goose acceptance tasks and summarize what the evidence shows.

# Status

Complete/historical for Phase 5. `docs/dogfooding/phase5-final-report.md` records 31 complete evidence runs, including 29 live Goose runs and 2 deterministic controls. Raw local `runs/` evidence remains out of git.

# Background

Workbench should improve from accepted artifacts, but synthetic samples should not drive routing policy. This issue collects the real run history needed for future routing decisions.

# Acceptance Criteria

- At least 20 local Goose runs have complete Workbench evidence folders.
- Outcomes include accepted, review-required, and failed examples.
- At least three task types are represented.
- No private run folders are committed.
- A short summary identifies which recipes and validation profiles produced accepted work.

# Recommended Disposition

Close as complete/historical. Follow-up routing work should use bounded, evidence-backed policy experiments rather than more broad dogfood collection.

# References

- `docs/dogfooding/phase5-dogfooding.md`
- `docs/analytics/acceptance-analytics.md`
- `docs/dogfooding/phase5-final-report.md`
