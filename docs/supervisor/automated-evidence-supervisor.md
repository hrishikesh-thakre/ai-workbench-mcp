# Automated Evidence Supervisor

The automated evidence supervisor is the experimental path for collecting
before/after evidence without requiring users to run manual commands around
every agent session.

## Goal

The supervisor should make evidence collection automatic while keeping outcomes
truthful:

- no fabricated validation passes
- no pretend pre-session baseline when capture started late
- no claim of full Codex coverage from transcript fallback
- final Workbench outcomes remain `accept`, `needs_review`, or `block`
  through `validation_report.json` and `revision_decision.json`

## Setup

For a project:

```bash
ai-workbench supervisor setup --project-dir . --task-type audit
ai-workbench supervisor start
ai-workbench supervisor status
```

`supervisor setup` registers the project in the daemon state directory. It does
not write daemon state into the project repository. Evidence still goes under
the project evidence root.

Direct registry commands remain available:

```bash
ai-workbench supervisor register --project-dir . --task-type audit
ai-workbench supervisor unregister --project-dir .
ai-workbench supervisor list
```

## State And Evidence Locations

Daemon-owned state lives in the user config directory:

- `daemon_state.json`
- `daemon.lock`
- `daemon.stop`
- `spool/codex_events.jsonl`
- `logs/daemon.jsonl`
- `logs/daemon.log`

Project evidence is run-scoped:

```text
runs/
  latest.json
  reports/
    index.json
    index.html
  <timestamp>-<agent>-<session-id>/
    metadata.json
    task_metadata.json
    final_prompt.md
    model_selection.json
    model_output.md
    run_log.jsonl
    validation_report.json
    revision_decision.json
    transcript.jsonl
    commands.jsonl
    workspace/
    validation/
    artifacts/
    acceptance_report_supporting.json
```

## Status Model

`ai-workbench supervisor status` separates project state from coverage.

Project state:

- `UNSUPERVISED`
- `FALLBACK_ONLY`
- `RUNNING`
- `block`
- `needs_review`
- `accept`

Coverage:

- `UNSUPERVISED`
- `HOOKS_CONFIGURED_UNTRUSTED_UNVERIFIED`
- `HOOKS_OBSERVED`
- `FALLBACK_ONLY`
- `OPENCODE_SQLITE_COMPATIBLE`
- `OPENCODE_SQLITE_OBSERVED`

Use JSON output for automation:

```bash
ai-workbench supervisor status --json
```

Every non-accepted state includes a `required_next_action`/`next_action`.

## Logs

Use:

```bash
ai-workbench supervisor logs --tail 50
ai-workbench supervisor logs --tail 50 --json
```

Logs are operational metadata only. They record lifecycle events, registration,
startup checks, adapter health, recovery actions, run start/finalization,
validation result summaries, and acceptance decisions.

Daemon logs redact raw stdout, stderr, transcript bodies, and tool outputs.
Evidence artifacts still preserve captured tool output because the acceptance
gate needs the real evidence record.

## Crash Recovery

The daemon uses:

- an owner lock file to avoid concurrent daemon instances
- PID liveness and heartbeat checks for stale lock recovery
- restart recovery for partially captured runs
- line-level Codex spool checkpoints

If a run has terminal metadata and existing report paths, recovery reuses the
existing report instead of writing duplicate acceptance reports.

## OpenCode Adapter

OpenCode supervision uses the OpenCode Desktop SQLite database.

Behavior:

- watches registered projects only
- checks the SQLite schema before polling
- dedupes events by session id and `part.rowid`
- starts a run when a matching session appears
- marks `late_snapshot=true` if the session already had rows before capture
- finalizes on idle timeout, daemon stop, or daemon restart recovery

Dogfood command:

```bash
ai-workbench supervisor start --foreground --idle-seconds 30
```

Then run a real OpenCode Desktop session in the registered project and inspect:

```bash
ai-workbench supervisor status
ai-workbench reports show latest --project-dir .
```

OpenCode coverage states:

- `OPENCODE_SQLITE_COMPATIBLE`: daemon can read a compatible OpenCode SQLite
  database for the registered project.
- `OPENCODE_SQLITE_OBSERVED`: daemon has captured OpenCode events or finalized
  an OpenCode-supervised run.

## Codex Adapter

Codex supervision is hook-first.

Install hooks:

```bash
ai-workbench setup codex --project-dir . --task-type audit
```

This writes project-local `.codex/hooks.json` for:

- `SessionStart`
- `PreToolUse`
- `PostToolUse`
- `Stop`

Codex must review and trust non-managed hooks before they run. After setup,
restart Codex or start a new session, open `/hooks`, review the hook, and trust
it once.

Coverage states:

- hooks configured but no real hook event observed:
  `HOOKS_CONFIGURED_UNTRUSTED_UNVERIFIED`
- hook event observed:
  `HOOKS_OBSERVED`
- transcript reconstruction only:
  `FALLBACK_ONLY`

Transcript polling is fallback/reconciliation only. It must not be used to claim
hook-first coverage.

Hook profiles:

- `--profile core` hooks Bash and file-edit tools. This is the default and has
  lower latency because it does not launch Python for every tool event.
- `--profile all` hooks every tool event and maximizes coverage for dogfood.

Read-only shell writes:

- `--read-only-shell-write warn` records shell writes as warnings. This is the
  early beta default to reduce false positives.
- `--read-only-shell-write block` denies shell write commands during read-only
  task types.

## Windows Startup

Windows login startup is supported experimentally:

```bash
ai-workbench supervisor startup-status
ai-workbench supervisor install-startup --dry-run
ai-workbench supervisor install-startup
ai-workbench supervisor install-startup --force
ai-workbench supervisor uninstall-startup
```

The generated startup command launches `ai-workbench supervisor start` and appends
startup failures to the daemon text log. Installation is idempotent. A stale
startup command is reported and requires `--force` to replace.

## Report Browsing

Report browsing is static and does not start a local web server:

```bash
ai-workbench reports list --project-dir .
ai-workbench reports show latest --project-dir .
ai-workbench reports show latest --project-dir . --json
ai-workbench reports show latest --project-dir . --markdown
ai-workbench reports open latest --project-dir .
```

The report browser reads `metadata.json` and acceptance report JSON/Markdown
only. It does not parse transcripts for browsing.

Finalized runs regenerate:

```text
runs/reports/index.json
runs/reports/index.html
```

## Validation

For code-change task types, the daemon only auto-detects conservative
validation commands:

- Python tests
- Node `test`
- Node `lint`
- Node `typecheck`

It does not infer deploy, publish, migrate, seed, clean, install, or destructive
commands. Missing validation blocks code-change acceptance. Timed-out
validation blocks the run. Failed validation also maps to Workbench `block`.
