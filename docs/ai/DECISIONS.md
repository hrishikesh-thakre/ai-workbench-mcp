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

Historical scope: this records the v0.2 package shape. v0.3 adds a first-class policy-pack catalog while preserving validation profile names and recipe references.

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

## 9. v0.3 PR Acceptance Uses Workbench Evidence

Status: Accepted

Decision:

- The v0.3 PR gate consumes Workbench run evidence for a pull request instead of treating CI status or scaffold validation as semantic acceptance.
- A PR gate decision is exactly one of `accept`, `needs_review`, or `block`.
- `accept` requires deterministic validation evidence and a quality-gate decision, especially `validation_report.json` and `revision_decision.json`.
- Scaffold-only fallback evidence is visibility evidence only and must block with `pr_gate.acceptance_evidence_missing`.
- Sticky PR comments and uploaded artifacts are presentation surfaces. They are not substitutes for the underlying evidence artifacts.

Why:

- The public merge-time story should match the core Workbench rule: do not call work accepted without deterministic validation and quality-gate acceptance.
- GitHub needs a fast PR-facing summary, but green CI alone cannot prove the agent task was accepted.

Implications:

- Same-repository PRs can receive one marker-based sticky comment when workflow permissions allow it.
- Fork PRs can still render and upload artifacts while skipping comment posting.
- GitHub Checks API integration, enforcement policy, fork-comment strategy changes, GEPA, provider plumbing, extra host integrations, and Codex cloud export remain out of scope for this alpha.
- The current published package remains `0.2.0a0`; v0.3 is not a published PyPI release until a future version is explicitly shipped.

## 10. v0.3 Policy Packs Are First-Class Catalog Assets

Status: Accepted

Decision:

- The five core policy packs are first-class entries in `configs/policy_packs.yaml`: `docs_only`, `low_risk_bug_fix`, `test_fix`, `api_contract_change`, and `security_privacy_sensitive`.
- Validation profiles keep their existing names and continue to be the recipe-facing selection surface.
- The policy-pack loader enriches validation profiles with catalog metadata for allowed files, required tests, required evidence, review triggers, blocker rules, and reason codes.
- Package/bootstrap assets should carry configs, prompts, and recipes forward for source builds and future package releases without implying that a v0.3 package has already been published.

Why:

- PR comments and downstream surfaces need machine-readable policy metadata to explain decisions without parsing prose.
- Existing recipes and examples already refer to validation profile names, so preserving those names avoids churn.

Implications:

- Sign-off profiles remain command-backed.
- Unknown or additive policy metadata should be displayed or tolerated by consumers rather than rejected.
- First-class policy metadata does not weaken the acceptance rule: validation and quality-gate evidence still decide whether a run is accepted.
