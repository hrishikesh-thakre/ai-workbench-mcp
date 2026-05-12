# AI Workbench MCP

[![License](https://img.shields.io/badge/License-Apache--2.0-blue.svg)](LICENSE)

AI Workbench MCP is a Goose-first, runtime-agnostic acceptance layer for agentic engineering work.
Licensed under Apache-2.0.

It is not another general-purpose agent runner. Goose owns the desktop, CLI, provider ecosystem, recipes, MCP extensions, and execution loop. This repo provides the complementary trust layer:

- model and runtime routing policy
- deterministic validation gates
- run evidence folders
- quality-loop decisions
- audit trail
- cost and acceptance analytics

Target shape:

```text
Goose Desktop / CLI / recipe
  -> AI Workbench MCP tools
  -> run evidence
  -> deterministic validation
  -> quality gate
  -> accepted artifact analytics
```

Current status: Phase 2.5 MCP MVP. The core Workbench operations and evidence lifecycle tools are callable directly from Python and exposed through a Goose-compatible stdio MCP server.

Start with [START_HERE.md](docs/ai/START_HERE.md).

## Install

From the repository root:

```bash
python -m pip install -e .
```

For development and tests:

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Goose MCP Setup

Register AI Workbench MCP as a command-line stdio extension:

```bash
goose configure
```

Choose:

- `Add Extension`
- `Command-line Extension`
- Name: `AI Workbench MCP`
- Command: `ai-workbench-mcp`
- Timeout: `300`

The server exposes:

- `workbench_open_run`
- `workbench_select_model`
- `workbench_record_execution`
- `workbench_validate_run`
- `workbench_quality_gate`
- `workbench_analyze_runs`

## Manual Tool Examples

Example Goose prompts:

- `Call workbench_open_run with project ai_workbench_mcp, task "Document the current lifecycle tools", run_dir runs/manual, prompt implement_request_change_request, and risk medium.`
- `Call workbench_select_model with project ai_workbench_mcp, task_type implement, risk medium, out runs/manual/model_selection.json, prompt implement_request_change_request, complexity_score 13.`
- `Call workbench_record_execution with project ai_workbench_mcp, run_dir runs/manual, and response_text "Summary:\nCaptured the manual smoke.\n\nFiles touched:\n- None.\n\nValidation run:\n- Not run.\n\nRisks / follow-ups:\n- None."`
- `Call workbench_validate_run with project ai_workbench_mcp, profile run_signoff, out_dir runs/manual.`
- `Call workbench_quality_gate with project ai_workbench_mcp, run_dir runs/manual, mode auto, risk medium.`
- `Call workbench_analyze_runs with runs_dir runs and out_dir runs/_reports.`

## Recipe

The first Goose recipe is available at [recipes/workbench-engineering-acceptance.yaml](recipes/workbench-engineering-acceptance.yaml).

Run it with:

```bash
goose run --recipe ./recipes/workbench-engineering-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/manual \
  --params task="Implement the requested bounded change" \
  --params risk=medium
```

The recipe uses the `ai-workbench-mcp` stdio extension and calls run setup, model selection, execution capture, validation, quality gate, and run analysis in order.
