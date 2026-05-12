# ROADMAP_STATUS

Owner: AI Workbench MCP
Status: Draft
Created: 2026-05-12

## Purpose

Track the extraction from private AI Workbench lab repo to public Goose-first trust-layer repo.

## Status Matrix

| Initiative | Status | Notes |
|---|---|---|
| Clean repo extraction | Done | Core files copied; docs created; scaffold validation passed |
| Public-safe docs | Done | Four operating docs created around Goose-first pivot |
| Private run history removal | Done | `runs/` is gitignored and not copied |
| Cline/VSCodium removal | Done | Not copied into this repo |
| Local path removal | Done | Search found no private target-repo or editor-fork references |
| Goose MCP server | Not started | `src/ai_workbench_mcp/` placeholder exists |
| Goose recipe MVP | Not started | `recipes/` placeholder exists |
| Core JSON response contracts | In progress | Contract envelopes added; direct callable model selection extracted |
| Validation of extracted tests | Passed | `python -m pytest -q` passed 39 tests |
| Scaffold validation | Passed | `python tools/validate_run.py --project ai_workbench_mcp --profile scaffold --out-dir runs\smoke` passed |
| Public README/install flow | Draft | Needs update after MCP server exists |

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

## Phase 1: Core Extraction Hardening (Current)

Goal:

Make copied logic stable enough to call from MCP.

Tasks:

- Define stable JSON contracts for selection, validation, quality gate, and analysis. (In progress)
- Preserve CLI behavior. (In progress)
- Add tests around response shapes. (In progress)
- Reduce assumptions inherited from the private lab repo.

## Phase 2: Goose MCP MVP

Goal:

Expose Workbench trust tools inside Goose.

Tasks:

- Implement Python MCP server.
- Add `workbench_select_model`.
- Add `workbench_validate_run`.
- Add `workbench_quality_gate`.
- Add `workbench_analyze_runs`.
- Add setup instructions for Goose Desktop and CLI.

## Phase 3: Goose Recipe MVP

Goal:

Give users a one-command Goose workflow.

Tasks:

- Add `recipes/workbench-engineering-acceptance.yaml`.
- Parameterize task, target repo, risk, and validation profile.
- Require artifact-backed acceptance reporting.
- Test with a small local sample project.

## Phase 4: Acceptance Analytics

Goal:

Make routing improve from accepted artifacts.

Tasks:

- Track acceptance rate by task class and tier.
- Track cost per accepted artifact.
- Promote sanitized golden cases.
- Feed historical evidence back into routing recommendations.

## Current Next Step

Continue Phase 1 by extracting deterministic validation into a direct callable core path while preserving CLI behavior and the stable response envelope.
