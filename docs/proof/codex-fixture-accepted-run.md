# Codex Fixture Accepted Run Proof

Status: sanitized live-run summary
Run date: 2026-05-16
Raw evidence: ignored local `runs/` ledger, not committed

## Claim

A fresh Codex local/IDE run can use the same AI Workbench MCP acceptance layer as Goose and produce accepted fixture-repair evidence through the corrected `fixture_repair_proof` path.

Acceptance still comes from Workbench deterministic validation and the quality gate, not from Codex self-reporting.

## Runtime

| Field | Value |
|---|---|
| Codex version | `0.130.0-alpha.5` |
| Codex model shown by host | `gpt-5.5 xhigh` |
| MCP server | `aiWorkbench` stdio server |
| Baseline commit | `ecc0ce1 Prepare Codex fixture proof handoff` |
| Validation profile | `fixture_repair_proof` |
| Run evidence folder | `runs/codex-live-20260516-fixture-proof/tiny-python-fix` |
| Analytics parent | `runs/codex-live-20260516-fixture-proof` |

The proof ran in an isolated temporary worktree with an external virtual environment. The main repository worktree was not mutated by the live proof.

## Task

```text
Fix examples/tiny-python-fix/calculator.py so python -m unittest discover -s examples/tiny-python-fix -p test_*.py passes.
```

## Baseline Signal

The focused unittest command failed before Codex changed the fixture. That failure is expected because the checked-in fixture is intentionally broken.

The live prompt explicitly told Codex to use OS-appropriate file inspection commands and to avoid assuming Unix-only commands such as `cat`.

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
events.jsonl
```

Host/source metadata recorded:

```text
execution_host = codex
response_source = codex
```

`validation_report.json` recorded:

```text
profile = fixture_repair_proof
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

Isolated analytics over `runs/codex-live-20260516-fixture-proof` reported two evidence folders: one accepted fixture repair and one tool-smoke folder without a quality-gate decision. The accepted fixture run counted under `execution_host=codex`, `response_source=codex`, and `validation_profile=fixture_repair_proof`.

## Interpretation

This proof exercises a different host from the Goose proof while preserving the same Workbench-owned acceptance boundary. Codex performed the task through MCP tools; Workbench accepted the evidence after focused validation, exact changed-file policy, and the quality gate.

It is still one data point. Do not change routing policy from this proof alone, and do not treat it as a model benchmark.
