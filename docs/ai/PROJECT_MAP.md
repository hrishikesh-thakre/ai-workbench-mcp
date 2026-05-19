# PROJECT_MAP

Owner: AI Workbench MCP
Status: v0.2 alpha release candidate
Active milestone: v0.3 Semantic PR Acceptance Alpha
Created: 2026-05-12

## 1. Purpose

This repo is the clean public-shaped extraction of the AI Workbench acceptance and audit layer. It is a Goose-compatible MCP extension and recipe set for accepting, validating, auditing, and learning from agentic work.

## 2. Target Architecture

```text
Goose Desktop / CLI / recipe
Codex local/IDE
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
| `src/ai_workbench_mcp/tools/run_analyze.py` | Aggregated run and routing analytics plus static evidence dashboard generation |
| `src/ai_workbench_mcp/tools/golden_eval.py` | Local golden-case scoring for sanitized accepted evidence baselines |
| `src/ai_workbench_mcp/tools/pr_gate.py` | PR-facing decision and comment renderer for Workbench acceptance evidence |
| `src/ai_workbench_mcp/tools/pr_gate_comment.py` | Marker-based GitHub PR comment helper for same-repository PRs |
| `src/ai_workbench_mcp/tools/policy_packs.py` | First-class policy-pack catalog loader for validation profiles |
| `src/ai_workbench_mcp/tools/policy_pack_select.py` | Advisory policy-pack selector from task metadata |
| `src/ai_workbench_mcp/tools/bootstrap_assets.py` | Bootstrap helper for materializing packaged configs, prompts, and recipes |
| `src/ai_workbench_mcp/tools/model_handoff.py` | Captures external output into Workbench evidence format |
| `src/ai_workbench_mcp/tools/context_scout.py` | Deterministic context/evidence packet builder |
| `src/ai_workbench_mcp/events.py` | Best-effort local operation event envelopes and JSONL sink |
| `src/ai_workbench_mcp/tools/config_loader.py` | Small YAML subset loader used by core tools |
| `src/ai_workbench_mcp/tools/response_format.py` | Response parsing and required-section helpers |
| `tools/` | Backward-compatible CLI wrappers for existing `python tools/*.py` commands |
| `tools/codex_live_test_handoff.py` | Safe preflight/countdown helper that writes a one-shot Codex live-test prompt without launching Codex |
| `tools/check_codex_live_result.py` | Read-only checker for Codex live-test evidence folders after a local/IDE run |
| `configs/` | Starter routing, validation, policy-pack, context, and quality-loop configuration |
| `configs/policy_packs.yaml` | v0.3 first-class catalog for the five core policy packs |
| `prompts/approved/` | Minimal public prompt templates |
| `recipes/` | Goose recipe files for Workbench acceptance workflows |
| `src/ai_workbench_mcp/` | Installable MCP server package, runtime-agnostic core wrappers, and packaged tool logic |
| `tests/` | Focused tests for core contracts, tool payloads, recipes, and MCP runtime smoke |
| `docs/ai/` | Operating docs for the Goose-first pivot |
| `docs/concepts/how-acceptance-works.md` | Concept guide explaining that MCP connects while Workbench validation profiles and quality gates decide acceptance |
| `docs/analytics/event-ledger.md` | Local event ledger guide for best-effort operation telemetry |
| `docs/analytics/evidence-dashboard.md` | Static local dashboard guide for `run_dashboard.html` |
| `docs/contracts/v0.2-contract-baseline.md` | Current non-v1-stable contract baseline for run evidence, MCP envelopes, analytics, policies, and PR gate artifacts |
| `docs/codex/` | Codex local/IDE setup, acceptance workflow, live-test handoff, AGENTS.md snippet, and cloud limitations |
| `docs/evals/golden-case-harness.md` | Golden-case eval harness guide |
| `docs/evals/policy-pack-quality-scorecard.md` | Internal policy-pack quality scorecard; not an acceptance gate |
| `docs/policy-packs/` | Product-facing docs for the five core policy packs |
| `docs/publishing/pypi.md` | PyPI publishing prep and current wheel boundary |
| `docs/github/repository-topics.md` | GitHub topic setup guide |
| `docs/github/create-launch-issues.md` | Launch issue creation commands |
| `docs/github/pr-gate-workflow-template.md` | Copy-paste GitHub Actions PR gate workflow template |
| `docs/proof/pr-gate-outcome-demos.md` | Sanitized PR gate outcome demo proof for `accept`, `needs_review`, and `block` |
| `docs/walkthroughs/goose-acceptance-demo.md` | Recording-ready public Goose acceptance demo walkthrough |
| `docs/walkthroughs/codex-acceptance-demo.md` | Codex local/IDE acceptance demo walkthrough with loop and crash guardrails |
| `evals/golden_cases/` | Sanitized accepted-baseline eval case specs |
| `.github/workflows/ci.yml` | Public repo self-validation CI gate prototype |
| `.github/workflows/ai-workbench-pr-gate.yml` | Copy-paste workflow template for target repositories that can provide Workbench evidence |

## 4. MCP Tool Boundary

| MCP Tool | Backing Logic |
|---|---|
| `workbench_open_run` | `ai_workbench_mcp.tools.context_scout` plus task metadata, final prompt, and initial run log |
| `workbench_select_policy_pack` | `ai_workbench_mcp.tools.policy_pack_select`; advisory only and does not mutate validation behavior |
| `workbench_select_model` | `ai_workbench_mcp.tools.model_select` |
| `workbench_record_execution` | `ai_workbench_mcp.tools.model_handoff` plus runtime metadata capture |
| `workbench_validate_run` | `ai_workbench_mcp.tools.validate_run` |
| `workbench_quality_gate` | `ai_workbench_mcp.tools.quality_loop` |
| `workbench_analyze_runs` | `ai_workbench_mcp.tools.run_analyze` |

`workbench_open_run` records canonical `execution_host` metadata. Initial allowed values are `goose`, `codex`, `ci`, and `other`; the default remains `goose`. `workbench_record_execution` records `response_source`, defaulting to `goose`.

## 5. PR Acceptance Boundary

The v0.3 PR acceptance alpha is a GitHub-facing presentation of Workbench evidence, not a new execution host.

Inputs:

- one explicit Workbench run directory, or a parent runs directory plus run id
- optional scaffold fallback evidence when no real run is available

Required artifacts for an `accept` decision:

- `validation_report.json`
- `revision_decision.json`

Outputs:

- `runs/pr_gate/pr_comment.md`
- `runs/pr_gate/pr_decision.json`

Allowed outcomes:

- `accept`
- `needs_review`
- `block`

Scaffold-only fallback evidence always blocks. Green CI, uploaded artifacts, or sticky PR comments do not replace deterministic validation and quality-gate evidence.

## 6. Non-Goals

This repo should not become:

- a Goose competitor
- a generic chat UI
- a generic provider marketplace
- a Cline/VSCodium fork
- a broad MCP marketplace
- a Codex-specific MCP server
- a private run-history archive
- a GEPA or broad host-integration experiment during v0.3

## 7. Public Hygiene

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
