# Release Readiness

`AI Workbench` package `ai-workbench-mcp==0.8.0a0` consolidates the local
evidence supervisor into one public alpha product surface.

## Supported Commands

### Public Alpha

| Command | Status | Notes |
|---|---|---|
| `ai-workbench mcp serve` | Alpha | MCP server entry point for Goose/Codex workflows |
| `ai-workbench bootstrap --target .` | Alpha | External-repo setup assets |
| `ai-workbench demo --target ./workbench-first-run` | Alpha | Synthetic first-run demo |
| `ai-workbench validate --project <project-or-path> --profile <profile> --run-dir <run>` | Alpha | Writes `validation_report.json`; bootstrapped repositories can use `--project .` |
| `ai-workbench gate --project <project-or-path> --run-dir <run>` | Alpha | Writes `revision_decision.json`; bootstrapped repositories can use `--project .` |
| `ai-workbench pr-gate --run-dir <run>` | Alpha | Renders PR-ready `accept`, `needs_review`, or `block` |
| `ai-workbench supervisor setup/register/unregister/start/stop/status/logs` | Alpha | Local automated evidence path |
| `ai-workbench setup codex --project-dir . --task-type <type>` | Alpha | Project-local Codex hook install; requires hook trust |
| `ai-workbench reports list/show/open --project-dir .` | Alpha | Static report browsing; no local web server |
| `ai-workbench opencode watch --project-dir .` | Alpha | Foreground OpenCode supervisor capture using canonical `runs/<run_id>/` artifacts |

## Known Limitations

1. **Confidence check false positives**: The word "heuristic" appearing in filenames (e.g., `heuristic_checker.py`) can trigger the heuristic extraction check. Mitigated in v0.3 by scoping detection to tool output fields only, but edge cases remain.

2. **Git status dependency**: Workspace hygiene checks require `git_status_before.txt` and `git_status_after.txt` in the evidence folder. If missing, the gate falls back to live `git status` on the target repo, which may lack historical context. The gate emits a warning when this occurs.

3. **Transcript format**: The JSONL parser supports common formats, but Codex
   supervision must use official hooks as the primary source. Transcript
   reconstruction is fallback/reconciliation only and is marked
   `FALLBACK_ONLY`.

4. **Single-platform startup integration**: Windows Startup-folder integration
   is implemented. macOS/Linux service-manager integration is not implemented.

5. **Daemon dogfood still required**: OpenCode and Codex supervision are covered
   by fixtures and smoke checks, but real Desktop dogfood remains required
   before treating the daemon as more than experimental.

6. **Reuse Scout scoring**: TF-IDF scoring with Jaccard overlap works for keyword-rich briefs but may produce low relevance scores (0.20-0.40) for abstract or domain-specific briefs. Semantic/embedding-based search is not implemented.

7. **No incremental acceptance**: The gate runs all checks every time. There is no caching, partial re-run, or incremental check mode.

8. **Operational logs are not evidence logs**: Daemon logs intentionally redact
   raw stdout/stderr and transcript bodies. The evidence folder remains the
   authoritative evidence record.

## False Accept / False Reject Definitions

- **False accept**: The Workbench PR gate returns `accept` for work that should
  have been `needs_review` or `block`. This is the most dangerous failure mode
  because bad agent work passed through undetected.

- **False block**: The Workbench PR gate returns `block` for work that should
  have been accepted or sent to review. This creates friction and erodes user
  trust.

### Current Rates (dogfood suite, 6 cases)

- False accept rate: 0% (0/6)
- False block rate: 0% (0/6)

These rates are measured on a curated 6-case dogfood suite. Real-world rates may differ.

## Public/Private Safety Rules

### Public Repo Must NOT Include

- Real project names or customer names
- Local absolute workstation paths
- Private wiki content or exports
- Real agent transcripts from internal projects
- Business strategy notes or internal decision logs
- Proprietary code, DRM logic, or publisher-specific content
- Secrets, API tokens, or environment values

### Public Repo Contains Only

- Generic source code with no project-specific references
- Fake/sample fixtures in `examples/`
- Publicly safe dogfood cases with fake data
- Policy YAML files with no internal project mappings
- Documentation describing the tool, not internal usage

## Supervisor Readiness

Implemented experimental supervisor capabilities:

- registered project supervision
- run-scoped evidence folders
- OpenCode SQLite supervision
- Codex hook-first supervision
- fallback transcript marking
- daemon lock/heartbeat/stale PID recovery
- safer line-level Codex spool checkpointing
- redacted daemon logs
- Windows startup install/status/uninstall
- static report listing/show/open
- normalized project state and coverage fields

Status states:

- `UNSUPERVISED`
- `FALLBACK_ONLY`
- `RUNNING`
- `block`
- `needs_review`
- `accept`

Coverage states:

- `UNSUPERVISED`
- `HOOKS_CONFIGURED_UNTRUSTED_UNVERIFIED`
- `HOOKS_OBSERVED`
- `FALLBACK_ONLY`
- `OPENCODE_SQLITE_COMPATIBLE`
- `OPENCODE_SQLITE_OBSERVED`

## What NOT to Use This Tool For (Yet)

- Production gatekeeping without human review
- Security audit sign-off (the tool checks evidence, not security correctness)
- Regulatory compliance (no formal certification)
- Replacing code review on high-risk changes (auth, crypto, data migration)
- Unattended high-risk PR enforcement without human review
- Multi-user or team workflows (single-user local daemon only)
- Unattended production enforcement without reviewing Workbench reports

## Test Coverage

- Full source suite: `python -m pytest -q -p no:cacheprovider`
- Static checks: `python -m ruff check . --no-cache` and
  `python -m mypy --no-sqlite-cache --no-incremental`
- Package checks: `python -m build` and `python -m twine check dist/*`
- Fresh wheel smoke: install `ai-workbench-mcp==0.8.0a0` from a local wheel in
  a clean virtual environment, verify only `ai-workbench` is installed as a
  console script, and confirm retired scripts are absent
- Clean-adopter smoke: bootstrap a fresh Git repository, register supervisor
  capture, install Codex hooks, simulate hook events through the installed hook
  module, process the daemon spool, verify `HOOKS_OBSERVED`, show the latest
  report, and render an `accept` PR-gate outcome from `runs/<run_id>/`

## Package Structure

The PyPI distribution remains `ai-workbench-mcp` for the public alpha. The
import package root is `ai_workbench_mcp/`, and the public console script is
`ai-workbench`. Supervisor policy profiles are bundled as package data under
`ai_workbench_mcp/supervisor/policies/`.

## PyPI Release Process

### Local verification

```bash
python -m pip install build twine
python -m build
python -m twine check dist/*
```

### TestPyPI (recommended before production PyPI)

```bash
python -m twine upload --repository testpypi dist/*
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple "ai-workbench-mcp==0.8.0a0"
ai-workbench --help
```

### Production PyPI

Tag a release commit:

```bash
git tag v0.8.0a0
git push origin v0.8.0a0
```

The GitHub Actions release workflow must build, check, and publish the
`ai-workbench-mcp` distribution via Trusted Publishing only after explicit
release approval.

### Trusted Publishing setup

1. In PyPI project settings, add a Trusted Publisher:
   - Owner: `hrishikesh-thakre`
   - Repository: `ai-workbench-mcp`
   - Workflow: the approved release workflow
2. In GitHub repo settings → Environments, create a `pypi` environment.
3. Push a `v*` tag to trigger the release workflow.
