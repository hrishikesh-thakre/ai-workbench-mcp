# Codex Tool Smoke

This smoke proves Codex local/IDE can call the existing `ai-workbench-mcp` server. It does not require Codex to edit files.

## Goal

Call the first two MCP tools:

1. `workbench_open_run`
2. `workbench_select_model`

Use Codex host metadata:

```text
execution_host="codex"
```

## Suggested Prompt

```text
Use AI Workbench MCP for a Codex tool smoke. Do not edit tracked files.

1. Call workbench_open_run with:
   project="ai_workbench_mcp"
   task="Codex local MCP tool smoke. Do not edit tracked files."
   run_dir="runs/codex-smoke/tool-smoke"
   risk="low"
   execution_host="codex"

2. Call workbench_select_model with:
   project="ai_workbench_mcp"
   task_type="implement"
   risk="low"
   out="runs/codex-smoke/tool-smoke/model_selection.json"
   complexity_score=4

3. Report the generated artifact paths.
```

Expected evidence:

- `runs/codex-smoke/tool-smoke/task_metadata.json`
- `runs/codex-smoke/tool-smoke/final_prompt.md`
- `runs/codex-smoke/tool-smoke/model_selection.json`
- `runs/codex-smoke/tool-smoke/events.jsonl`

Do not commit `runs/`.
