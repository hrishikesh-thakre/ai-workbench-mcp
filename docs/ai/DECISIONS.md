# DECISIONS

Owner: AI Workbench MCP
Status: Draft
Created: 2026-05-12

## 1. Goose-First, Not Goose-Only

Status: Accepted

Decision:

- Goose is the default user surface and execution runtime.
- Workbench capabilities should be exposed to Goose through MCP tools and recipes.
- Workbench core logic remains runtime-agnostic so other runtimes, CI jobs, or future dashboards can reuse it.

Why:

- Goose already provides the ecosystem, UI, providers, recipes, MCP, and execution loop.
- The differentiated Workbench value is evidence-backed acceptance, validation, quality gates, routing recommendations, and learning from accepted artifacts.

Implications:

- Do not build a competing chat/editor UI.
- Do not rebuild broad MCP or provider plumbing.
- Keep core logic separate from Goose-specific wrappers.

## 2. Evidence Folders Are The Source Of Truth

Status: Accepted

Decision:

- `runs/<run_id>/` is the authoritative local evidence ledger.
- Goose session text, memory, or tool output can be recorded as runtime evidence, but acceptance belongs to Workbench artifacts.

Required acceptance artifacts:

- task metadata or task contract
- captured output or artifact changes
- runtime/provider/model metadata when available
- deterministic validation report
- quality-gate decision
- clear run status

## 3. Validation Gates Are Deterministic

Status: Accepted

Decision:

- A run must not be accepted based only on model self-claims.
- `validate_run.py` or its extracted core must produce command-backed, machine-readable evidence.

Implications:

- Validation profiles remain separate from model judgment.
- Failed validation blocks acceptance unless a human explicitly changes the policy.

## 4. Routing Optimizes For Accepted Artifacts

Status: Accepted

Decision:

- Model/runtime routing should optimize for accepted output, not cheapest tokens or strongest model by default.
- Routing policy should consider risk, complexity, privacy, validation strength, historical pass rate, and cost.

Implications:

- Local or cheap models can be draft tiers.
- High-risk or weakly validated work should escalate to stronger review or human approval.

## 5. Cline/VSCodium Work Is Out Of Scope

Status: Accepted

Decision:

- This public repo does not carry the old Cline/VSCodium fork or gateway path.

Why:

- That work belongs to the private lab history.
- The public path should be clean, Goose-first, and extension-shaped.

## 6. MCP Is The First Distribution Boundary

Status: Accepted

Decision:

- The first public integration should be a Goose-compatible MCP server exposing Workbench tools.

Initial tools:

- `workbench_select_model`
- `workbench_validate_run`
- `workbench_quality_gate`
- `workbench_analyze_runs`
- `workbench_open_run`
- `workbench_record_execution`
