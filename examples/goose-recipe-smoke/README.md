# Goose Recipe Smoke

Use this smoke when Goose is configured locally with a provider. It asks Goose
to fix the tiny example, records the response through AI Workbench MCP, then
validates and quality-gates the run evidence.

On slow local models, run `examples/goose-tool-smoke/` first. The full recipe
may need a long shell timeout because it requires an implementation turn plus
multiple MCP tool calls.

```bash
goose run --recipe ./recipes/workbench-engineering-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-tiny-python-fix \
  --params task="Fix examples/tiny-python-fix/calculator.py so python -m unittest discover -s examples/tiny-python-fix -p test_*.py passes. Keep the change minimal and report the validation result." \
  --params task_type=implement \
  --params risk=low \
  --params validation_strength=medium \
  --params validation_profile=tiny_python_fix \
  --params prompt=implement_request_change_request \
  --params complexity_score=4
```

After the run, inspect:

```text
runs/goose-tiny-python-fix/
  model_selection.json
  model_output.md
  validation_report.json
  revision_decision.json
  run_log.jsonl
```

Do not commit `runs/`. If you need a public demo artifact, copy only sanitized
evidence into `examples/sample-runs/`.
