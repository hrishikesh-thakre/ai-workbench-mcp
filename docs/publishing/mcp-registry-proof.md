# MCP Registry Proof

Status: `0.3.0a0` registry publication recorded as complete; `0.6.0a0`
registry update pending PyPI publication and explicit approval
Latest published registry version: `0.3.0a0`
Target metadata version: `0.6.0a0`
Date verified in repo docs: 2026-05-18

## Registry Identity

| Field | Value |
|---|---|
| Server name | `io.github.hrishikesh-thakre/ai-workbench-mcp` |
| Title | `AI Workbench MCP` |
| Package | `ai-workbench-mcp` |
| Latest published package version | `0.3.0a0` |
| Target package version | `0.6.0a0` |
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

Published PyPI install for the latest historical registry version:

```bash
python -m pip install ai-workbench-mcp==0.3.0a0
```

This installs the server code, the `ai-workbench-mcp` stdio console script, and
the `ai-workbench-bootstrap-assets` helper.

The v0.6 target package adds the `ai-workbench-bootstrap` adoption command for
external repositories:

```bash
python -m pip install ai-workbench-mcp==0.6.0a0
ai-workbench-bootstrap --target .
```

Installed-package users can bootstrap default configs, prompts, recipes, and
PR-gate adoption assets after the v0.6 package is published.
Full demo fixtures, examples, evals, and private run evidence remain outside the
published wheel.

## Version History

| Version | Registry status | Verified |
|---|---|---|
| `0.2.0a0` | active, not latest | 2026-05-16 |
| `0.3.0a0` | active, latest | 2026-05-18 |
| `0.6.0a0` | pending PyPI publication and explicit approval | pending |

## Maintenance Rule

Do not rerun registry publication for `0.2.0a0` or `0.3.0a0`.

Future registry updates require:

- version bump in `pyproject.toml`
- aligned `server.json.version`
- aligned `server.json.packages[0].version`
- published package version
- registry validation
- explicit release approval

Registry metadata maintenance must not upload to TestPyPI or PyPI.
