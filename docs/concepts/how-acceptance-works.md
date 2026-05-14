# How Acceptance Works

AI Workbench MCP is an acceptance and audit layer for AI coding-agent runs.

MCP is the connection protocol. AI Workbench MCP is the tool server. Acceptance is decided by the selected validation profile and quality gate. The agent performs. Workbench accepts. MCP connects them.

## Roles

Goose, Codex local/IDE, or another MCP-compatible host executes the task and calls Workbench tools. The host owns the agent loop, provider setup, model execution, and user interaction.

AI Workbench MCP owns the evidence ledger and acceptance decision. It opens a run folder, records task and runtime metadata, captures output, runs deterministic validation, applies the quality gate, and summarizes analytics.

MCP connects those pieces. It does not prove correctness, enforce a prompt definition-of-done, replace tests, or decide acceptance by itself.

## Evidence Flow

The standard run flow is:

```text
workbench_open_run
  -> workbench_select_model
  -> agent performs the task
  -> workbench_record_execution
  -> workbench_validate_run
  -> workbench_quality_gate
  -> workbench_analyze_runs
```

The run folder is the local evidence ledger:

```text
runs/<run_id>/
  task_metadata.json
  final_prompt.md
  model_selection.json
  model_output.md
  validation_report.json
  revision_decision.json
  run_log.jsonl
```

A run is accepted only when the validation report passes, the report is sign-off ready, and the quality gate writes an accepted decision.

## Prompt DoD vs Acceptance Gate

A prompt definition-of-done is an instruction to the agent. It can ask for tests, files touched, risks, and a structured response. It is useful, but it is not enforcement.

The acceptance gate runs after the agent acts. It checks explicit artifacts and command-backed validation results. Starter validation profiles can require tests, build or lint checks, non-empty evidence files, changed-file policy, focused task test commands, and review checks. For docs-only work, claimed changed files must have matching worktree diff evidence; a model saying it edited a file is not enough.

If the evidence is incomplete, risky, ambiguous, or failed, Workbench should produce `review_required`, `revision_required`, or `failed` instead of `accepted`.

## What Workbench Does Not Claim

AI Workbench MCP does not prove software correctness. It does not replace CI, code review, security review, or human judgment for high-risk work.

The current validation profiles are starter policies. They are useful for bounded launch workflows, but they are not universal truth. Deterministic checks come first; reviewer-agent workflows and richer policy metadata are future work.

Use committed sample evidence for public demos, and keep raw local `runs/` evidence out of git.
