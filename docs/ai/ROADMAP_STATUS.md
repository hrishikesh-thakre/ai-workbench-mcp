# ROADMAP_STATUS

Owner: AI Workbench MCP
Status: v0.6 external-repo PR gate adoption hardening branch
Active milestone: v0.6 External Repo PR Gate Adoption Hardening
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
| Goose MCP server | Alpha complete | Six acceptance-lifecycle tools plus the advisory policy-pack selector are exposed through a stdio FastMCP server; real MCP and console-script discovery smokes passed |
| Goose recipe MVP | Alpha complete | Engineering acceptance recipe uses run setup, execution capture, validation, quality gate, and analysis; local Gemma 4 six-tool smoke passed |
| Core JSON response contracts | Alpha stable | Contract envelopes added; direct callable model selection, validation, quality gate, run analysis, and evidence lifecycle added; `docs/contracts/v0.2-contract-baseline.md` records the current non-v1-stable contract baseline |
| Validation of extracted tests | Passed | Full pytest suite passed during Phase 5 analytics hardening |
| Scaffold validation | Passed | `python tools\validate_run.py --project ai_workbench_mcp --profile scaffold --out-dir runs\phase5_analytics_scaffold` passed |
| Public README/install flow | Alpha ready | README is positioned around evidence-backed acceptance gates, the six-tool recipe flow, and advisory policy-pack selection |
| Public examples | Done | Tiny Python fix, Goose/Codex tool smokes, Goose recipe smoke, focused workflow commands, and sanitized sample runs are committed |
| Execution capture idempotency | Done | Repeated `workbench_record_execution` calls return success without overwriting `model_output.md` or duplicating `run_log.jsonl` entries |
| v0.2 recipe and policy discovery | Release candidate | Folder-level recipe discovery and validation-profile reference tests cover docs-only, Python package maintenance, test-fix, and low-risk coding profiles |
| v0.2 public examples and release note | Release candidate | Focused workflow command examples, sanitized docs-only sample evidence, prompt catalog docs, and v0.2 alpha release summary are committed |
| v0.2 focused Goose smoke | Passed | Live docs-only focused recipe smoke passed with local Gemma 4; `docs_only` validation passed and quality gate accepted |
| Acceptance analytics | Phase 5 complete | `workbench_analyze_runs` summarizes accepted, review-required, and failed runs; Phase 5 closed with 31 complete evidence runs, including 29 live Goose runs and 2 deterministic controls |
| User-extensible model registry | Public-readiness hardening | Local ignored registry overrides let adopters bring their own model IDs while preserving committed defaults and selector validation |
| Minimal event envelopes | Public-readiness hardening | Core MCP operations write best-effort local `events.jsonl` ledgers from final response envelopes |
| Public CI gate prototype | Historical prototype | GitHub Actions repo self-validation runs install, tests, scaffold validation, PR gate artifact rendering, guarded same-repo sticky PR comments, and diff hygiene; this remains visibility evidence rather than semantic acceptance |
| v0.3 Semantic PR Acceptance Alpha | Current alpha | PR gate consumes real Workbench evidence, reports exactly one of `accept`, `needs_review`, or `block`, and blocks scaffold-only fallback evidence with required next action |
| v0.3 first-class policy packs | Current alpha | Five core policy packs live in `configs/policy_packs.yaml` and are loaded into validation profiles: `docs_only`, `low_risk_bug_fix`, `test_fix`, `api_contract_change`, and `security_privacy_sensitive` |
| v0.4 Policy Pack Productization | Complete | Policy-pack product docs, advisory selector, PR-gate policy-pack display, internal scorecard, and sanitized per-pack validation summary are complete; closeout added fresh aggregate evidence for `low_risk_bug_fix` acceptance and `security_privacy_sensitive` review-required behavior without changing acceptance semantics |
| v0.5 Safe Policy-Pack Auto-Selection | Current alpha | Policy-pack catalog entries map to validation profiles, selector output includes `recommended_validation_profile`, run setup can persist `policy_pack_selection.json`, validation can use selected profile metadata, and PR gate output displays pack, profile, and selection mode without changing acceptance semantics |
| v0.3 copy-paste PR workflow | Current alpha | `.github/workflows/ai-workbench-pr-gate.yml` documents a reusable GitHub workflow that renders PR gate artifacts and same-repository sticky comments from Workbench evidence |
| v0.3 package bootstrap assets | Current alpha | Source tree includes bootstrap assets and `ai-workbench-bootstrap-assets` for configs, prompts, and recipes; package metadata and workflow defaults are prepared for `0.3.0a0` |
| v0.3 PR gate outcome demos | Current alpha | Sanitized fixtures under `examples/pr-gate-outcomes/` and proof docs show `accept`, `needs_review`, and `block` decisions without committing private `runs/` evidence |
| v0.3 external sample repo proof | Complete | Public toy repository `hrishikesh-thakre/toy-ai-workbench-pr-gate` proves the copied workflow installs `ai-workbench-mcp==0.3.0a0`, renders same-repo PR artifacts/comments, and dispatches `accept`, `needs_review`, `block`, and scaffold-fallback `block` outcomes |
| v0.6 External Repo PR Gate Adoption Hardening | Current | Source tree adds `ai-workbench-bootstrap --target .`, packaged PR-gate adoption assets, clearer missing-evidence recovery steps, and bootstrap-first external setup docs without changing acceptance semantics or publishing a new package version |
| Single-file evidence dashboard | Public-readiness hardening | `workbench_analyze_runs` writes `run_dashboard.html` for local scanning without embedding raw model output or provider logs |
| Golden-case eval harness | Public-readiness hardening | Local file-based harness scores sanitized accepted evidence baselines without provider calls or routing-policy mutation |
| PyPI and package plumbing | Registry published | Historical package build checks, wheel smoke, TestPyPI install, exact-version PyPI install, and MCP Registry publication passed for `0.2.0a0`; `0.3.0a0` build, wheel smoke, TestPyPI upload/install, PyPI upload/install, and MCP Registry publication passed |
| GitHub launch setup | Done | Public repository topics are applied and launch issues `#1`-`#6` are open with public links |
| Codex local/IDE host metadata | Proof sample committed | One shared MCP server now records `execution_host` and `response_source`; sanitized Codex tiny Python fix evidence, bounded live walkthrough, and preflight/countdown handoff helper are committed |
| Dogfood Batch 1 | Evidence collected | Eight isolated local Goose/Gemma-backed runs produced 4 accepted and 4 review-required outcomes; report is aggregate-only and raw evidence stays ignored |
| Focused validation hardening | Done | Validation now falls back to model-selection profile metadata, `test_fix` requires focused task-specific Python test evidence for repo-target repairs, fixture proof profiles avoid repo self-test contradictions, and focused profiles require non-empty exact changed-file evidence |
| Dogfood Batch 2 | Evidence collected | Stage A and Stage B produced eight isolated Goose/Gemma-backed runs; Stage B confirmed exact-diff validation blocks no-op and underreported changed-file claims |
| Targeted docs-only routing evidence | Evidence collected | Six isolated low-risk `docs_only` Goose runs stayed on `local_coding`, passed deterministic validation, and were accepted by the quality gate; report is aggregate-only in `docs/dogfooding/targeted-docs-only-current-tier-report.md` |
| Docs-only current-tier advisory policy | Implemented | Selector feedback now returns `prefer_current_tier` only for the bounded low-risk, easy `docs_only` bucket with enough accepted evidence; defaults and selected tiers remain unchanged |
| Public alpha launch material | In progress | Phase 5 dogfooding protocol, acceptance concept guide, launch issues `#1`-`#6`, external repo setup, completed external sample proof, and v0.3 docs document the move from evidence collection to semantic PR acceptance |

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
- Add validation policy packs for docs-only, low-risk bug-fix, package maintenance, test-fix, API/contract, security/privacy, and low-risk coding work.
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
- Keep the analytics-to-routing loop advisory until a bounded policy experiment proves a candidate change with fresh isolated evidence.
- Feed historical evidence back into routing recommendations.
- Allow adopters to use local ignored model-registry overrides without editing committed defaults.
- Emit local best-effort operation events for future analytics and CI integration.
- Add a public CI gate prototype for repo self-validation, artifact rendering, and guarded same-repo PR comments before broader PR acceptance automation.
- Generate a static single-file evidence dashboard from run analytics for local scanning and demos.
- Add a local golden-case eval harness for accepted sanitized baselines.
- Prepare PyPI packaging checks and the recording-ready demo walkthrough.
- Apply public repository topics and create launch issues `#1`-`#6`.
- Add explicit execution-host and response-source metadata, with Codex local/IDE as the first second-host proof.
- Document the v0.2 contract baseline for run evidence, MCP envelopes, analytics/dashboard output, policy metadata, and PR gate artifacts.

