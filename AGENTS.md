# AGENTS.md

## Repository Summary

`ai-workbench-mcp` is a public-shaped extraction of the AI Workbench acceptance and audit layer. Its purpose is to integrate with Goose as the first supported MCP host while preserving Workbench-owned evidence, validation, quality gates, routing recommendations, and analytics.

## Read First

1. `docs/ai/START_HERE.md`
2. `docs/ai/DECISIONS.md`
3. `docs/ai/PROJECT_MAP.md`
4. `docs/ai/ROADMAP_STATUS.md`

## Working Rules

1. Keep Goose as the default execution surface.
2. Keep Workbench core logic runtime-agnostic.
3. Do not add private run history, local machine paths, provider secrets, or personal target-repo config.
4. Preserve `runs/<run_id>/` as the local evidence ledger, but keep `runs/` out of git.
5. Do not claim a run is accepted without deterministic validation and a quality-gate decision.
6. Prefer MCP tools and Goose recipes over custom UI or provider plumbing.

## Current Direction

The repo is being built toward:

```text
Goose-first distribution.
Workbench-owned acceptance and audit layer.
Runtime-agnostic core.
```

The first public MVP exposes run setup, model selection, execution capture, validation, quality gate, and run analysis through a Goose-compatible MCP server.
