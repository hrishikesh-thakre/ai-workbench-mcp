# Policy Packs

Status: v0.3 semantic PR acceptance alpha catalog

Policy packs describe the product-facing rules behind the repository's
validation profiles. They make allowed file scope, required tests, evidence,
review triggers, blocker rules, and reason codes easy to read without replacing
deterministic validation or the quality gate.

The first-class catalog lives in `configs/policy_packs.yaml`. Validation
profiles keep their existing names in `configs/validation_profiles.yaml` and
remain the recipe-facing selection surface.

## Acceptance Rule

Do not claim a run is accepted from policy-pack metadata, green CI, scaffold
evidence, a PR comment, or model prose alone.

A Workbench run is accepted only when the run evidence includes:

- `validation_report.json` with `overall_status="passed"`
- `validation_report.json` with `sign_off_ready=true`
- `revision_decision.json` with `final_status="accepted"`

For PRs, the PR gate reports exactly one of `accept`, `needs_review`, or
`block`. Scaffold-only fallback evidence always blocks with
`pr_gate.acceptance_evidence_missing`.

## Catalog

| Policy pack | Use |
|---|---|
| [`docs_only`](docs-only.md) | Bounded public documentation changes. |
| [`low_risk_bug_fix`](low-risk-bug-fix.md) | Bounded production bug fixes with focused regression evidence. |
| [`test_fix`](test-fix.md) | Fixing tests or test-adjacent behavior while keeping the full suite passing. |
| [`api_contract_change`](api-contract-change.md) | API, MCP, tool response, contract, recipe, or packaged-surface changes. |
| [`security_privacy_sensitive`](security-privacy-sensitive.md) | Security, privacy, public hygiene, prompt-safety, secret-boundary, or sensitive configuration changes. |

## Standard Evidence

The policy catalog requires these baseline artifacts for all five packs:

- `model_selection.json`
- `model_output.md`
- `run_log.jsonl`

Acceptance and PR-gate decisions also depend on:

- `validation_report.json`
- `revision_decision.json`

Committed docs and examples must avoid private run history, local absolute
paths, provider secrets, private target-repo names, and raw provider logs.

