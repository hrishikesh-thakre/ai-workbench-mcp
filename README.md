# AI Workbench Goose

AI Workbench Goose is a Goose-first acceptance layer for agentic engineering work.

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

Current status: extracted starter repo. The copied Python tools are the initial core; the Goose MCP wrapper and production recipe are the next implementation steps.

Start with [START_HERE.md](docs/ai/START_HERE.md).
