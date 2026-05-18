# PyPI Publishing Prep

Published package version: `ai-workbench-mcp==0.3.0a0`.

The `0.3.0a0` package is published and exact-version install verified on TestPyPI and PyPI as of 2026-05-18. MCP Registry metadata validates for `0.3.0a0`, but registry publication is still blocked by an expired registry token and requires a refreshed login. The latest historical verified publication before this release was `ai-workbench-mcp==0.2.0a0`.

This guide records the package boundary and release checklist. Recheck the project name and version on PyPI immediately before any future upload because PyPI versions are immutable.

## Current Package Boundary

The prepared `0.3.0a0` source build installs the `ai_workbench_mcp` package, the `ai-workbench-mcp` console script, and the `ai-workbench-bootstrap-assets` console script.

Historical note: the published `0.2.0a0` wheel is code/server only. It installs the `ai_workbench_mcp` package and the `ai-workbench-mcp` console script.

The source tree includes a package-resource pass for the `0.3.0a0` build. New source builds include bootstrappable defaults under `ai_workbench_mcp/assets/`:

- `configs/`, including `policy_packs.yaml`, `validation_profiles.yaml`, project defaults, model selection defaults, routing feedback policy, and quality-loop defaults.
- `prompts/approved/`, including the public approved prompt catalog.
- `recipes/`, including the Goose acceptance and smoke recipes.

The wheel does not include `examples/`, `evals/`, committed sample evidence, local `runs/`, or provider setup. Full Goose recipe workflows can still be run from a checked-out repository, but installed-package users can now materialize the default repo-style assets when they do not have a checkout:

```powershell
python -m ai_workbench_mcp.tools.bootstrap_assets --target-dir .
```

The console-script equivalent is:

```powershell
ai-workbench-bootstrap-assets --target-dir .
```

The bootstrap command writes `configs/`, `prompts/`, and `recipes/` under the target directory. Existing files are left untouched unless `--force` is supplied:

```powershell
python -m ai_workbench_mcp.tools.bootstrap_assets --target-dir . --force
```

To inspect the packaged asset plan without writing files:

```powershell
python -m ai_workbench_mcp.tools.bootstrap_assets --target-dir . --dry-run
```

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

Before any upload, ensure `dist/` contains only the intended target version. Do
not upload `dist/*` from a workspace that still contains artifacts from an older
release:

```powershell
Get-ChildItem dist
```

Check metadata:

```powershell
python -m twine check dist/*
```

Smoke the wheel:

```powershell
python -m pip install --force-reinstall (Get-ChildItem dist\*.whl | Select-Object -First 1).FullName
python -c "import ai_workbench_mcp; from ai_workbench_mcp import server; from ai_workbench_mcp.tools import model_select, validate_run"
python -m ai_workbench_mcp.tools.bootstrap_assets --target-dir $env:TEMP\ai-workbench-mcp-assets-smoke --groups configs --force
```

Fresh virtual environment smoke:

```powershell
python -m venv $env:TEMP\ai-workbench-mcp-wheel-smoke
& "$env:TEMP\ai-workbench-mcp-wheel-smoke\Scripts\python.exe" -m pip install --upgrade pip
& "$env:TEMP\ai-workbench-mcp-wheel-smoke\Scripts\python.exe" -m pip install (Get-ChildItem dist\*.whl | Select-Object -First 1).FullName
& "$env:TEMP\ai-workbench-mcp-wheel-smoke\Scripts\python.exe" -c "import ai_workbench_mcp; from ai_workbench_mcp import server"
& "$env:TEMP\ai-workbench-mcp-wheel-smoke\Scripts\python.exe" -c "from pathlib import Path; import sys; scripts=Path(sys.executable).parent; assert (scripts/'ai-workbench-mcp.exe').exists() or (scripts/'ai-workbench-mcp').exists()"
& "$env:TEMP\ai-workbench-mcp-wheel-smoke\Scripts\python.exe" -c "from pathlib import Path; import sys; scripts=Path(sys.executable).parent; assert (scripts/'ai-workbench-bootstrap-assets.exe').exists() or (scripts/'ai-workbench-bootstrap-assets').exists()"
& "$env:TEMP\ai-workbench-mcp-wheel-smoke\Scripts\python.exe" -m ai_workbench_mcp.tools.bootstrap_assets --target-dir "$env:TEMP\ai-workbench-mcp-wheel-assets" --groups configs --force
```

