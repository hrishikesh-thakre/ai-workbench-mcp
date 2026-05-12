# START_HERE

Owner: AI Workbench MCP
Status: Draft
Created: 2026-05-12

## 1. Project One-Liner

`ai-workbench-mcp` is a Goose-first, runtime-agnostic trust layer for agentic work. It packages Workbench routing, validation, evidence, quality-gate, and analytics logic so Goose can execute work while Workbench decides whether that work is acceptable.

## 2. Product Direction

The repo is built around this pivot:

```text
Goose-first distribution.
Workbench-owned trust layer.
Runtime-agnostic core.
```

Goose should provide:

- desktop and CLI UX
- provider configuration
- MCP extension hosting
- recipes
- execution loop
- subagents and tool ecosystem

Workbench should provide:

- task and risk policy
- routing recommendations
- deterministic validation
- evidence folders
- quality-loop decisions
- audit records
- cost and accepted-artifact analytics

## 3. Current State

This is an extracted starter repo, not a completed public release.

Copied core:

- `tools/model_select.py`
- `tools/validate_run.py`
- `tools/quality_loop.py`
- `tools/run_analyze.py`
- `tools/model_handoff.py`
- `tools/context_scout.py`
- shared helpers under `tools/`
- starter configs under `configs/`
- focused tests under `tests/`

Not copied:

- private run history
- Cline/VSCodium fork work
- local target-repo paths
- provider secrets
- old experimental docs

## 4. Target User Flow

```text
Goose recipe
  -> workbench_open_run
  -> workbench_select_model
  -> Goose executes the task
  -> workbench_record_execution
  -> workbench_validate_run
  -> workbench_quality_gate
  -> accepted / revise / needs_review
```

The first implementation should expose the Workbench core through a Goose-compatible MCP server.

## 5. Validation Expectations

For this starter extraction, begin with:

```bash
python tools/model_select.py --help
python tools/validate_run.py --help
python tools/quality_loop.py --help
python tools/run_analyze.py --help
pytest
```

Do not treat Goose prose as acceptance evidence. A run is accepted only when the evidence folder has deterministic validation and a quality-gate decision.

## 6. Public Release Rule

Before public release, remove or avoid:

- personal paths
- private run artifacts
- private provider config
- local-only target project references
- broad UI/provider plumbing that competes with Goose

The public repo should look like a Goose-compatible acceptance extension, not an alternative agent platform.
