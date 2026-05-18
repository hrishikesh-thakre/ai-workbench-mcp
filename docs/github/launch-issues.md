# Launch Issue Seeds

These launch issue seeds are public GitHub issues. This page is now a historical launch backlog plus current v0.3 status, not a fresh list of work to start from scratch.

The current product focus is the v0.3 Semantic PR Acceptance Alpha: real Workbench evidence for PR acceptance, five first-class policy packs, a copy-paste GitHub workflow, bootstrap assets, and sanitized PR gate outcome demos. The latest published package remains `ai-workbench-mcp==0.2.0a0`; do not imply a v0.3 package release is already published.

| Issue | Public link | Current disposition |
|---|---|---|
| `#1` dogfooding: collect 20-50 Goose acceptance runs | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/1 | Complete/historical; Phase 5 closed with 31 complete evidence runs |
| `#2` analytics: promote routing feedback candidates into policy experiments | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/2 | Keep open only for bounded routing-policy experiments |
| `#3` cost evidence: capture provider token and cost metadata | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/3 | Keep open; not blocking v0.3 semantic PR acceptance |
| `#4` policy packs: design first-class validation policy metadata | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/4 | v0.3 catalog exists; close or retitle only if future policy composition remains in scope |
| `#5` ci: prototype PR acceptance gate | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/5 | Retitle/scope to v0.3 Semantic PR Acceptance Alpha |
| `#6` docs: record a five-minute Goose acceptance demo | https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/6 | Written walkthrough/proof path exists; only a published video remains if required |

Exact proposed issue comments are recorded in `docs/github/v0.3-issue-hygiene-report.md`.

## dogfooding: collect 20-50 Goose acceptance runs

Public issue: https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/1

Current repo status: complete/historical. Phase 5 evidence collection is complete in `docs/dogfooding/phase5-final-report.md` with 31 complete evidence runs, including 29 live Goose runs and 2 deterministic controls. The next repository work should use the closeout evidence for bounded routing-policy experiments rather than broad collection.

Original acceptance criteria status:

- At least 20 local Goose runs have complete Workbench evidence folders: met.
- Outcomes include accepted, review-required, and failed examples: accepted and review-required evidence is present; no failed public outcomes were recorded in the closeout.
- No private run folders are committed: met.
- A short summary identifies which recipes and validation profiles produced accepted work: met in the Phase 5 closeout report.

## analytics: promote routing feedback candidates into policy experiments

Public issue: https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/2

Current repo status: still valid, but bounded. The first docs-only current-tier advisory policy is implemented from isolated low-risk `docs_only` evidence. Keep routing feedback advisory and do not generalize it to medium-risk work, code changes, `test_fix`, security/privacy-sensitive work, or PR acceptance.

Acceptance criteria:

- Candidate groups are reviewed by recipe, validation profile, selected tier, risk, and complexity band.
- Proposed policy changes cite acceptance rate, review rate, failure rate, and top failure reasons.
- No routing rule is changed solely from synthetic sample data.

## cost evidence: capture provider token and cost metadata

Public issue: https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/3

Current repo status: open and decoupled from v0.3 PR acceptance. Cost/time evidence remains useful, but PR acceptance should not depend on provider-backed cost metadata.

Acceptance criteria:

- Cost fields remain empty or zero when evidence is unavailable.
- `model_call_metadata.json` is documented with the minimum accepted shape.
- Sample data stays synthetic and does not invent provider costs.
- Analytics continues to distinguish no provider cost evidence from free execution.

## policy packs: design first-class validation policy metadata

Public issue: https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/4

Current repo status: v0.3 has a first-class catalog at `configs/policy_packs.yaml` with loader support. Existing validation profile names remain backward compatible, and recipes still select validation profiles. The five first-class policy packs are `docs_only`, `low_risk_bug_fix`, `test_fix`, `api_contract_change`, and `security_privacy_sensitive`.

Acceptance criteria status:

- Existing validation profile names remain backward compatible: met.
- A migration plan preserves current recipe references: met by keeping recipes pointed at validation profile names.
- The proposal explains what cannot be represented cleanly in the current catalog and validation-profile shape: defer remaining composition/inheritance questions to a later policy expansion issue.

## ci: prototype PR acceptance gate

Public issue: https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/5

Current repo status: update scope from prototype to v0.3 Semantic PR Acceptance Alpha. The PR gate now needs to be described as a Workbench-evidence acceptance surface, not merely repo self-validation.

v0.3 acceptance criteria:

- The PR gate reads a real Workbench acceptance run for a PR.
- It reports exactly one of `accept`, `needs_review`, or `block`.
- It shows deterministic validation status and quality-gate status separately.
- It reports whether `validation_report.json` and `revision_decision.json` are present.
- It states why the decision happened and gives the required next action.
- It blocks scaffold-only fallback evidence with `pr_gate.acceptance_evidence_missing`.
- It renders `pr_comment.md` and `pr_decision.json` as workflow artifacts.
- It posts or updates one marker-based PR comment only for same-repository pull requests.

Out of scope for this issue: GitHub Checks API integration, broad enforcement policy, fork-comment strategy changes, GEPA, provider plumbing, and extra host integrations.

## docs: record a five-minute Goose acceptance demo

Public issue: https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/6

Current repo status: written demo material exists. `docs/walkthroughs/goose-acceptance-demo.md` is the recording-ready public runbook, and proof material under `docs/proof/` covers accepted, review-required, and PR gate outcome demos. If this issue requires a published video, the remaining work should be narrowed to recording and linking that artifact.

Acceptance criteria status:

- The demo uses public sample code or sanitized toy evidence: met.
- It shows the six-tool acceptance lifecycle: met in the walkthrough.
- It inspects the evidence folder: met.
- It ends by running analytics over sample or dogfood evidence: met.
- It references the written walkthrough: met.
