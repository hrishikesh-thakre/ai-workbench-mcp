# Goose Recipe Smoke

Use this smoke when Goose is configured locally with a provider. It asks Goose
to fix the tiny example, records the response through AI Workbench MCP, then
validates and quality-gates the run evidence.

This is the first full lifecycle check after the two-tool smoke passes. It
uses the general engineering acceptance recipe with the `tiny_python_fix`
profile. For the current focused fixture proof path, use the
`fixture_repair_proof` command in `examples/focused-workflows/`.

On slow local models, run `examples/goose-tool-smoke/` first. The full recipe
may need a long shell timeout because it requires an implementation turn plus
multiple MCP tool calls. A local Gemma 4 full smoke took about 22 minutes on
the initial v0.1 alpha machine.

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
  task_metadata.json
  final_prompt.md
  model_selection.json
  model_output.md
  validation_report.json
  revision_decision.json
  run_log.jsonl
```

Call the run accepted only if `validation_report.json` is passed and
sign-off ready, and `revision_decision.json` records
`final_status="accepted"`. If validation fails or the quality gate requests
revision, keep the evidence and treat it as a needs-review run.

Do not commit `runs/`. If you need a public demo artifact, copy only sanitized
evidence into `examples/sample-runs/`.
