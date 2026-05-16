# PyPI Publishing Prep

AI Workbench MCP is published to PyPI as `ai-workbench-mcp==0.2.0a0`.

This guide records the package boundary and release checklist. Recheck the project name and version on PyPI immediately before any future upload because PyPI versions are immutable.

## Current Package Boundary

The current wheel is code/server only. It installs the `ai_workbench_mcp` package and the `ai-workbench-mcp` console script.

Full Goose recipe workflows still require a checked-out repository because the default `configs/`, `prompts/`, `recipes/`, `examples/`, `evals/`, and validation profiles are repo assets. A future package-resource pass can move selected defaults into the wheel.

## Local Build Check

Confirm only intended files are tracked before release preparation. The handoff note `external_launch_execution_prep.md` is local planning context and must remain untracked unless a later pass explicitly chooses to publish it:

```powershell
git status --short
```

Install build and publish tooling before package checks:

```powershell
python -m pip install -e ".[dev,publish]"
```

Build artifacts:

```powershell
python -m build
```

Check metadata:

```powershell
python -m twine check dist/*
```

Smoke the wheel:

```powershell
python -m pip install --force-reinstall (Get-ChildItem dist\*.whl | Select-Object -First 1).FullName
python -c "import ai_workbench_mcp; from ai_workbench_mcp import server; from ai_workbench_mcp.tools import model_select, validate_run"
```

Fresh virtual environment smoke:

```powershell
python -m venv $env:TEMP\ai-workbench-mcp-wheel-smoke
& "$env:TEMP\ai-workbench-mcp-wheel-smoke\Scripts\python.exe" -m pip install --upgrade pip
& "$env:TEMP\ai-workbench-mcp-wheel-smoke\Scripts\python.exe" -m pip install (Get-ChildItem dist\*.whl | Select-Object -First 1).FullName
& "$env:TEMP\ai-workbench-mcp-wheel-smoke\Scripts\python.exe" -c "import ai_workbench_mcp; from ai_workbench_mcp import server"
& "$env:TEMP\ai-workbench-mcp-wheel-smoke\Scripts\python.exe" -c "import shutil; assert shutil.which('ai-workbench-mcp')"
```

Do not run `ai-workbench-mcp` directly as a smoke command. It is a stdio MCP server entrypoint, not a normal help-printing CLI.

## TestPyPI Dry Run

Status: TestPyPI dry run completed for `ai-workbench-mcp==0.2.0a0` on 2026-05-15.

TestPyPI package page:

```text
https://test.pypi.org/project/ai-workbench-mcp/0.2.0a0/
```

The completed rehearsal verified fresh artifacts, `twine check`, a local wheel smoke in a fresh virtual environment, upload to TestPyPI, and an exact-version install smoke from TestPyPI with PyPI as the dependency fallback.

Only run this after confirming credentials and release intent, and only after checking that the target version does not already exist on TestPyPI. Do not use `--skip-existing`:

```powershell
python -m twine upload --repository testpypi --non-interactive dist/*
```

Then verify installation in a fresh environment:

```powershell
python -m pip install --no-cache-dir --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple "ai-workbench-mcp==0.2.0a0"
python -c "import ai_workbench_mcp; from ai_workbench_mcp import server"
python -c "import shutil; assert shutil.which('ai-workbench-mcp')"
```

## PyPI Upload

Status: PyPI release completed for `ai-workbench-mcp==0.2.0a0` on 2026-05-15.

PyPI package page:

```text
https://pypi.org/project/ai-workbench-mcp/0.2.0a0/
```

The completed release verified fresh artifacts, `twine check`, a local wheel smoke in a fresh virtual environment, upload to PyPI, and an exact-version install smoke from PyPI.

Do not rerun the upload for `0.2.0a0`. Future PyPI uploads require a version bump, TestPyPI verification, final version review, and explicit release approval:

```powershell
python -m twine upload --repository pypi --non-interactive dist/*
```

Published install command:

```bash
python -m pip install ai-workbench-mcp==0.2.0a0
```

## MCP Registry Prep

Status: MCP Registry publication completed for `io.github.hrishikesh-thakre/ai-workbench-mcp` version `0.2.0a0` on 2026-05-16.

Registry API lookup:

```text
https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.hrishikesh-thakre%2Fai-workbench-mcp
```

The MCP Registry metadata is prepared in `server.json`. The public proof note is `docs/publishing/mcp-registry-proof.md`.

Registry publication remains separate from package release. For the PyPI package path, keep `server.json.version` and `server.json.packages[0].version` aligned with `pyproject.toml` `project.version`, and keep the hidden README `mcp-name` marker exactly matched to `server.json.name`.

Do not rerun `mcp-publisher publish` for `0.2.0a0`. Future registry updates require a version bump, a published package version, `mcp-publisher validate`, and explicit approval. Do not upload to TestPyPI or PyPI as part of registry metadata maintenance.
