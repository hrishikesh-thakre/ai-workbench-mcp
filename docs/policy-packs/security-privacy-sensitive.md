# security_privacy_sensitive Policy Pack

## Use when

Use `security_privacy_sensitive` for security or privacy-sensitive changes,
public hygiene boundaries, prompt safety, secret handling, sensitive
configuration, provider-adjacent behavior, or anything that could expose private
run history, local paths, secrets, or raw provider logs.

## Do not use when

Do not use it to auto-accept routine docs, bug-fix, or test-only work. Do not use
it to weaken review: this pack is intentionally conservative and commonly
requires human review even after deterministic checks pass.

## Accept condition

Accept only when security prompt catalog checks pass, public hygiene tests pass,
the full suite passes, forbidden private or secret files are not changed,
required evidence is present, and the quality gate accepts the run.

## Needs review condition

Needs review when deterministic checks pass but the pack triggers alternate
model review, high-risk security/privacy prompt review, model output status
review, or captured response format review without blocker-severity evidence.

## Block condition

Block when public hygiene tests fail, the full suite fails, private or secret
files changed, `runs/**` or local model registry overrides are touched, changed
file evidence is missing, unreported diffs exist, or required acceptance
artifacts are missing.

## Required evidence

- `model_selection.json`
- `model_output.md`
- `run_log.jsonl`
- `validation_report.json`
- `revision_decision.json`

Required validation commands from the profile:

- `security_prompt_catalog`
- `public_hygiene_tests`
- `full_test_suite`

## Example PR comment

```text
Decision: Needs Review
Why: security_privacy_sensitive validation passed, but high-risk review was triggered.
Required next action: Human security/privacy review before merge.
Evidence present: validation_report yes, revision_decision yes
Reason codes: security_privacy_sensitive.required_tests_passed
```

## Minimal command

```bash
python tools/validate_run.py --project ai_workbench_mcp --profile security_privacy_sensitive --out-dir runs/<run_id> --changed-files src/<security_change>.py tests/<security_test>.py
python tools/quality_loop.py --run-dir runs/<run_id>
```

## Common failure modes

- Touching `.env`, `.env.*`, `runs/**`, or `configs/model_registry.local.yaml`.
- Publishing local absolute paths, provider secrets, private target-repo names,
  raw model-loader logs, or unreviewed run evidence.
- Passing tests but treating that as a substitute for security/privacy review.
- Missing the approved `security_privacy_risk_review.md` prompt.

## Compact examples

| Outcome | Example |
|---|---|
| Accepted | A public hygiene test update passes prompt catalog checks, hygiene tests, the full suite, and the quality gate accepts. |
| Needs review | Validation passes, but the change modifies prompt safety behavior and triggers high-risk review. |
| Blocked | The diff includes `.env`, `runs/<run_id>/`, or another private/secret artifact. |
