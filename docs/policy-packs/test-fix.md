# test_fix Policy Pack

## Use when

Use `test_fix` for bounded repo-target test fixes where the work may touch
tests, supporting code, examples, or docs, and must preserve full project test
health.

## Do not use when

Do not use it for intentionally broken demo fixture repairs that conflict with
repo self-tests; use focused fixture profiles for those. Do not use it for API
contract changes, security/privacy-sensitive changes, broad implementation
work, or test changes without a focused failing/passing task command.

## Accept condition

Accept only when the required `task_test_command` succeeds, pytest collection
passes, the full suite passes, recipe/policy discovery tests pass, changed-file
evidence is present, and the quality gate accepts the run.

## Needs review condition

Needs review when commands pass but the focused test command is weak or unclear,
the captured response format is incomplete, model output status raises concern,
or the quality gate requests review without blocker-severity evidence.

## Block condition

Block when the focused task test command is missing or fails, the full suite
fails, changed-file evidence is missing, unreported diffs exist, or required
acceptance artifacts are missing or unreadable.

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
- `recipe_policy_discovery_tests`

## Example PR comment

```text
Decision: Block
Why: test_fix requires a focused task_test_command and full-suite evidence.
Required next action: Re-run validation with a focused pytest or unittest command.
Evidence present: validation_report yes, revision_decision no
Reason codes: test_fix.required_test_missing
```

## Minimal command

```bash
ai-workbench validate --project ai_workbench_mcp --profile test_fix --run-dir runs/<run_id> --changed-file tests/<focused_test>.py --task-test-command "python -m pytest tests/<focused_test>.py -q -p no:cacheprovider"
ai-workbench gate --project ai_workbench_mcp --run-dir runs/<run_id>
```

## Common failure modes

- Repairing a fixture with `test_fix` when the repository tests intentionally
  assert that fixture starts broken.
- Missing focused task-specific test evidence.
- Full suite failure after a focused test passes.
- Unreported changed files.

## Compact examples

| Outcome | Example |
|---|---|
| Accepted | A flaky test assertion is corrected, the focused test passes, collection passes, the full suite passes, and the quality gate accepts. |
| Needs review | Tests pass, but the output does not explain whether behavior or only the test was changed. |
| Blocked | The run lacks `task_test_command`, or `python -m pytest -q -p no:cacheprovider` fails. |
