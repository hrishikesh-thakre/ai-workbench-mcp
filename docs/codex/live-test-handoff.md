# Codex Live-Test Handoff

Use this helper when you want a bounded way to test Codex local/IDE without starting a nested Codex session from an active Codex run.

The helper:

- checks that the Python package imports
- checks whether the `ai-workbench-mcp` command is on `PATH`
- optionally runs `codex mcp list`
- writes a one-shot Codex prompt under ignored `runs/`
- uses one unique parent directory for the tool smoke and acceptance smoke
- prints a visible countdown
- tells you when to start Codex
- prints the exact result-check command to run after Codex finishes

It does not:

- launch Codex
- start `ai-workbench-mcp` as a foreground stdio server
- call Workbench MCP tools itself
- edit tracked files

## Windows Batch Flow

From the repository root:

```bat
tools\codex_live_test_handoff.cmd --countdown-seconds 15
```

If you are using the IDE extension and do not have the Codex CLI on `PATH`, skip the CLI check:

```bat
tools\codex_live_test_handoff.cmd --skip-codex-cli-check --countdown-seconds 15
```

When the helper prints:

```text
READY: Start Codex now, then use the generated prompt.
```

start or reload Codex local/IDE and use the printed prompt or the prompt file written under `runs/codex-live-handoff/`.

After Codex finishes, run the exact checker command printed by the helper.

## Cross-Platform Python Flow

```bash
python tools/codex_live_test_handoff.py --countdown-seconds 15
```

Use a deterministic suffix when you want predictable local evidence paths:

```bash
python tools/codex_live_test_handoff.py --stamp 20260513-120000 --countdown-seconds 15
```

The generated run directories look like:

```text
runs/codex-live-20260513-120000/tool-smoke
runs/codex-live-20260513-120000/tiny-python-fix
```

If the parent or either child directory already exists, the helper refuses to continue. This prevents repeated attempts from overwriting or mixing evidence.

## After The Codex Run

Check the specific live-test evidence folder:

```bash
python tools/check_codex_live_result.py --stamp 20260513-120000
```

Or pass the exact directories printed by the handoff helper:

```bash
python tools/check_codex_live_result.py \
  --tool-run-dir runs/codex-live-20260513-120000/tool-smoke \
  --acceptance-run-dir runs/codex-live-20260513-120000/tiny-python-fix
```

On Windows:

```bat
tools\check_codex_live_result.cmd --stamp 20260513-120000
```

The checker prints `RESULT: PASS` only when:

- the tool-smoke run has `execution_host="codex"`
- the acceptance run has `execution_host="codex"` and `response_source="codex"`
- deterministic validation passed and is sign-off ready
- the quality gate wrote `final_status="accepted"`
- the event ledger contains the expected Workbench tool operations

Analyze only the isolated live-test parent:

```bash
python tools/run_analyze.py --runs-dir runs/codex-live-20260513-120000 --out-dir runs/codex-live-20260513-120000/_reports
```

Check:

- `execution_host_counts` includes `codex`
- `response_source_counts` includes `codex`
- the Codex acceptance run has a passing `validation_report.json`
- the quality gate wrote `revision_decision.json` with `final_status="accepted"`

Keep `runs/` out of git. Promote only intentionally sanitized examples into `examples/sample-runs/`.
