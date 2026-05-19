# low_risk_bug_fix Policy Pack

## Use when

Use `low_risk_bug_fix` for bounded production bug fixes that can be validated by
a focused task test command plus the full project test suite. Allowed files are
limited to `src/**/*.py`, `tools/*.py`, `tests/**/*.py`, `examples/**/*.py`,
`docs/**/*.md`, and `README.md`.

## Do not use when

Do not use it for API contract changes, security/privacy-sensitive work, broad
refactors, provider plumbing, private configuration, or changes that cannot be
covered by a focused regression command.

## Accept condition

Accept only when the required `task_test_command` runs successfully, pytest
collection passes, the full suite passes, the Workbench tool help smoke passes,
changed-file evidence is present and in scope, and the quality gate accepts the
run.

## Needs review condition

Needs review when deterministic tests pass but regression evidence is weak, the
captured response format is incomplete, model output status raises concern, or
the quality gate requires review without blocker-severity evidence.

## Block condition

Block when `task_test_command` is missing or fails, the full suite fails,
changed-file evidence is missing, unreported worktree diffs exist, required
evidence is missing, or validation/quality gate evidence does not support
acceptance.

## Required evidence

- `model_selection.json`
- `model_output.md`
- `run_log.jsonl`
- `validation_report.json`
- `revision_decision.json`

Required validation commands from the profile:

- `task_test_command`
- `pytest_collection`
- `full_test_suite`
- `workbench_tool_help_smoke`

## Example PR comment

```text
Decision: Needs Review
Why: low_risk_bug_fix tests passed, but regression coverage was flagged for review.
Required next action: Human review the focused test evidence before merge.
Evidence present: validation_report yes, revision_decision yes
Reason codes: low_risk_bug_fix.required_tests_passed
```

## Minimal command

```bash
python tools/validate_run.py --project ai_workbench_mcp --profile low_risk_bug_fix --out-dir runs/<run_id> --changed-files src/<changed_file>.py tests/<focused_test>.py --task-test-command "python -m pytest tests/<focused_test>.py -q -p no:cacheprovider"
python tools/quality_loop.py --run-dir runs/<run_id>
```

## Common failure modes

- Omitting `task_test_command`.
- Using a broad command without focused regression coverage for the bug.
- Passing the focused command but failing the full suite.
- Editing files outside the low-risk bug-fix allowed scope.
- Treating a green PR workflow as Workbench acceptance without run evidence.

## Compact examples

| Outcome | Example |
|---|---|
| Accepted | A one-file parser bug fix in `src/` includes a focused pytest command for the regression, passes the full suite, and the quality gate accepts. |
| Needs review | The code and full suite pass, but the model output does not clearly connect the fix to the reported bug. |
| Blocked | The run has no `task_test_command`, or the focused regression test fails. |
