# Codex Local/IDE Setup

AI Workbench uses the same `ai-workbench mcp serve` stdio server for Goose and Codex. Codex is a first-class execution host, but this pass does not create a Codex-specific server.

## Prerequisites

- Install this repository in editable mode:

```bash
python -m pip install -e .
```

- Confirm the package is importable:

```bash
python -c "import ai_workbench_mcp; print('ai-workbench ready')"
```

## Configure Codex

Codex supports MCP servers from the CLI and IDE extension with shared configuration. OpenAI's MCP setup docs show the same `codex mcp add` and `codex mcp list` flow for MCP servers.

For the local Workbench stdio server, add this server to Codex:

```bash
codex mcp add aiWorkbench -- ai-workbench mcp serve
codex mcp list
```

If you manage Codex MCP config directly, keep the server name short and point it at the installed command:

```toml
[mcp_servers.aiWorkbench]
command = "ai-workbench"
args = ["mcp", "serve"]
```

## Host Metadata

When Codex opens a run, pass:

```text
execution_host="codex"
```

When Codex records its response, pass:

```text
response_source="codex"
```

Workbench still writes evidence under `runs/<run_id>/` and still requires deterministic validation plus a quality-gate decision before a run is accepted.

## Safe Live Test

After setup, use `docs/walkthroughs/codex-acceptance-demo.md` for the bounded local/IDE proof. If you want a visible countdown and generated prompt first, use `docs/codex/live-test-handoff.md`.

Do not run `ai-workbench mcp serve` directly as a foreground terminal command; Codex should launch it as an MCP server.

## References

- OpenAI Docs MCP quickstart: https://developers.openai.com/learn/docs-mcp
- Codex CLI docs: https://developers.openai.com/codex/cli
- Codex IDE extension docs: https://developers.openai.com/codex/ide
