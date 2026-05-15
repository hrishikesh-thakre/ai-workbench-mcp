# Launch Issue Seeds

These launch issue seeds have been created as public GitHub issues. They should gather real evidence before adding more recipes or broadening provider integrations.

| Issue | Public link |
|---|---|
| `#1` dogfooding: collect 20-50 Goose acceptance runs | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/1 |
| `#2` analytics: promote routing feedback candidates into policy experiments | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/2 |
| `#3` cost evidence: capture provider token and cost metadata | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/3 |
| `#4` policy packs: design first-class validation policy metadata | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/4 |
| `#5` ci: prototype PR acceptance gate | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/5 |
| `#6` docs: record a five-minute Goose acceptance demo | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/6 |

## dogfooding: collect 20-50 Goose acceptance runs

Public issue: https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/1

Run the Phase 5 dogfooding protocol across a mix of docs-only, low-risk coding, package maintenance, and test-fix tasks.

Acceptance criteria:

- At least 20 local Goose runs have complete Workbench evidence folders.
- Outcomes include accepted, review-required, and failed examples.
- No private run folders are committed.
- A short summary identifies which recipes and validation profiles produced accepted work.

## analytics: promote routing feedback candidates into policy experiments

Public issue: https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/2

Use `routing_feedback_candidates` from `run_metrics.json` to propose model-selection policy changes.

Acceptance criteria:

- Candidate groups are reviewed by recipe, validation profile, selected tier, risk, and complexity band.
- Proposed policy changes cite acceptance rate, review rate, failure rate, and top failure reasons.
- No routing rule is changed solely from synthetic sample data.

## cost evidence: capture provider token and cost metadata

Public issue: https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/3

Add real provider cost metadata capture for runs where the provider exposes token or cost evidence.

Acceptance criteria:

- Cost fields remain empty or zero when evidence is unavailable.
- `model_call_metadata.json` is documented with the minimum accepted shape.
- Sample data stays synthetic and does not invent provider costs.

## policy packs: design first-class validation policy metadata

Public issue: https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/4

Evaluate when `configs/validation_profiles.yaml` should become versioned policy packs with metadata, changed-file rules, evidence requirements, and risk labels.

Acceptance criteria:

- Existing validation profile names remain backward compatible.
- A migration plan preserves current recipe references.
- The proposal explains what cannot be represented cleanly in the current YAML shape.

## ci: prototype PR acceptance gate

Public issue: https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/5

Prototype running Workbench validation and quality-gate reporting as a pull-request acceptance check.

Acceptance criteria:

- The prototype can read a prepared evidence folder or create one from a PR workflow.
- It reports deterministic validation status and quality-gate status separately.
- It does not require committing local `runs/` history.

## docs: record a five-minute Goose acceptance demo

Public issue: https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/6

Create a short public demo that shows Goose executing work while Workbench records evidence, validates, gates, and analyzes the run.

Acceptance criteria:

- The demo uses public sample code or a sanitized toy task.
- It shows the six-tool acceptance lifecycle.
- It ends by running analytics over sample or dogfood evidence.
