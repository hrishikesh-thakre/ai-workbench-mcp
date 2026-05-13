# START_HERE

Owner: AI Workbench MCP
Status: v0.2 alpha release candidate
Created: 2026-05-12

## 1. Project One-Liner

`ai-workbench-mcp` is the acceptance and audit layer for AI coding agents. It packages Workbench evidence, validation, quality-gate, routing, and analytics logic so Goose can execute work while Workbench decides whether that work is acceptable.

## 2. Product Direction

The repo is built around this pivot:

```text
Goose-first distribution.
Workbench-owned acceptance and audit layer.
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

This is a v0.2 alpha-shaped repo, not a completed stable release.

Copied core:

- packaged tool logic under `src/ai_workbench_mcp/tools/`
- backward-compatible CLI wrappers under `tools/`
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

The current alpha exposes the Workbench core through a Goose-compatible MCP server.

## 5. Approved Prompt Catalog

Approved prompts live in `prompts/approved/`. The public catalog is:

| Prompt | Primary use |
|---|---|
| `bug_root_cause_investigation.md` | Bug investigation and root-cause analysis before fixing. |
| `code_review_patch_risk_audit.md` | Patch, diff, or AI-generated change review. |
| `data_acquisition_surface_audit.md` | Data acquisition, ingestion, scraping, upload, and webhook surface review. |
| `documentation_accuracy_audit.md` | Documentation accuracy checks against implementation reality. |
| `implement_request_change_request.md` | Bounded implementation from a request, PRD, bug fix, or change brief. |
| `navigation_page_title_ia_audit.md` | Navigation, page title, label, route, and information architecture audit. |
| `performance_latency_hotspot_audit.md` | Performance and latency hot spot investigation. |
| `prompt_failure_improvement_log.md` | Prompt failure review and prompt improvement record. |
| `repository_context_index_audit.md` | Repository context indexing and orientation audit. |
| `security_privacy_risk_review.md` | Security and privacy risk review. |
| `test_case_development_meaningful_coverage.md` | Meaningful test-case development and coverage expansion. |
| `ux_visual_accessibility_audit.md` | UX, accessibility, and visual clarity audit. |

Focused v0.2 defaults:

- Docs-only recipe: `documentation_accuracy_audit.md`
- Test-fix recipe: `bug_root_cause_investigation.md`
- Future test-creation workflow: `test_case_development_meaningful_coverage.md`

## 6. Validation Expectations

For this starter extraction, begin with:

```bash
python tools/model_select.py --help
python tools/validate_run.py --help
python tools/quality_loop.py --help
python tools/run_analyze.py --help
pytest
```

Do not treat Goose prose as acceptance evidence. A run is accepted only when the evidence folder has deterministic validation and a quality-gate decision.

Evidence boundary:

- Keep local run evidence in ignored `runs/`.
- Commit only sanitized examples under `examples/sample-runs/`.
- Remove local absolute paths, provider secrets, private target-repo names, and raw model-loader logs from any committed sample.
- Read `docs/configuration/model-registry.md` before customizing local model tiers.
- Read `docs/analytics/event-ledger.md` before using local operation events for analytics or CI prototypes.
- Read `docs/analytics/acceptance-analytics.md` before using run analytics for routing decisions.
- Follow `docs/dogfooding/phase5-dogfooding.md` before turning routing feedback candidates into model-selection policy.
- Read `docs/github/pr-gate.md` before treating the CI gate prototype as anything beyond repo self-validation.

## 7. Public Release Rule

Before public release, remove or avoid:

- personal paths
- private run artifacts
- private provider config
- local-only target project references
- broad UI/provider plumbing that competes with Goose

The public repo should look like a Goose-compatible acceptance extension, not an alternative agent platform.

## 8. Phase 5 Launch Path

The next product pass is not more recipes. It is collecting real Goose runs and using `workbench_analyze_runs` to decide whether routing policy should change.

Use:

- `docs/dogfooding/phase5-dogfooding.md` for the dogfooding protocol.
- `docs/analytics/acceptance-analytics.md` for reading metrics and summaries.
- `docs/github/launch-issues.md` for public alpha issue seeds.