Closeout status:

- Phase 5 evidence collection is complete in `docs/dogfooding/phase5-final-report.md`.
- Historical exact-diff hardening evidence remains in `docs/dogfooding/phase5-batch2-stage-b-report.md`.
- Final dogfood totals: 31 complete runs, 29 live Goose runs, 2 deterministic controls, 16 accepted outcomes, 15 review-required outcomes, and 0 failed public outcomes.
- Routing feedback remains advisory. At Phase 5 closeout, the PR gate was a GitHub-native visibility layer; v0.3 now owns the semantic PR acceptance alpha without changing default routing policy from the closeout report alone.
- The first targeted routing evidence batch is complete in `docs/dogfooding/targeted-docs-only-current-tier-report.md`: six low-risk `docs_only` Goose runs on `local_coding`, all accepted, with no review-required or failed outcomes.
- The first bounded policy branch is implemented from `docs/routing/docs-only-current-tier-policy-design.md`; it remains advisory and limited to low-risk, easy, accepted `docs_only` work.

## Phase 6: v0.3 Semantic PR Acceptance Alpha (Current)

Goal:

Make GitHub PR acceptance real from Workbench evidence while keeping Goose first and Workbench runtime-agnostic.

Tasks:

- Consume explicit Workbench run evidence for PR gate decisions.
- Report exactly one of `accept`, `needs_review`, or `block`.
- Show validation and quality-gate status separately.
- Report whether `validation_report.json` and `revision_decision.json` are present.
- Block scaffold-only fallback evidence with `pr_gate.acceptance_evidence_missing`.
- Keep the five first-class policy packs clear and usable through `configs/policy_packs.yaml`.
- Provide a copy-paste GitHub Actions workflow template for target repositories.
- Provide bootstrap assets for configs, prompts, and recipes in the published `0.3.0a0` package.
- Provide a one-page external repository setup guide.
- Complete a separate external sample repository proof.
- Commit sanitized PR gate outcome demos for public proof.

