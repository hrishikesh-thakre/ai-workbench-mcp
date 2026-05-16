# Gemini Fixture Accepted Run Proof

Status: sanitized live-run summary
Run date: 2026-05-16
Raw evidence: ignored local `runs/` ledger, not committed

## Claim

A fresh Goose run using the configured Gemini default can repair the intentionally broken tiny Python fixture and produce accepted Workbench evidence without dirtying the main repository worktree.

Acceptance still comes from Workbench validation and the quality gate, not from Goose or model self-reporting.

## Runtime

| Field | Value |
|---|---|
| Goose version | `1.34.1` |
| Goose provider/model | `gemini_oauth / gemini-3-flash-preview` |
| Provider/model command overrides | none |
| Baseline commit | `3d66aec Fix fixture repair proof profile` |
| Recipe | `workbench-test-fix-acceptance.yaml` |
| Validation profile | `fixture_repair_proof` |
| Run evidence folder | `runs/gemini-fixture-proof/tiny-python-fix` |
| Analytics parent | `runs/gemini-fixture-proof` |

The proof ran in an isolated temporary worktree with an external virtual environment. The main repository worktree was not mutated by the live proof.

## Task

```text
Fix examples/tiny-python-fix/calculator.py so python -m unittest discover -s examples/tiny-python-fix -p test_*.py passes. Keep the change minimal and do not edit unrelated files.
```

## Baseline Signal

The focused unittest command failed before Goose changed the fixture. That failure is expected because the checked-in fixture is intentionally broken.

During exploration, a Unix-only `cat` command failed on Windows. That failed inspection command was not acceptance evidence; Goose recovered with a Windows-compatible file inspection command and continued the repair.

## Accepted Evidence

Required artifacts were present:

```text
task_metadata.json
final_prompt.md
model_selection.json
model_output.md
validation_report.json
revision_decision.json
run_log.jsonl
```

`validation_report.json` recorded:

```text
overall_status = passed
sign_off_ready = true
task_test_command = passed
changed_file_policy = passed
full_test_suite command = absent
```

`revision_decision.json` recorded:

```text
final_status = accepted
```

The only tracked task diff was:

```text
examples/tiny-python-fix/calculator.py
```

The repair changed the fixture implementation from subtraction to addition:

```diff
-    return left - right
+    return left + right
```

Isolated analytics over `runs/gemini-fixture-proof` reported one accepted run and an acceptance rate of `1.0`.

## Interpretation

This live proof is stronger than the committed sample-only path because it exercised Goose, the configured Gemini runtime, the test-fix recipe, focused fixture validation, changed-file policy, quality gate, and isolated analytics in one fresh run.

It is still one data point. Do not change routing policy from this proof alone, and do not treat it as a model benchmark. Use it as evidence that the corrected `fixture_repair_proof` path can produce accepted live Goose evidence.

## Reproduce A Similar Live Run

Use an isolated worktree and an external virtual environment, then run Goose without provider or model overrides:

```bash
goose run --no-session --max-turns 20 --max-tool-repetitions 2 \
  --recipe ./recipes/workbench-test-fix-acceptance.yaml \
  --params project=ai_workbench_mcp \
  --params run_dir=runs/gemini-fixture-proof/tiny-python-fix \
  --params task="Fix examples/tiny-python-fix/calculator.py so python -m unittest discover -s examples/tiny-python-fix -p test_*.py passes. Keep the change minimal and do not edit unrelated files." \
  --params risk=low \
  --params validation_profile=fixture_repair_proof \
  --params complexity_score=4 \
  --params task_test_command="python -m unittest discover -s examples/tiny-python-fix -p test_*.py" \
  --params analytics_runs_dir=runs/gemini-fixture-proof \
  --params analytics_out_dir=runs/gemini-fixture-proof/_reports
```

Keep the live evidence under ignored `runs/`. Promote only sanitized summaries or intentionally sanitized sample evidence.
