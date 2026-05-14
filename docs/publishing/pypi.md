# PyPI Publishing Prep

AI Workbench MCP has not been published to PyPI yet.

This guide prepares a package release, but it does not authorize or automate publishing. Recheck the project name on PyPI immediately before any upload.

## Current Package Boundary

The current wheel is code/server only. It installs the `ai_workbench_mcp` package and the `ai-workbench-mcp` console script.

Full Goose recipe workflows still require a checked-out repository because the default `configs/`, `prompts/`, `recipes/`, `examples/`, `evals/`, and validation profiles are repo assets. A future package-resource pass can move selected defaults into the wheel.

## Local Build Check

Install build tools:

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

Only run this after confirming credentials and release intent:

```powershell
python -m twine upload --repository testpypi dist/*
```

Then verify installation in a fresh environment:

```powershell
python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple ai-workbench-mcp
python -c "import ai_workbench_mcp; from ai_workbench_mcp import server"
python -c "import shutil; assert shutil.which('ai-workbench-mcp')"
```

## PyPI Upload

Only run this after TestPyPI verification, final version review, and explicit release approval:

```powershell
python -m twine upload dist/*
```

After publishing, update README install instructions from source install to:

```bash
python -m pip install ai-workbench-mcp
```
