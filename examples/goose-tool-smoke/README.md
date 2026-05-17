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

Use this as the first live check after `python -m pip install -e .` and
`goose configure`. A passing tool smoke means the MCP server is reachable from
Goose; it is not an accepted Workbench run because no execution capture,
deterministic validation, or quality gate has run yet.

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

If this smoke fails, check the Goose extension command and package install
before trying a full acceptance recipe.
