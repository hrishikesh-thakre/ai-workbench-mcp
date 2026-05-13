# Codex AGENTS.md Snippet

Paste this into a repository `AGENTS.md` when you want Codex to use AI Workbench MCP as the acceptance layer.

```markdown
## AI Workbench MCP Acceptance Loop

When using AI Workbench MCP, keep one shared MCP server: `ai-workbench-mcp`.

For Codex local/IDE runs:

1. Open the run with `workbench_open_run` and `execution_host="codex"`.
2. Select the advisory model/runtime tier with `workbench_select_model`.
3. Perform the requested task with the smallest justified change.
4. Record execution with `workbench_record_execution` and `response_source="codex"`.
5. Validate the run with `workbench_validate_run`.
6. Apply the quality gate with `workbench_quality_gate`.
7. Use `workbench_analyze_runs` when comparing accepted outcomes across runs.

Never claim a run is accepted unless deterministic validation passes and the quality gate returns accepted.

Keep local evidence in `runs/<run_id>/`. Do not commit `runs/` unless the evidence has been intentionally sanitized into `examples/sample-runs/`.
```