Do not run `ai-workbench-mcp` directly as a smoke command. It is a stdio MCP server entrypoint, not a normal help-printing CLI.

## TestPyPI Dry Run

Status: TestPyPI dry run completed for `ai-workbench-mcp==0.3.0a0` on 2026-05-18.

TestPyPI package page:

```text
https://test.pypi.org/project/ai-workbench-mcp/0.3.0a0/
```

The completed rehearsal verified fresh artifacts, `twine check`, a local wheel smoke in a fresh virtual environment, upload to TestPyPI, and an exact-version install smoke from TestPyPI with PyPI as the dependency fallback.

Historical status: TestPyPI dry run completed for `ai-workbench-mcp==0.2.0a0` on 2026-05-15.

Historical TestPyPI package page:

```text
https://test.pypi.org/project/ai-workbench-mcp/0.2.0a0/
```

The historical rehearsal verified fresh artifacts, `twine check`, a local wheel smoke in a fresh virtual environment, upload to TestPyPI, and an exact-version install smoke from TestPyPI with PyPI as the dependency fallback.

Do not rerun the upload for `0.3.0a0`. Future TestPyPI dry runs require a version bump and a fresh existence check. Only run this after confirming credentials and release intent. Do not use `--skip-existing`:

```powershell
python -m twine upload --repository testpypi --non-interactive dist/*
```

Then verify installation in a fresh environment:

```powershell
python -m pip install --no-cache-dir --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple "ai-workbench-mcp==0.3.0a0"
python -c "import ai_workbench_mcp; from ai_workbench_mcp import server"
python -c "import shutil; assert shutil.which('ai-workbench-mcp')"
python -c "import shutil; assert shutil.which('ai-workbench-bootstrap-assets')"
```

## PyPI Upload

Status: PyPI release completed for `ai-workbench-mcp==0.3.0a0` on 2026-05-18.

PyPI package page:

```text
https://pypi.org/project/ai-workbench-mcp/0.3.0a0/
```

The completed release verified fresh artifacts, `twine check`, a local wheel smoke in a fresh virtual environment, upload to PyPI, and an exact-version install smoke from PyPI.

Historical status: PyPI release completed for `ai-workbench-mcp==0.2.0a0` on 2026-05-15.

Historical PyPI package page:

```text
https://pypi.org/project/ai-workbench-mcp/0.2.0a0/
```

The historical release verified fresh artifacts, `twine check`, a local wheel smoke in a fresh virtual environment, upload to PyPI, and an exact-version install smoke from PyPI.

Do not rerun the upload for `0.2.0a0` or `0.3.0a0`. Future PyPI uploads require a version bump, TestPyPI verification, final version review, and explicit release approval:

```powershell
python -m twine upload --repository pypi --non-interactive dist/*
```

Published install command:

```bash
python -m pip install ai-workbench-mcp==0.3.0a0
```

## MCP Registry Prep

Status for `io.github.hrishikesh-thakre/ai-workbench-mcp` version `0.3.0a0`: `server.json` validates with the official `mcp-publisher` CLI, but publication is blocked by an expired Registry JWT token. Refresh registry login before rerunning publish.

Historical status: MCP Registry publication completed for `io.github.hrishikesh-thakre/ai-workbench-mcp` version `0.2.0a0` on 2026-05-16.

Registry API lookup:

```text
https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.hrishikesh-thakre%2Fai-workbench-mcp
```

The MCP Registry metadata is prepared in `server.json`. The public proof note for the historical `0.2.0a0` publication is `docs/publishing/mcp-registry-proof.md`.

Registry publication remains separate from package release. For the PyPI package path, keep `server.json.version` and `server.json.packages[0].version` aligned with `pyproject.toml` `project.version`, and keep the hidden README `mcp-name` marker exactly matched to `server.json.name`.

Do not rerun `mcp-publisher publish` for `0.2.0a0`. The `0.3.0a0` registry update has passed `mcp-publisher validate server.json`; publication requires a refreshed registry login, explicit approval, and then `mcp-publisher publish server.json`. Do not upload to TestPyPI or PyPI as part of registry metadata maintenance.
