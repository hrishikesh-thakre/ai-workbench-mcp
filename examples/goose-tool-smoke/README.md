# Goose Tool Smoke

Use this smoke before the full acceptance recipe on slow local models. It asks
Goose to call only two MCP tools:

```text
workbench_open_run
workbench_select_model
```

This proves the Goose CLI can discover and call the AI Workbench MCP server
without waiting for a full agent implementation, validation, quality gate, and
analytics loop.

```bash
goose run --no-session --max-turns 4 --recipe ./recipes/workbench-mcp-tool-smoke.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-tool-smoke \
  --params task="Local Goose MCP tool smoke. Do not edit tracked files." \
  --params risk=low \
  --params complexity_score=4
```

Expected evidence:

```text
runs/goose-tool-smoke/
  task_metadata.json
  final_prompt.md
  model_selection.json
  run_log.jsonl
```

Local Gemma models can take several minutes to warm up. If this minimal smoke
passes, run the full recipe smoke from `examples/goose-recipe-smoke/` with a
longer shell timeout.