Out of scope:

- GEPA or extra host integrations.
- GitHub Checks API enforcement.
- Fork-comment strategy changes.
- Provider plumbing or provider cost enforcement.
- Codex cloud evidence export.
- Removing deterministic validation or quality-gate requirements.

## Current Next Step

The current pass is v0.6 external-repo PR gate adoption hardening. Make the already-proven PR gate easier to install and recover by using `ai-workbench-bootstrap --target .`, bootstrap-first docs, and explicit missing-evidence recovery steps. The public external sample repository proof remains complete at `https://github.com/hrishikesh-thakre/toy-ai-workbench-pr-gate`. v0.5 safe policy-pack auto-selection connects policy-pack selection to validation-profile setup evidence without changing acceptance semantics. Use `docs/concepts/how-acceptance-works.md` when explaining why validation profiles and quality gates decide acceptance. Keep routing feedback and policy-pack selection advisory for acceptance purposes. Do not broaden this into GEPA, medium-risk auto-routing, extra host integrations, Checks API enforcement, provider plumbing, or Codex cloud evidence export. Use `task_test_command` for every `low_risk_bug_fix` and `test_fix` run. Keep the package story explicit: `0.3.0a0` is published and exact-version install verified on TestPyPI, PyPI, and MCP Registry; no v0.6 package has been published in this branch.
