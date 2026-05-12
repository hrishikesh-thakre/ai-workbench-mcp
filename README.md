# AI Workbench MCP

[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

`ai-workbench-mcp` is a Goose-compatible MCP extension that turns AI coding work into evidence-backed accepted runs.

Goose executes the work. AI Workbench records what happened, validates it, runs a quality gate, and decides whether the result should be trusted.

## Problem

AI coding agents can produce useful work, but "done" is not the same as accepted. A useful acceptance workflow needs reproducible evidence:

- what task was requested
- which model/runtime was selected
- what the agent produced
- which deterministic checks ran
- whether the quality gate accepted, rejected, or requested review
- where the audit trail lives

AI Workbench MCP provides that acceptance and audit layer.

## Why Goose + Acceptance Gates

Goose already owns the agent execution surface: CLI, desktop, providers, recipes, MCP hosting, and the agent loop.

AI Workbench MCP stays complementary:

- opens run evidence folders
- recommends model/runtime tiers
- records model or Goose output
- runs deterministic validation
- makes quality-gate decisions
- summarizes accepted-run analytics

It does not provide a chat UI, editor fork, provider marketplace, or general agent runner.

## 5-Minute Quickstart

Install from the repository root:

```bash
python -m pip install -e .
```

Register the MCP server in Goose:

```bash
goose configure
```

Choose:

- `Add Extension`
- `Command-line Extension`
- Name: `AI Workbench MCP`
- Command: `ai-workbench-mcp`
- Timeout: `300`

On slower local models, start with the two-tool smoke to verify Goose can reach the MCP server:

```bash
goose run --no-session --max-turns 4 --recipe ./recipes/workbench-mcp-tool-smoke.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-tool-smoke \
  --params task="Local Goose MCP tool smoke. Do not edit tracked files." \
  --params risk=low \
  --params complexity_score=4
```

Then run the full sample recipe smoke after Goose has a provider configured:

```bash
goose run --recipe ./recipes/workbench-engineering-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/goose-tiny-python-fix \
  --params task="Fix examples/tiny-python-fix/calculator.py so python -m unittest discover -s examples/tiny-python-fix -p test_*.py passes. Keep the change minimal and report the validation result." \
  --params task_type=implement \
  --params risk=low \
  --params validation_profile=tiny_python_fix \
  --params complexity_score=4
```

Inspect the evidence folder:

```text
runs/goose-tiny-python-fix/
  task_metadata.json
  final_prompt.md
  model_selection.json
  model_output.md
  validation_report.json
  revision_decision.json
  run_log.jsonl
```

Do not commit `runs/`. It is the local evidence ledger.

## Six MCP Tools

```text
workbench_open_run
  -> creates the run folder, task metadata, final prompt, context packet, and initial run log

workbench_select_model
  -> recommends a model/runtime tier and writes model_selection.json

workbench_record_execution
  -> captures raw Goose/model response text into model_output.md and appends run_log.jsonl

workbench_validate_run
  -> runs deterministic validation and writes validation_report.json

workbench_quality_gate
  -> accepts, rejects, or requests review and writes revision_decision.json

workbench_analyze_runs
  -> summarizes accepted-run metrics under runs/_reports
```

## Workflow

```text
Goose recipe
  -> workbench_open_run
  -> workbench_select_model
  -> Goose performs the task
  -> workbench_record_execution
  -> workbench_validate_run
  -> workbench_quality_gate
  -> workbench_analyze_runs
```

A run is accepted only when deterministic validation and the quality gate support acceptance.

## Examples

- [Tiny Python fix](examples/tiny-python-fix/): a deliberately broken one-function project for recipe smoke tests.
- [Goose tool smoke](examples/goose-tool-smoke/): two-tool live smoke for slow local models.
- [Goose recipe smoke](examples/goose-recipe-smoke/): exact command for a low-risk Goose acceptance run.
- [Sample accepted run](examples/sample-runs/accepted-tiny-python-fix/): sanitized committed evidence showing an accepted run folder.

## Development

Install development dependencies:

```bash
python -m pip install -e ".[dev]"
```

Run tests:

```bash
python -m pytest -q -p no:cacheprovider
```

Run scaffold validation:

```bash
python tools/validate_run.py --project ai_workbench_mcp --profile scaffold --out-dir runs/scaffold-smoke
```

## Roadmap

- `v0.1.0-alpha`: first public Goose MCP acceptance workflow.
- `v0.2`: stronger recipe library.
- `v0.3`: validation policy packs.
- `v0.4`: accepted-artifact analytics.
- `v0.5`: CI mode for PR acceptance.
- `v1.0`: stable MCP contracts and recipe API.

## GitHub Topics

Suggested repository topics:

```text
goose
mcp
model-context-protocol
ai-agents
agentic-ai
coding-agents
developer-tools
validation
evals
quality-gates
audit-trail
```

## License

Apache-2.0. See [LICENSE](LICENSE).
