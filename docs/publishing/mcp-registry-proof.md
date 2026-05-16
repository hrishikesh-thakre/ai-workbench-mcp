# MCP Registry Proof

Status: registry publication recorded as complete  
Version: `0.2.0a0`  
Date verified in repo docs: 2026-05-16

## Registry Identity

| Field | Value |
|---|---|
| Server name | `io.github.hrishikesh-thakre/ai-workbench-mcp` |
| Title | `AI Workbench MCP` |
| Package | `ai-workbench-mcp` |
| Package version | `0.2.0a0` |
| Transport | `stdio` |
| Repository | `https://github.com/hrishikesh-thakre/ai-workbench-mcp` |
| License | `Apache-2.0` |

Registry lookup:

```text
https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.hrishikesh-thakre%2Fai-workbench-mcp
```

Local registry metadata:

```text
server.json
```

The hidden README marker must remain aligned with `server.json.name`:

```text
<!-- mcp-name: io.github.hrishikesh-thakre/ai-workbench-mcp -->
```

## Tool List

The server exposes:

```text
workbench_open_run
workbench_select_model
workbench_record_execution
workbench_validate_run
workbench_quality_gate
workbench_analyze_runs
```

## Install Path

Published PyPI install:

```bash
python -m pip install ai-workbench-mcp==0.2.0a0
```

This installs the server code and `ai-workbench-mcp` stdio console script.

Full Goose recipe workflows still require a checked-out repository because configs, prompts, recipes, examples, evals, and validation profiles are repo assets.

## Maintenance Rule

Do not rerun registry publication for `0.2.0a0`.

Future registry updates require:

- version bump in `pyproject.toml`
- aligned `server.json.version`
- aligned `server.json.packages[0].version`
- published package version
- registry validation
- explicit release approval

Registry metadata maintenance must not upload to TestPyPI or PyPI.
