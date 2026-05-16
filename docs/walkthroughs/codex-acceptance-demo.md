# Codex Acceptance Demo Walkthrough

This walkthrough proves Codex local/IDE can use the same AI Workbench MCP acceptance layer as Goose.

The target outcome is not a new Codex server. The target outcome is one shared `ai-workbench-mcp` server, one six-tool lifecycle, and evidence that marks:

- `execution_host="codex"`
- `response_source="codex"`

## Safety Boundaries

Use this walkthrough from a single active Codex local/IDE session.

Do not:

- start `ai-workbench-mcp` as a foreground shell command
- ask Codex to launch another Codex session
- delegate this walkthrough to Codex cloud
- run multiple Codex acceptance attempts against the same `run_dir`
- keep retrying a hanging MCP call
- assume Unix-only shell commands such as `cat`; use OS-appropriate file inspection commands

If a tool call hangs or fails unexpectedly, stop that run and start a new run directory after checking `codex mcp list` and the local package install. The committed fallback proof is `examples/sample-runs/accepted-codex-tiny-python-fix/`.

## 1. Configure The MCP Server

Install the package from the repository root:

```bash
python -m pip install -e .
```

Confirm Python can import the package:

```bash
python -c "import ai_workbench_mcp; print('ai-workbench-mcp ready')"
```

Configure Codex to use the existing server command:

```bash
codex mcp add aiWorkbench -- ai-workbench-mcp
codex mcp list
```

Do not run `ai-workbench-mcp` directly in a normal terminal for this demo. It is a stdio MCP server and is meant to be launched by the MCP host.

## Optional Batch Handoff

If you want a visible timer and a generated one-shot prompt before starting Codex, run:

```bash
python tools/codex_live_test_handoff.py --countdown-seconds 15
```

On Windows:

```bat
tools\codex_live_test_handoff.cmd --countdown-seconds 15
```

The helper writes a prompt under `runs/codex-live-handoff/`, prints unique run directories, counts down, and then prints `READY: Start Codex now`. It does not launch Codex or start the MCP stdio server. See `docs/codex/live-test-handoff.md` for details.

## 2. Run The Tool Smoke

Ask Codex:

```text
Use AI Workbench MCP for a Codex tool smoke. Do not edit tracked files.

1. Call workbench_open_run with:
   project="ai_workbench_mcp"
   task="Codex local MCP tool smoke. Do not edit tracked files."
   run_dir="runs/codex-local-demo/tool-smoke"
   risk="low"
   execution_host="codex"

2. Call workbench_select_model with:
   project="ai_workbench_mcp"
   task_type="implement"
   risk="low"
   out="runs/codex-local-demo/tool-smoke/model_selection.json"
   complexity_score=4

3. Report the generated artifact paths.
```

Expected artifacts:

- `runs/codex-local-demo/tool-smoke/task_metadata.json`
- `runs/codex-local-demo/tool-smoke/final_prompt.md`
- `runs/codex-local-demo/tool-smoke/model_selection.json`
- `runs/codex-local-demo/tool-smoke/events.jsonl`

Check that `task_metadata.json` contains `execution_host: codex` and `final_prompt.md` contains `Execution Host: codex`.

## 3. Run The Acceptance Smoke

Use a fresh run directory:

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
   run_dir="runs/codex-local-demo/tiny-python-fix"
   risk="low"
   execution_host="codex"

2. Select the advisory model/runtime tier with workbench_select_model:
   project="ai_workbench_mcp"
   task_type="test"
   risk="low"
   out="runs/codex-local-demo/tiny-python-fix/model_selection.json"
   validation_profile="fixture_repair_proof"
   complexity_score=4

3. Confirm the focused unittest starts failing, then make the minimal code fix.

4. Record execution with workbench_record_execution:
   project="ai_workbench_mcp"
   run_dir="runs/codex-local-demo/tiny-python-fix"
   response_text="Summary:\nFixed examples/tiny-python-fix/calculator.py so add returns the sum of two integers.\n\nFiles touched:\n- examples/tiny-python-fix/calculator.py\n\nValidation run:\n- python -m unittest discover -s examples/tiny-python-fix -p test_*.py -> passed before Workbench validation.\n\nRisks / follow-ups:\n- None."
   response_source="codex"
   files_touched=["examples/tiny-python-fix/calculator.py"]

5. Validate with workbench_validate_run:
   project="ai_workbench_mcp"
   out_dir="runs/codex-local-demo/tiny-python-fix"
   profile="fixture_repair_proof"
   task_test_command="python -m unittest discover -s examples/tiny-python-fix -p test_*.py"
   changed_files=["examples/tiny-python-fix/calculator.py"]

6. Apply workbench_quality_gate:
   project="ai_workbench_mcp"
   run_dir="runs/codex-local-demo/tiny-python-fix"
   mode="auto"
   risk="low"

Do not claim accepted unless validation passes and the quality gate accepts the run.
```

Expected accepted artifacts:

- `task_metadata.json`
- `final_prompt.md`
- `model_selection.json`
- `model_output.md`
- `validation_report.json`
- `revision_decision.json`
- `run_log.jsonl`
- `events.jsonl`

Expected validation details:

- `profile="fixture_repair_proof"`
- `task_test_command` passed
- `changed_file_policy` passed
- no `full_test_suite` command is present

## 4. Analyze Host Outcomes

Run analytics over only the isolated Codex demo parent:

```bash
python tools/run_analyze.py --runs-dir runs/codex-local-demo --out-dir runs/codex-local-demo/_reports
```

Open:

- `runs/codex-local-demo/_reports/run_metrics.json`
- `runs/codex-local-demo/_reports/run_summary.md`
- `runs/codex-local-demo/_reports/run_dashboard.html`

Check:

- `execution_host_counts` includes `codex`
- `response_source_counts` includes `codex`
- `outcome_breakdown.by_execution_host.codex` reflects the new run

## 5. Compare Against The Public Sample

The committed sample at `examples/sample-runs/accepted-codex-tiny-python-fix/` shows the expected sanitized evidence shape.

Use it as a reference only. Do not copy private local `runs/` evidence into git unless it has been intentionally sanitized into `examples/sample-runs/`.

## 6. Failure Handling

If Codex cannot see the MCP tools:

1. Stop the current attempt.
2. Run `codex mcp list`.
3. Confirm the package import command still works.
4. Reopen Codex or reload the IDE extension if needed.
5. Start a new `run_dir`.

If validation fails:

1. Do not claim accepted.
2. Inspect `validation_report.json`.
3. Record the quality-gate result.
4. Keep the failed evidence local unless it is intentionally sanitized as a public sample.

If the run is accepted:

1. Keep `runs/` uncommitted.
2. Use `workbench_analyze_runs` to compare host/source outcomes.
3. Only promote a new sample if it teaches a new public behavior.
