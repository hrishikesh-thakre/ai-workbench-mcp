# Goose Accepted Run Proof

Evidence folder:

```text
examples/sample-runs/accepted-tiny-python-fix/
```

## Claim

The default Goose-first workflow can produce accepted Workbench evidence when deterministic validation passes and the quality gate accepts the run.

## Task

```text
Fix examples/tiny-python-fix/calculator.py so the unittest validation command passes.
```

## Evidence Summary

| Field | Value |
|---|---|
| Execution host | `goose` by default for historical samples |
| Response source | `goose` |
| Recipe | `workbench-engineering-acceptance.yaml` |
| Validation profile | `run_signoff` in the committed sample |
| Outcome | `accepted` |

Standard artifacts:

```text
task_metadata.json
final_prompt.md
model_selection.json
model_output.md
validation_report.json
revision_decision.json
run_log.jsonl
```

## Acceptance Evidence

`validation_report.json` records:

```text
overall_status = passed
sign_off_ready = true
confidence = 1.0
commands_failed = 0
```

The deterministic command passed:

```bash
python -m unittest discover -s examples/tiny-python-fix -p "test_*.py"
```

`revision_decision.json` records:

```text
final_status = accepted
accepted_pass = 1
blocking_findings = []
```

## Interpretation

This run is accepted because the evidence artifacts support acceptance. The model or agent response alone is not treated as sufficient. Workbench requires a validation report and a quality-gate decision before the public outcome can be called accepted.

## Reproduce A Similar Live Goose Run

After Goose and the MCP server are configured, use:

```bash
goose run --recipe ./recipes/workbench-engineering-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/proof-goose-tiny-python-fix \
  --params task="Fix examples/tiny-python-fix/calculator.py so python -m unittest discover -s examples/tiny-python-fix -p test_*.py passes. Keep the change minimal and report the validation result." \
  --params task_type=implement \
  --params risk=low \
  --params validation_profile=tiny_python_fix \
  --params complexity_score=4
```

Keep the live run under ignored `runs/`. Promote only sanitized evidence if it adds new public value.
