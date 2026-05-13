# Codex Acceptance Smoke

This smoke runs the full six-tool lifecycle through Codex local/IDE using the tiny Python fix example.

## Lifecycle

Use all six MCP tools:

1. `workbench_open_run`
2. `workbench_select_model`
3. Codex performs the tiny Python fix
4. `workbench_record_execution`
5. `workbench_validate_run`
6. `workbench_quality_gate`

Then optionally run `workbench_analyze_runs` to compare host outcomes.

## Suggested Prompt

```text
Use AI Workbench MCP for a Codex acceptance smoke.

Task:
Fix examples/tiny-python-fix/calculator.py so:
python -m unittest discover -s examples/tiny-python-fix -p test_*.py
passes. Keep the change minimal.

Lifecycle:
1. Open the run with workbench_open_run:
   project="ai_workbench_mcp"
   task="Fix examples/tiny-python-fix/calculator.py so python -m unittest discover -s examples/tiny-python-fix -p test_*.py passes."
   run_dir="runs/codex-smoke/tiny-python-fix"
   risk="low"
   execution_host="codex"

2. Select the advisory model/runtime tier with workbench_select_model:
   project="ai_workbench_mcp"
   task_type="implement"
   risk="low"
   out="runs/codex-smoke/tiny-python-fix/model_selection.json"
   validation_profile="tiny_python_fix"
   complexity_score=4

3. Make the minimal code fix.

4. Record execution with workbench_record_execution:
   project="ai_workbench_mcp"
   run_dir="runs/codex-smoke/tiny-python-fix"
   response_text="Summary:\nFixed examples/tiny-python-fix/calculator.py so add returns the sum of two integers.\n\nFiles touched:\n- examples/tiny-python-fix/calculator.py\n\nValidation run:\n- Workbench validation is run in the next step.\n\nRisks / follow-ups:\n- None."
   response_source="codex"
   files_touched=["examples/tiny-python-fix/calculator.py"]

5. Validate with workbench_validate_run:
   project="ai_workbench_mcp"
   out_dir="runs/codex-smoke/tiny-python-fix"
   profile="tiny_python_fix"
   changed_files=["examples/tiny-python-fix/calculator.py"]

6. Apply workbench_quality_gate:
   project="ai_workbench_mcp"
   run_dir="runs/codex-smoke/tiny-python-fix"
   mode="auto"
   risk="low"

Do not claim accepted unless validation passes and the quality gate accepts the run.
```

Expected accepted evidence:

- `task_metadata.json` with `execution_host="codex"`
- `final_prompt.md` with `Execution Host: codex` and compatibility `Mode: codex`
- `model_output.md` with `Execution Host` and `Response Source`
- `validation_report.json`
- `revision_decision.json`
- `run_log.jsonl`

Do not commit `runs/`. A sanitized accepted Codex sample run belongs to a later Codex proof pass.
