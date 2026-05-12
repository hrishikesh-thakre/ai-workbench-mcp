# ROADMAP_STATUS

Owner: AI Workbench MCP
Status: v0.1 alpha baseline
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
| Validation of extracted tests | Passed | `python -m pytest -q -p no:cacheprovider` passed 78 tests and 2 subtests |
| Scaffold validation | Passed | `python tools/validate_run.py --project ai_workbench_mcp --profile scaffold --out-dir runs\smoke` passed |
| Public README/install flow | Alpha ready | README is positioned around evidence-backed acceptance gates and the six-tool recipe flow |
| Public examples | Done | Tiny Python fix, Goose tool smoke, Goose recipe smoke, and sanitized sample run added for v0.1 alpha |
| Execution capture idempotency | Done | Repeated `workbench_record_execution` calls return success without overwriting `model_output.md` or duplicating `run_log.jsonl` entries |

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

## Phase 4: v0.2 Recipe And Policy Packs (Next)

Goal:

Make the alpha workflow useful across common low-risk engineering tasks without broadening product scope.

Tasks:

- Add focused Goose recipes for docs-only changes, Python package maintenance, and test-fix workflows.
- Add validation policy packs for docs-only, low-risk coding, and package maintenance.
- Add tests that recipes and policy packs are discoverable and reference valid validation profiles.
- Keep the six-tool acceptance workflow stable.

## Phase 5: Acceptance Analytics

Goal:

Make routing improve from accepted artifacts.

Tasks:

- Track acceptance rate by task class and tier.
- Track cost per accepted artifact.
- Promote sanitized golden cases.
- Feed historical evidence back into routing recommendations.

## Current Next Step

Start v0.2 recipe library and validation policy pack work. Keep the six-tool acceptance workflow stable while adding focused recipes and policy variants.
