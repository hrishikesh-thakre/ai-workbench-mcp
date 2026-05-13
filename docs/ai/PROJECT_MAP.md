# PROJECT_MAP

Owner: AI Workbench MCP
Status: v0.2 alpha release candidate
Created: 2026-05-12

## 1. Purpose

This repo is the clean public-shaped extraction of the AI Workbench acceptance and audit layer. It is a Goose-compatible MCP extension and recipe set for accepting, validating, auditing, and learning from agentic work.

## 2. Target Architecture

```text
Goose Desktop / CLI / recipe
  |
  v
AI Workbench MCP server
  |
  +--> routing policy
  +--> run evidence
  +--> deterministic validation
  +--> quality gate
  +--> run analytics
  |
  v
runs/<run_id>/
  - task metadata
  - model/runtime selection
  - captured output
  - validation report
  - quality decision
  - run log
```

## 3. Current File Map

| Path | Purpose |
|---|---|
| `src/ai_workbench_mcp/tools/model_select.py` | Routing policy and model tier recommendation logic |
| `src/ai_workbench_mcp/tools/validate_run.py` | Deterministic validation engine |
| `src/ai_workbench_mcp/tools/quality_loop.py` | Acceptance decision, retry/review/escalation logic |
| `src/ai_workbench_mcp/tools/run_analyze.py` | Aggregated run and routing analytics |
| `src/ai_workbench_mcp/tools/model_handoff.py` | Captures external output into Workbench evidence format |
| `src/ai_workbench_mcp/tools/context_scout.py` | Deterministic context/evidence packet builder |
| `src/ai_workbench_mcp/tools/config_loader.py` | Small YAML subset loader used by core tools |
| `src/ai_workbench_mcp/tools/response_format.py` | Response parsing and required-section helpers |
| `tools/` | Backward-compatible CLI wrappers for existing `python tools/*.py` commands |
| `configs/` | Starter routing, validation, context, and quality-loop configuration |
| `prompts/approved/` | Minimal public prompt templates |
| `recipes/` | Goose recipe files for Workbench acceptance workflows |
| `src/ai_workbench_mcp/` | Installable MCP server package, runtime-agnostic core wrappers, and packaged tool logic |
| `tests/` | Focused tests for core contracts, tool payloads, recipes, and MCP runtime smoke |
| `docs/ai/` | Operating docs for the Goose-first pivot |

## 4. MCP Tool Boundary

| MCP Tool | Backing Logic |
|---|---|
| `workbench_open_run` | `ai_workbench_mcp.tools.context_scout` plus task metadata, final prompt, and initial run log |
| `workbench_select_model` | `ai_workbench_mcp.tools.model_select` |
| `workbench_record_execution` | `ai_workbench_mcp.tools.model_handoff` plus runtime metadata capture |
| `workbench_validate_run` | `ai_workbench_mcp.tools.validate_run` |
| `workbench_quality_gate` | `ai_workbench_mcp.tools.quality_loop` |
| `workbench_analyze_runs` | `ai_workbench_mcp.tools.run_analyze` |

## 5. Non-Goals

This repo should not become:

- a Goose competitor
- a generic chat UI
- a generic provider marketplace
- a Cline/VSCodium fork
- a broad MCP marketplace
- a private run-history archive

## 6. Public Hygiene

Do not add:

- `.env` files
- API keys or provider credentials
- private `runs/`
- local machine paths
- target repo names from private work
- generated caches

The public repo should remain small, installable, and easy to explain.

Evidence boundary:

- `runs/` is the local evidence ledger and must stay ignored.
- Committed evidence belongs only under `examples/sample-runs/`.
- Any committed sample run must be sanitized: no local absolute paths, provider secrets, private target-repo names, or raw model-loader logs.
