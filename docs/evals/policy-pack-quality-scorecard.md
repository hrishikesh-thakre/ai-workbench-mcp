# Policy Pack Quality Scorecard

Status: internal eval metadata only
Scope: v0.4 policy-pack productization review

This scorecard is a documentation and eval aid for reviewing the five
first-class policy packs in `configs/policy_packs.yaml`.

It is not an acceptance gate and does not affect validation, quality gate,
model selection, PR gate decisions, routing policy, or any runtime behavior.

Workbench acceptance remains defined by deterministic validation plus a
quality-gate decision. For PR-facing outcomes, `accept` still requires
`validation_report.json` with passing sign-off evidence and
`revision_decision.json` with an accepted final status. This scorecard does not
replace those artifacts.

## Inputs Reviewed

- `configs/policy_packs.yaml`
- `configs/validation_profiles.yaml`
- `docs/contracts/v0.3-contract-baseline.md`
- `docs/dogfooding/phase5-final-report.md`
- `docs/dogfooding/v0.4-policy-pack-validation-report.md`

## Rating Scale

Scores are 1 to 5.

For clarity, strictness, and evidence quality, higher is better.

For false-positive risk, false-negative risk, and setup friction, higher means
more risk or more friction.

False-positive risk means the pack may accept or appear to support work that
should have been reviewed or blocked. False-negative risk means the pack may
push acceptable work into review or block. Setup friction reflects how much
task-specific evidence, test setup, and pack selection discipline the user must
provide before the pack is useful.

## Summary Matrix

| Policy pack | Clarity | Strictness | False-positive risk | False-negative risk | Setup friction | Evidence quality |
|---|---:|---:|---:|---:|---:|---:|
| `docs_only` | 5 | 5 | 1 | 2 | 1 | 4 |
| `low_risk_bug_fix` | 4 | 4 | 2 | 3 | 4 | 5 |
| `test_fix` | 4 | 4 | 2 | 3 | 4 | 5 |
| `api_contract_change` | 4 | 5 | 2 | 3 | 3 | 5 |
| `security_privacy_sensitive` | 4 | 5 | 3 | 4 | 4 | 4 |

## Pack Notes

### `docs_only`

This is the clearest and lowest-friction pack. The catalog and validation
profile both limit the changed-file surface to Markdown documentation and
examples, and the profile explicitly forbids source, tool, test, config,
recipe, packaging, and requirements changes. Required tests are narrow:
public-doc existence checks and recipe/policy discovery tests.

Strictness is high because exact changed-file evidence is required, non-empty
changed-file evidence is required, and source/config changes are blocker-class
policy failures. False-positive risk is low because the file boundary is easy
to inspect. False-negative risk is moderate-low: valid docs changes can still
be blocked if worktree diff evidence is unavailable or underreported.

Evidence quality is good but intentionally scoped. The pack requires
`model_selection.json`, `model_output.md`, and `run_log.jsonl`; acceptance still
depends on validation and quality-gate artifacts produced later in the run.

### `low_risk_bug_fix`

This pack is clear but depends heavily on a correctly supplied
`task_test_command`. The catalog requires focused task evidence, pytest
collection, the full suite, and a Workbench tool help smoke. The validation
profile allows bounded Python, test, example, docs, and README changes.

Strictness is strong because missing or failed focused commands, failed full
suite runs, missing changed-file evidence, and unreported diffs block. The
main false-positive risk is misclassification: a change labeled low-risk may
still touch behavior with broader product impact. The main false-negative risk
is test brittleness or an overly narrow focused command that does not match the
task cleanly.

Evidence quality is high when used correctly. Phase 5 repeatedly found focused
test command failures and exact-diff failures to be useful deterministic
signals, and the v0.4 closeout added a fresh accepted aggregate case for this
pack. The contract baseline keeps validation and quality-gate evidence
authoritative.

### `test_fix`

This pack is similar to `low_risk_bug_fix` but more specifically oriented
toward repairing tests while keeping the full project test suite passing. It
requires a task-specific test command, pytest collection, the full suite, and
recipe/policy discovery tests.

Strictness is strong because it combines focused repair evidence with the full
suite and changed-file evidence. False-positive risk is low to moderate: a test
repair can still weaken test intent while passing the suite unless review
checks catch the model output issue. False-negative risk is moderate because
legitimate fixture or demo repairs may need a more focused proof profile rather
than this repo-target profile.

Evidence quality is high for repo-target repairs. The Phase 5 report calls out
focused test commands and changed-file policy as repeated useful signals.

### `api_contract_change`

This pack has a broad but well-named surface: core package code, tools, tests,
configs, recipes, docs, README, package metadata, and server metadata. It
requires contract-focused tests plus the full test suite.

Strictness is very high because contract test absence or failure blocks, as
does full-suite failure, missing changed-file evidence, or unreported diffs.
False-positive risk is low to moderate because contract tests are explicit, but
v0.3 contracts are still alpha and consumers are required to tolerate additive
fields and unknown reason codes. False-negative risk is moderate because valid
additive contract changes may fail old assumptions until tests and docs move
together.

Evidence quality is high. This pack aligns closely with the v0.3 contract
baseline: policy metadata is cataloged, validation profiles remain the
selection surface, and complete acceptance evidence remains separate from the
catalog.

### `security_privacy_sensitive`

This is the strictest and highest-review pack. It covers source, tools, tests,
configs, prompts, docs, README, package metadata, and server metadata, while
forbidding `.env`, `.env.*`, `runs/**`, and local model registry overrides. It
requires the security prompt catalog check, public hygiene tests, and the full
suite.

Strictness is very high because public hygiene, full-suite failure, private or
secret file changes, missing changed-file evidence, and unreported diffs are
blockers. False-positive risk remains moderate because security and privacy
review often depends on threat modeling beyond deterministic tests. The pack
mitigates this with review triggers for alternate-model review and
high-risk/security/privacy prompts, but those are review signals rather than a
proof of safety.

False-negative risk and setup friction are both high relative to the other
packs. This is appropriate for the risk class: acceptable work may require
manual review even after deterministic checks pass. The v0.4 closeout confirms
that behavior with a fresh aggregate case: deterministic validation passed, and
the quality gate still required security/privacy review. Evidence quality is
good, but not as complete as a full security assessment unless paired with
review output and the normal validation plus quality-gate artifacts.

## Cross-Pack Findings

- All five first-class packs require the same core execution evidence:
  `model_selection.json`, `model_output.md`, and `run_log.jsonl`.
- All five product profiles require non-empty changed-file evidence and actual
  diff evidence, which directly addresses the Phase 5 no-op and underreported
  diff failures.
- `docs_only` is the most productized pack because its allowed and forbidden
  file boundaries are narrow and easy to explain.
- `low_risk_bug_fix` and `test_fix` are strong when `task_test_command` is
  supplied, but that requirement is also their main setup burden.
- `api_contract_change` is strict and well-aligned with the v0.3 baseline, but
  contract alpha status means review context remains important.
- `security_privacy_sensitive` should be expected to produce more review
  outcomes. That is a product feature, not a scorecard failure.

## Assumptions

- Scores reflect the current v0.3 catalog and validation profile shape, not a
  future v1-stable policy schema.
- Phase 5 aggregate evidence is used only as qualitative support for policy
  interpretation. It does not change routing policy or acceptance rules.
- The scorecard intentionally avoids private run evidence and local machine
  details.
