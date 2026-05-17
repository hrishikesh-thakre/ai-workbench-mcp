# Codex Local/IDE Run Proof

Evidence folder:

```text
examples/sample-runs/accepted-codex-tiny-python-fix/
```

## Claim

Codex local/IDE can use the same `ai-workbench-mcp` server and evidence lifecycle as Goose. Codex support does not require a separate Codex-specific MCP server.

## Task

```text
Fix examples/tiny-python-fix/calculator.py so the unittest validation command passes.
```

## Evidence Summary

| Field | Value |
|---|---|
| Execution host | `codex` |
| Response source | `codex` |
| Recipe | `workbench-engineering-acceptance.yaml` |
| Validation profile | `tiny_python_fix` |
| Outcome | `accepted` |

Standard artifacts:

```text
task_metadata.json
final_prompt.md
model_selection.json
model_output.md
validation_report.json
revision_decision.json
run_log.jsonl
```

## Host Portability Evidence

`task_metadata.json` records:

```text
execution_host = codex
```

`model_output.md` records:

```text
Response Source = codex
Status = response_captured
```

`validation_report.json` includes explicit metadata checks:

```text
execution_host_metadata = passed
response_source_metadata = passed
```

## Acceptance Evidence

`validation_report.json` records:

```text
overall_status = passed
sign_off_ready = true
confidence = 1.0
commands_failed = 0
```

The deterministic command passed:

```bash
python -m unittest discover -s examples/tiny-python-fix -p "test_*.py"
```

`revision_decision.json` records:

```text
final_status = accepted
accepted_pass = 1
blocking_findings = []
```

## Interpretation

This sample proves the Workbench evidence layer is host-aware. Codex controls its own execution runtime, and Workbench records Codex as the execution host and response source. `workbench_select_model` remains advisory for Codex; acceptance still comes from validation and the quality gate.

## Fresh Live Codex Proof

For a fresh local/IDE proof, use:

```bash
python tools/codex_live_test_handoff.py --countdown-seconds 15
```

Then follow:

```text
docs/codex/live-test-handoff.md
docs/walkthroughs/codex-acceptance-demo.md
```

Keep live evidence under ignored `runs/` unless it is intentionally sanitized into `examples/sample-runs/`.
