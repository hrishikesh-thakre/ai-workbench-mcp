# Focused v0.2 Workflows

These examples show the focused v0.2 Goose recipes and validation profiles.
They are command examples only; local run evidence still belongs under ignored
`runs/`.

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
