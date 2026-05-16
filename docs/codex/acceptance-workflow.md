# Codex Acceptance Workflow

Codex local/IDE support uses the existing six MCP tools. The only Codex-specific inputs in this pass are host metadata:

- `execution_host="codex"` when opening the run.
- `response_source="codex"` when recording execution.

## Six-Tool Lifecycle

1. `workbench_open_run`
   - Create `runs/<run_id>/`.
   - Pass `execution_host="codex"`.
   - Confirm `task_metadata.json` and `final_prompt.md` include `Execution Host: codex`.

2. `workbench_select_model`
   - Ask Workbench for the advisory model/runtime tier.
   - Treat this as advisory for Codex because Codex may control the actual model/runtime.

3. Codex performs the task
   - Make the requested source or documentation change.
   - Keep the change scoped to the task and the selected validation profile.

4. `workbench_record_execution`
   - Capture Codex's response text into `model_output.md`.
   - Pass `response_source="codex"`.
   - Confirm `model_output.md` includes `Execution Host` and `Response Source`.

5. `workbench_validate_run`
   - Run deterministic validation for the selected profile.
   - Write `validation_report.json`.
   - For the intentionally broken tiny Python fixture, use `fixture_repair_proof` with the exact focused unittest as `task_test_command`.

6. `workbench_quality_gate`
   - Apply the quality gate.
   - Write `revision_decision.json`.
   - Do not claim the run is accepted unless validation passed and the quality gate accepted it.

## Minimal Tool Inputs

```text
workbench_open_run(
  project="ai_workbench_mcp",
  task="<task>",
  run_dir="runs/codex-local-smoke",
  risk="low",
  execution_host="codex"
)

workbench_select_model(
  project="ai_workbench_mcp",
  task_type="implement",
  risk="low",
  out="runs/codex-local-smoke/model_selection.json",
  complexity_score=4
)

workbench_record_execution(
  project="ai_workbench_mcp",
  run_dir="runs/codex-local-smoke",
  response_text="<Codex response>",
  response_source="codex"
)
```

Then run validation and the quality gate with the same run directory.

## Public Sample

See `examples/sample-runs/accepted-codex-tiny-python-fix/` for sanitized accepted evidence from this workflow shape. The sample is committed only because it is sanitized public evidence; private local runs should stay in ignored `runs/` folders.

## Live Walkthrough

Use `docs/walkthroughs/codex-acceptance-demo.md` for live local/IDE testing. It includes guardrails to avoid nested Codex sessions, foreground stdio-server loops, and repeated attempts against the same run directory.
