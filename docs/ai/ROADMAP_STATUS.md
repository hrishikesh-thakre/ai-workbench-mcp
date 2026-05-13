# ROADMAP_STATUS

Owner: AI Workbench MCP
Status: v0.2 alpha release candidate
Created: 2026-05-12

## Purpose

Track the extraction from private AI Workbench lab repo to a public Goose-first acceptance and audit layer.

## Status Matrix

| Initiative | Status | Notes |
|---|---|---|
| Clean repo extraction | Done | Core files copied; docs created; scaffold validation passed |
| Public-safe docs | Done | Four operating docs created around Goose-first pivot |
| Private run history removal | Done | `runs/` is gitignored and not copied |
| Cline/VSCodium removal | Done | Not copied into this repo |
| Local path removal | Done | Search found no private target-repo or editor-fork references |
| Goose MCP server | Alpha complete | Six Workbench tools exposed through a stdio FastMCP server; real MCP and console-script discovery smokes passed |
| Goose recipe MVP | Alpha complete | Engineering acceptance recipe uses run setup, execution capture, validation, quality gate, and analysis; local Gemma 4 six-tool smoke passed |
| Core JSON response contracts | Alpha stable | Contract envelopes added; direct callable model selection, validation, quality gate, run analysis, and evidence lifecycle added |
| Validation of extracted tests | Passed | Full pytest suite passed during Phase 5 analytics hardening |
| Scaffold validation | Passed | `python tools\validate_run.py --project ai_workbench_mcp --profile scaffold --out-dir runs\phase5_analytics_scaffold` passed |
| Public README/install flow | Alpha ready | README is positioned around evidence-backed acceptance gates and the six-tool recipe flow |
| Public examples | Done | Tiny Python fix, Goose tool smoke, Goose recipe smoke, focused workflow commands, and sanitized sample runs are committed |
| Execution capture idempotency | Done | Repeated `workbench_record_execution` calls return success without overwriting `model_output.md` or duplicating `run_log.jsonl` entries |
| v0.2 recipe and policy discovery | Release candidate | Folder-level recipe discovery and validation-profile reference tests cover docs-only, Python package maintenance, test-fix, and low-risk coding profiles |
| v0.2 public examples and release note | Release candidate | Focused workflow command examples, sanitized docs-only sample evidence, prompt catalog docs, and v0.2 alpha release summary are committed |
| v0.2 focused Goose smoke | Passed | Live docs-only focused recipe smoke passed with local Gemma 4; `docs_only` validation passed and quality gate accepted |
| Acceptance analytics | Hardening | `workbench_analyze_runs` summarizes accepted, review-required, and failed runs; `workbench_select_model` can now record advisory routing feedback without changing tiers |
| User-extensible model registry | Public-readiness hardening | Local ignored registry overrides let adopters bring their own model IDs while preserving committed defaults and selector validation |
| Minimal event envelopes | Public-readiness hardening | Core MCP operations write best-effort local `events.jsonl` ledgers from final response envelopes |
| Public alpha launch material | In progress | Phase 5 dogfooding protocol and current launch issue seeds document the next public evidence loop |

## Phase 0: Repo Alignment (Complete)

Goal:

Make the clean repo understandable and safe to work in.

Tasks:

- Create clean repo.
- Copy reusable Workbench core.
- Create `START_HERE.md`, `DECISIONS.md`, `PROJECT_MAP.md`, and `ROADMAP_STATUS.md`.
- Remove private paths from config.
- Add starter README and AGENTS instructions.
- Initialize git.

Exit criteria:

- A new contributor can understand that Goose is the execution layer and Workbench is the acceptance layer.
- Extracted tests and scaffold validation have passed.

## Phase 1: Core Extraction Hardening (Complete)

Goal:

Make copied logic stable enough to call from MCP.

Tasks:

- Define stable JSON contracts for selection, validation, quality gate, analysis, and evidence lifecycle.
- Preserve CLI behavior.
- Add tests around response shapes.
- Reduce assumptions inherited from the private lab repo.

## Phase 2: Goose MCP MVP (Complete)

Goal:

Expose Workbench trust tools inside Goose.

Tasks:

- Implement Python MCP server.
- Add `workbench_select_model`.
- Add `workbench_validate_run`.
- Add `workbench_quality_gate`.
- Add `workbench_analyze_runs`.
- Add `workbench_open_run`.
- Add `workbench_record_execution`.
- Add setup instructions for Goose Desktop and CLI.

## Phase 3: Goose Recipe MVP (Complete)

Goal:

Give users a one-command Goose workflow.

Tasks:

- Add `recipes/workbench-engineering-acceptance.yaml`.
- Parameterize task, target repo, risk, and validation profile.
- Require artifact-backed acceptance reporting.
- Test with a small local sample project.

## Phase 4: v0.2 Recipe And Policy Packs (Release Candidate)

Goal:

Make the alpha workflow useful across common low-risk engineering tasks without broadening product scope.

Tasks:

- Add focused Goose recipes for docs-only changes, Python package maintenance, and test-fix workflows.
- Add validation policy packs for docs-only, low-risk coding, package maintenance, and test-fix work.
- Add deterministic changed-file policy enforcement, starting with the `docs_only` profile.
- Restore the approved 12-prompt public prompt library and document the prompt catalog.
- Add tests that recipes, prompts, examples, and policy packs are discoverable and reference valid assets.
- Add public examples, sanitized focused sample evidence, and release notes for focused workflows.
- Keep the six-tool acceptance workflow stable.

## Phase 5: Acceptance Analytics (Hardening)

Goal:

Make routing improve from accepted artifacts.

Tasks:

- Track acceptance rate by task class, recipe, validation profile, and tier. Started in `tools/run_analyze.py`.
- Track review-required and failed outcomes with deterministic failure reasons.
- Add routing feedback candidates for later model-selection policy.
- Track cost per accepted artifact when real provider cost evidence exists.
- Promote sanitized golden cases.
- Run the Phase 5 dogfooding protocol across 20-50 real Goose tasks.
- Keep the analytics-to-routing loop advisory until enough real dogfood evidence exists.
- Feed historical evidence back into routing recommendations.
- Allow adopters to use local ignored model-registry overrides without editing committed defaults.
- Emit local best-effort operation events for future analytics and CI integration.

## Current Next Step

Continue Phase 5 by running the dogfooding protocol in `docs/dogfooding/phase5-dogfooding.md`, then use real `routing_feedback_candidates` to propose bounded model-selection policy experiments. Policy packs stay in `configs/validation_profiles.yaml` for v0.2; revisit a first-class policy-pack directory when the profile schema needs metadata beyond command and artifact checks.
