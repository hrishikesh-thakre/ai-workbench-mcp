# Event Ledger

`events.jsonl` is a local operation telemetry ledger for Workbench MCP/core calls. It is separate from `run_log.jsonl`.

`run_log.jsonl` records run decisions and status transitions. `events.jsonl` records completed Workbench operations from the final public response envelope.

## Where Events Are Written

Core MCP operations write best-effort events beside their evidence artifacts:

| Operation | Event path |
|---|---|
| `workbench_open_run` | `<run_dir>/events.jsonl` |
| `workbench_select_model` | `<model_selection.json parent>/events.jsonl` |
| `workbench_record_execution` | `<run_dir>/events.jsonl` |
| `workbench_validate_run` | `<out_dir>/events.jsonl` |
| `workbench_quality_gate` | `<run_dir>/events.jsonl` |
| `workbench_analyze_runs` | `<report_dir>/events.jsonl` |

Event writes are best-effort and non-fatal. If the event file cannot be written, the original Workbench operation response is returned normally.

## Event Shape

Each line is one JSON object:

```json
{
  "schema_version": 1,
  "event_id": "unique-event-id",
  "timestamp": "2026-05-13T00:00:00+00:00",
  "event_type": "workbench.operation.completed",
  "source": "ai_workbench_mcp",
  "operation": "workbench_validate_run",
  "status": "passed",
  "ok": true,
  "run_id": "example-run",
  "project": "ai_workbench_mcp",
  "summary": {},
  "artifacts": {},
  "errors": []
}
```

`operation`, `status`, `ok`, `summary`, `artifacts`, and `errors` are copied from the final public response envelope. `run_id` and `project` are convenience fields derived from the response summary or artifact paths when available.

## Local Evidence Boundary

`events.jsonl` may include task summaries, response summaries, and local artifact paths. Event ledgers under ignored `runs/` should stay local and should not be committed unless a future sanitized sample intentionally demonstrates them.

Events are not required sign-off artifacts in v0.2. They are optional evidence for later analytics, CI, and routing feedback work.
