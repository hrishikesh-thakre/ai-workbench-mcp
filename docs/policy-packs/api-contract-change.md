# api_contract_change Policy Pack

## Use when

Use `api_contract_change` for changes to Workbench API, MCP server behavior,
tool response envelopes, validation or quality-gate contracts, recipe/config
interfaces, packaging metadata, or public contract documentation.

## Do not use when

Do not use it for docs-only edits, ordinary low-risk bug fixes, test-only
repairs, or security/privacy-sensitive changes. Use the narrower pack when the
contract surface is unchanged.

## Accept condition

Accept only when contract-focused tests pass, the full suite passes, changed-file
evidence is present and in scope, contract documentation is consistent with the
implementation, and the quality gate accepts the run.

## Needs review condition

Needs review when tests pass but the contract surface changed in a way that
requires human confirmation, migration review, compatibility review, or release
note review, and no blocker-severity reason exists.

## Block condition

Block when contract tests are missing or fail, the full suite fails, changed-file
evidence is missing, unreported diffs exist, acceptance artifacts are missing, or
the evidence indicates an unknown or incompatible acceptance state.

## Required evidence

- `model_selection.json`
- `model_output.md`
- `run_log.jsonl`
- `validation_report.json`
- `revision_decision.json`

Required validation commands from the profile:

- `contract_tests`
- `full_test_suite`

## Example PR comment

```text
Decision: Accept
Why: api_contract_change contract tests and full suite passed; quality gate accepted.
Required next action: None.
Evidence present: validation_report yes, revision_decision yes
Reason codes: api_contract_change.required_tests_passed, api_contract_change.accepted
```

## Minimal command

```bash
python tools/validate_run.py --project ai_workbench_mcp --profile api_contract_change --out-dir runs/<run_id> --changed-files src/ai_workbench_mcp/<changed_file>.py tests/test_contracts.py
python tools/quality_loop.py --run-dir runs/<run_id>
```

The profile's contract test command is:

```bash
python -m pytest tests/test_contracts.py tests/test_server.py tests/test_mcp_runtime.py -q -p no:cacheprovider
```

## Common failure modes

- Updating response fields without updating contract tests.
- Changing policy metadata consumers without preserving tolerance for additive
  fields and unknown reason codes.
- Treating a PR comment as a contract acceptance artifact.
- Forgetting that v0.3 contracts are alpha baselines, not v1-stable contracts.

## Compact examples

| Outcome | Example |
|---|---|
| Accepted | A new additive response field is covered by contract tests, the full suite passes, and the quality gate accepts. |
| Needs review | Tests pass, but the MCP response surface changed enough to require compatibility review. |
| Blocked | `tests/test_contracts.py` fails, or `revision_decision.json` is missing. |
