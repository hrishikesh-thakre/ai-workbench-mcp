# Codex Cloud Limitations

Codex cloud is not part of this implementation pass. This pass targets Codex local/IDE because local MCP configuration can call the existing `ai-workbench mcp serve` stdio server directly.

## Why Cloud Comes Later

Codex cloud runs tasks inside a cloud environment tied to repositories and pull request workflows. OpenAI's Codex cloud docs describe background and parallel task execution in a cloud environment. That changes the evidence problem:

- Where does `runs/<run_id>/` persist after the task finishes?
- Can the cloud task reach the local or remote MCP server?
- Should evidence be committed, uploaded, exported, or summarized?
- Which secrets and network routes are available to the task?
- How should PRs link to `validation_report.json` and `revision_decision.json`?

Codex cloud also controls internet access for the agent phase. OpenAI documents that agent internet access is off by default after setup unless enabled for the environment.

## Current Policy

- Do not claim Codex cloud support from this repo yet.
- Do not add a Codex-specific MCP server.
- Do not assume local `runs/` evidence survives a cloud task.
- Treat cloud evidence as ephemeral unless it is explicitly exported, committed, uploaded, or summarized.

## Follow-Up Design Questions

- Should cloud evidence be committed to a branch under a sanitized path?
- Should cloud evidence be uploaded as CI artifacts instead?
- Should Workbench produce a PR comment summary that references exported evidence?
- Should cloud runs use `execution_host="codex"` plus later fields such as `host_task_id`, `host_branch`, `host_pr_url`, and `host_commit_sha`?

Those fields are intentionally deferred. This pass adds only `execution_host` and `response_source`.

## References

- Codex cloud docs: https://developers.openai.com/codex/cloud
- Codex cloud internet access: https://developers.openai.com/codex/cloud/internet-access
