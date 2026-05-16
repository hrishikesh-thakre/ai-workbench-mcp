# DECISIONS

Owner: AI Workbench MCP
Status: v0.2 alpha release candidate
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

## 7. v0.2 Policy Packs Stay In Validation Profiles

Status: Accepted

Decision:

- For v0.2, focused policy packs are named profiles inside `configs/validation_profiles.yaml`.
- Each acceptance profile must remain command-backed and declare required evidence artifacts when it can be used for sign-off.
- Do not create a separate policy-pack directory until profiles need additional metadata, composition, inheritance, or runtime-specific packaging.

Why:

- The current v0.2 profiles are small and share the same validation engine.
- Keeping profiles in one config keeps Goose recipes simple: recipes only need to pass `validation_profile`.
- A first-class policy-pack directory would add structure before there is a clear schema boundary.

Implications:

- Discovery tests should verify that recipes reference valid validation profiles.
- Profile growth should be revisited before v0.3 if command lists, artifact policy, or risk policy become hard to maintain in one YAML file.
- Fixture repair proofs must not reuse repo-wide self-validation when the repo intentionally asserts that a fixture starts broken. Use focused fixture profiles such as `tiny_python_fix` or `fixture_repair_proof` for demo targets, and keep `test_fix` for repo-target repairs that must preserve the full suite.

## 8. Goose-First, Codex-First-Class

Status: Accepted

Decision:

- Goose remains the default v0.2 execution host.
- Codex local/IDE is the first second-host integration target.
- The canonical host field is `execution_host`.
- Initial allowed values are `goose`, `codex`, `ci`, and `other`.
- `response_source` records where captured execution output came from.
- Workbench keeps one shared MCP server: `ai-workbench-mcp`.

Why:

- Codex has strong developer distribution and can use MCP in local/IDE workflows.
- Codex is a direct test of whether Workbench is a host-portable acceptance layer rather than Goose-specific tooling.
- The same evidence folder, validation, quality gate, event ledger, and analytics should work across hosts.

Implications:

- Do not create `ai-workbench-codex-mcp` or any Codex-specific server fork.
- Keep `workbench_select_model` advisory for Codex because Codex may control its actual model/runtime.
- Add host/source analytics so accepted rates can be compared across Goose, Codex, CI, and future hosts.
- Target Codex local/IDE before Codex cloud.
- Treat Codex cloud evidence persistence, export, PR linking, and network access as a separate design pass.
