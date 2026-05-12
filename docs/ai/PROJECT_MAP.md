# PROJECT_MAP

Owner: AI Workbench MCP
Status: Draft
Created: 2026-05-12

## 1. Purpose

This repo is the clean public-shaped extraction of the AI Workbench trust layer. It should become a Goose-compatible MCP extension and recipe set for accepting, validating, auditing, and learning from agentic work.

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
| `tools/model_select.py` | Existing routing policy and model tier recommendation logic |
| `tools/validate_run.py` | Deterministic validation engine |
| `tools/quality_loop.py` | Acceptance decision, retry/review/escalation logic |
| `tools/run_analyze.py` | Aggregated run and routing analytics |
| `tools/model_handoff.py` | Captures external output into Workbench evidence format |
| `tools/context_scout.py` | Deterministic context/evidence packet builder |
| `tools/config_loader.py` | Small YAML subset loader used by core tools |
| `tools/response_format.py` | Response parsing and required-section helpers |
| `configs/` | Starter routing, validation, context, and quality-loop configuration |
| `prompts/approved/` | Minimal public prompt templates |
| `recipes/` | Goose recipe files for Workbench acceptance workflows |
| `src/ai_workbench_mcp/` | MCP server package and runtime-agnostic core wrappers |
| `tests/` | Focused tests for core contracts, tool payloads, recipes, and MCP runtime smoke |
| `docs/ai/` | Operating docs for the Goose-first pivot |

## 4. MCP Tool Boundary

| MCP Tool | Backing Logic |
|---|---|
| `workbench_open_run` | `tools/context_scout.py` plus task metadata, final prompt, and initial run log |
| `workbench_select_model` | `tools/model_select.py` |
| `workbench_record_execution` | `tools/model_handoff.py` plus runtime metadata capture |
| `workbench_validate_run` | `tools/validate_run.py` |
| `workbench_quality_gate` | `tools/quality_loop.py` |
| `workbench_analyze_runs` | `tools/run_analyze.py` |

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
