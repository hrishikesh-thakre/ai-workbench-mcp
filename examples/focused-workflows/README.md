# Focused v0.2 Workflows

These examples show the focused v0.2 Goose recipes and validation profiles.
They are command examples only; local run evidence still belongs under ignored
`runs/`.

Start here when the two-tool Goose smoke passes and you know the shape of the
task. Choose the recipe/profile pair before running the agent:

| Task shape | Recipe | Profile |
|---|---|---|
| Public Markdown or example documentation only | `workbench-docs-only-acceptance.yaml` | `docs_only` |
| Low-risk bug fix with focused regression evidence | `workbench-test-fix-acceptance.yaml` | `low_risk_bug_fix` |
| Bounded package, import, config, tool, recipe, or test maintenance | `workbench-python-package-maintenance.yaml` | `python_package_maintenance` |
| Repo-target repair starting from a focused failing test | `workbench-test-fix-acceptance.yaml` | `test_fix` |
| API or MCP contract change | `workbench-engineering-acceptance.yaml` | `api_contract_change` |
| Security or privacy-sensitive change | `workbench-engineering-acceptance.yaml` | `security_privacy_sensitive` |
| Intentionally broken demo fixture repair proof | `workbench-test-fix-acceptance.yaml` | `fixture_repair_proof` |
| General low-risk implementation with deterministic tests | `workbench-engineering-acceptance.yaml` | `low_risk_coding` |

For change-producing profiles, pass the same exact changed-file list to
execution capture and validation. For `low_risk_bug_fix` and `test_fix`, also
pass the exact focused Python test command through `task_test_command`.

## Docs-Only Changes

Use this when the task is limited to public Markdown or example documentation.
The recipe defaults to the `docs_only` validation profile.

```bash
goose run --recipe ./recipes/workbench-docs-only-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-docs-only \
  --params task="Update the requested public documentation. Do not modify source code." \
  --params risk=low
```

## Python Package Maintenance

Use this for bounded package, import, config, tool, recipe, or test maintenance
inside this package. The recipe defaults to the `python_package_maintenance`
validation profile.

```bash
goose run --recipe ./recipes/workbench-python-package-maintenance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-package-maintenance \
  --params task="Make the requested bounded Python package maintenance change and keep the full test suite passing." \
  --params task_type=implement \
  --params risk=medium
```

## Low-Risk Bug Fix

Use this when a small bug fix has focused regression evidence and the broader
suite must remain green. The test-fix recipe carries the required
`task_test_command`; override the validation profile to `low_risk_bug_fix`.

```bash
goose run --recipe ./recipes/workbench-test-fix-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-low-risk-bug-fix \
  --params task="Fix the requested low-risk bug with the smallest justified change and keep the regression command passing." \
  --params validation_profile=low_risk_bug_fix \
  --params task_test_command="python -m pytest tests/test_target.py -q" \
  --params risk=low
```

## Test-Fix Work

Use this when the task starts from a failing deterministic test signal and the
broader repository test suite must remain green. The recipe defaults to the
`test_fix` validation profile.

```bash
goose run --recipe ./recipes/workbench-test-fix-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-test-fix \
  --params task="Fix the requested failing test signal with the smallest justified change, keep the repo test suite passing, and report the exact validation command." \
  --params task_test_command="python -m pytest tests/test_target.py -q" \
  --params risk=medium
```

For intentionally broken demo fixtures, use the focused fixture proof profile
so the proof validates the target fixture without contradicting repo self-tests
that assert the checked-in fixture starts broken:

```bash
goose run --recipe ./recipes/workbench-test-fix-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-fixture-repair-proof \
  --params task="Fix examples/tiny-python-fix/calculator.py so python -m unittest discover -s examples/tiny-python-fix -p test_*.py passes. Keep the change minimal and do not edit unrelated files." \
  --params validation_profile=fixture_repair_proof \
  --params task_test_command="python -m unittest discover -s examples/tiny-python-fix -p test_*.py" \
  --params analytics_runs_dir=runs/goose-fixture-repair-proof \
  --params analytics_out_dir=runs/goose-fixture-repair-proof/_reports \
  --params risk=low
```

Use the analytics scope parameters for isolated live proofs so unrelated local
smokes or abandoned run folders do not pollute the proof summary.

## API Or Contract Change

Use this when the change touches an API, MCP tool contract, recipe contract, or
other public interface. The profile requires contract-focused tests plus the
full suite.

```bash
goose run --recipe ./recipes/workbench-engineering-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-api-contract-change \
  --params task="Make the requested API or MCP contract change and update contract tests." \
  --params task_type=implement \
  --params risk=medium \
  --params validation_profile=api_contract_change \
  --params validation_strength=strong \
  --params complexity_score=13
```

## Security Or Privacy-Sensitive Change

Use this when the change touches security, privacy, prompts for risk review, or
sensitive data handling. The profile keeps the full suite and public hygiene
checks in the validation envelope.

```bash
goose run --recipe ./recipes/workbench-engineering-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-security-privacy \
  --params task="Make the requested security or privacy-sensitive change and preserve public hygiene checks." \
  --params task_type=implement \
  --params risk=high \
  --params validation_profile=security_privacy_sensitive \
  --params validation_strength=strong \
  --params complexity_score=16
```

## Low-Risk Coding

Use the general engineering acceptance recipe with the `low_risk_coding`
profile when the task is a bounded implementation change with deterministic
test coverage.

```bash
goose run --recipe ./recipes/workbench-engineering-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-low-risk-coding \
  --params task="Make the requested bounded low-risk code change and keep deterministic tests passing." \
  --params task_type=implement \
  --params risk=low \
  --params validation_profile=low_risk_coding \
  --params complexity_score=8
```

## Expected Evidence

Every full acceptance workflow should produce the same Workbench evidence
shape:

```text
runs/<run_id>/
  task_metadata.json
  final_prompt.md
  model_selection.json
  model_output.md
  validation_report.json
  revision_decision.json
  run_log.jsonl
```

Do not commit `runs/`. Public examples should be sanitized and moved under
`examples/sample-runs/`.

Outcome checklist:

- Accepted: deterministic validation passed, sign-off is ready, and the quality gate accepted the run.
- Needs-review or revision: validation or quality-gate evidence says more work or human review is required.
- Blocked or failed: required deterministic evidence is missing or failed; do not present the run as accepted.
