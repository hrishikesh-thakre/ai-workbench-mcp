# docs_only Policy Pack

## Use when

Use `docs_only` for bounded public documentation updates where all changed files
are Markdown files allowed by the catalog: `*.md`, `docs/**/*.md`, or
`examples/**/*.md`.

## Do not use when

Do not use it for source, tool, test, config, recipe, packaging, or runtime
changes. Use a stronger pack when the work changes executable behavior,
acceptance contracts, security posture, or test logic.

## Accept condition

Accept only when deterministic validation passes, changed-file evidence is
non-empty and limited to the allowed Markdown scope, and the quality gate writes
`revision_decision.json` with `final_status="accepted"`.

## Needs review condition

Needs review when deterministic checks pass but the captured model output,
response format, or quality gate asks for human review without a blocker
severity reason.

## Block condition

Block when source or config files changed, changed-file evidence is missing, a
claimed file has no worktree diff, an unreported worktree diff exists, required
docs tests fail, or acceptance evidence is missing or unreadable.

## Required evidence

- `model_selection.json`
- `model_output.md`
- `run_log.jsonl`
- `validation_report.json`
- `revision_decision.json`

Required validation commands from the profile:

- `verify_public_docs`
- `recipe_policy_discovery_tests`

## Example PR comment

```text
Decision: Accept
Why: docs_only validation passed and the quality gate accepted the run.
Required next action: None.
Evidence present: validation_report yes, revision_decision yes
Reason codes: docs_only.required_tests_passed, docs_only.accepted
```

## Minimal command

```bash
ai-workbench validate --project ai_workbench_mcp --profile docs_only --run-dir runs/<run_id> --changed-file docs/<changed_doc>.md
ai-workbench gate --project ai_workbench_mcp --run-dir runs/<run_id>
```

For PR rendering, point the PR gate at that completed run:

```bash
ai-workbench pr-gate --run-dir runs/<run_id> --out runs/pr_gate/pr_comment.md --json-out runs/pr_gate/pr_decision.json
```

## Common failure modes

- Editing `src/`, `tools/`, `tests/`, `configs/`, or `recipes/`.
- Claiming a changed file that has no actual diff.
- Leaving an actual Markdown diff out of the captured changed-file evidence.
- Treating scaffold validation as docs acceptance.

## Compact examples

| Outcome | Example |
|---|---|
| Accepted | A typo fix in `docs/github/pr-gate.md` passes `verify_public_docs`, `recipe_policy_discovery_tests`, changed-file policy, and the quality gate. |
| Needs review | Markdown-only files changed and commands pass, but model output is incomplete enough that the quality gate requests review. |
| Blocked | A docs PR also changes `configs/validation_profiles.yaml`, or the run lacks `validation_report.json`. |
