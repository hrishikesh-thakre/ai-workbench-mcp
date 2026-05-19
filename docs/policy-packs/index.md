# Policy Packs

Status: v0.3 semantic PR acceptance alpha catalog

Policy packs describe the product-facing rules behind the repository's
validation profiles. They make allowed file scope, required tests, evidence,
review triggers, blocker rules, and reason codes easy to read without replacing
deterministic validation or the quality gate.

The first-class catalog lives in `configs/policy_packs.yaml`. Validation
profiles keep their existing names in `configs/validation_profiles.yaml` and
remain the recipe-facing selection surface.

Version note: each pack still declares `version: v0.2` because that field
identifies the policy metadata contract lineage. The v0.4 closeout
productized, documented, and validated these packs without changing the
machine-readable pack schema.

## Safe Auto-Selection

Goose recipes may call `workbench_select_policy_pack` before
`workbench_select_model` when the user has not explicitly supplied a
`validation_profile` override. The selector returns a recommended policy pack
and recommended validation profile from task metadata. Recipes should pass that
selected validation profile to both `workbench_select_model` and
`workbench_validate_run`.

`validation_profile` remains an override parameter for backward compatibility.
When it is supplied explicitly, recipes should skip advisory auto-selection and
use that profile for both model selection and deterministic validation.

Selector output and profile selection are setup guidance only. They choose the
validation profile when no explicit profile is passed; they are not acceptance
evidence and do not replace deterministic validation or the quality gate.

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

## Closeout Evidence

The v0.4 productization closeout is summarized in
[`docs/dogfooding/v0.4-policy-pack-validation-report.md`](../dogfooding/v0.4-policy-pack-validation-report.md).
It records one real or sanitized case per pack, including fresh isolated
closeout evidence for `low_risk_bug_fix` and `security_privacy_sensitive`,
without committing raw `runs/` evidence.
