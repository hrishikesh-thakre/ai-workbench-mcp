from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import sys
import textwrap
import time


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare a bounded Codex local/IDE live-test handoff without launching Codex."
    )
    parser.add_argument(
        "--countdown-seconds",
        type=int,
        default=15,
        help="Visible countdown before printing the final START CODEX message.",
    )
    parser.add_argument(
        "--out-dir",
        default="runs/codex-live-handoff",
        help="Ignored local directory where the generated Codex prompt is written.",
    )
    parser.add_argument(
        "--run-id-stem",
        default="codex-live",
        help="Stem used for unique local run directories.",
    )
    parser.add_argument(
        "--stamp",
        help="Optional deterministic timestamp suffix. Defaults to current local time.",
    )
    parser.add_argument(
        "--skip-codex-cli-check",
        action="store_true",
        help="Skip the optional codex mcp list check. Useful for IDE-only testing.",
    )
    parser.add_argument(
        "--codex-timeout-seconds",
        type=int,
        default=10,
        help="Timeout for the optional codex mcp list check.",
    )
    return parser


def run_check(command: list[str], timeout_seconds: int) -> tuple[int, str]:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        return 124, "timed out"
    except OSError as exc:
        return 127, str(exc)
    output = "\n".join(part for part in (result.stdout.strip(), result.stderr.strip()) if part)
    return result.returncode, output


def unique_run_dirs(stem: str, stamp: str) -> tuple[Path, Path]:
    safe_stem = stem.strip().replace("\\", "-").replace("/", "-") or "codex-live"
    parent = Path("runs") / f"{safe_stem}-{stamp}"
    return (
        parent / "tool-smoke",
        parent / "tiny-python-fix",
    )


def result_check_command(stem: str, stamp: str) -> str:
    command = f"python tools/check_codex_live_result.py --stamp {stamp}"
    if stem != "codex-live":
        command = f"{command} --run-id-stem {stem}"
    return command


def build_codex_prompt(tool_run_dir: Path, acceptance_run_dir: Path) -> str:
    return textwrap.dedent(
        f"""
        Use AI Workbench MCP for a bounded Codex local/IDE live test.

        Safety:
        - Do not ask Codex to launch another Codex session.
        - Do not start ai-workbench-mcp directly; use the MCP tools already registered in Codex.
        - Do not delegate this to Codex cloud.
        - If a tool call hangs or fails unexpectedly, stop and report the failing step.
        - Do not reuse an existing run directory.

        Tool smoke:
        1. Call workbench_open_run with:
           project="ai_workbench_mcp"
           task="Codex local MCP tool smoke. Do not edit tracked files."
           run_dir="{tool_run_dir.as_posix()}"
           risk="low"
           execution_host="codex"

        2. Call workbench_select_model with:
           project="ai_workbench_mcp"
           task_type="implement"
           risk="low"
           out="{(tool_run_dir / "model_selection.json").as_posix()}"
           complexity_score=4

        3. Confirm task_metadata.json contains execution_host="codex".

        Acceptance smoke:
        1. Open the acceptance run with workbench_open_run:
           project="ai_workbench_mcp"
           task="Fix examples/tiny-python-fix/calculator.py so python -m unittest discover -s examples/tiny-python-fix -p test_*.py passes."
           run_dir="{acceptance_run_dir.as_posix()}"
           risk="low"
           execution_host="codex"

        2. Select the advisory model/runtime tier with workbench_select_model:
           project="ai_workbench_mcp"
           task_type="implement"
           risk="low"
           out="{(acceptance_run_dir / "model_selection.json").as_posix()}"
           validation_profile="tiny_python_fix"
           complexity_score=4

        3. Fix examples/tiny-python-fix/calculator.py so:
           python -m unittest discover -s examples/tiny-python-fix -p test_*.py
           passes. Keep the change minimal.

        4. Record execution with workbench_record_execution:
           project="ai_workbench_mcp"
           run_dir="{acceptance_run_dir.as_posix()}"
           response_text="Summary:\\nFixed examples/tiny-python-fix/calculator.py so add returns the sum of two integers.\\n\\nFiles touched:\\n- examples/tiny-python-fix/calculator.py\\n\\nValidation run:\\n- Workbench validation is run in the next step.\\n\\nRisks / follow-ups:\\n- None."
           response_source="codex"
           files_touched=["examples/tiny-python-fix/calculator.py"]

        5. Validate with workbench_validate_run:
           project="ai_workbench_mcp"
           out_dir="{acceptance_run_dir.as_posix()}"
           profile="tiny_python_fix"
           changed_files=["examples/tiny-python-fix/calculator.py"]

        6. Apply workbench_quality_gate:
           project="ai_workbench_mcp"
           run_dir="{acceptance_run_dir.as_posix()}"
           mode="auto"
           risk="low"

        7. Do not claim accepted unless validation passes and the quality gate returns accepted.
        """
    ).strip() + "\n"


def print_countdown(seconds: int) -> None:
    if seconds <= 0:
        return
    for remaining in range(seconds, 0, -1):
        print(f"START CODEX IN {remaining:02d}s", flush=True)
        time.sleep(1)


def main() -> int:
    args = build_parser().parse_args()
    stamp = args.stamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    tool_run_dir, acceptance_run_dir = unique_run_dirs(args.run_id_stem, stamp)

    print("Codex local/IDE live-test handoff")
    print("This helper does not launch Codex or start the MCP stdio server.")
    print()

    try:
        import ai_workbench_mcp  # noqa: F401
    except Exception as exc:
        print(f"FAIL package import: {exc}")
        print("Run: python -m pip install -e .")
        return 1
    print("OK package import: ai_workbench_mcp")

    server_command = shutil.which("ai-workbench-mcp")
    if server_command:
        print("OK server command: ai-workbench-mcp")
    else:
        print("WARN server command not found on PATH. Run: python -m pip install -e .")

    if args.skip_codex_cli_check:
        print("SKIP codex mcp list")
    else:
        codex_command = shutil.which("codex")
        if not codex_command:
            print("WARN codex CLI not found on PATH. IDE-only users can still use the generated prompt.")
        else:
            code, output = run_check([codex_command, "mcp", "list"], args.codex_timeout_seconds)
            if code == 0:
                print("OK codex mcp list")
            else:
                print(f"WARN codex mcp list returned {code}: {output}")

    live_run_parent = tool_run_dir.parent
    existing_dirs = [path for path in (live_run_parent, tool_run_dir, acceptance_run_dir) if path.exists()]
    if existing_dirs:
        print("FAIL refusing to reuse existing run directories:")
        for path in existing_dirs:
            print(f"- {path.as_posix()}")
        print("Run again with a different --stamp or --run-id-stem.")
        return 1

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = out_dir / f"codex_live_prompt_{stamp}.txt"
    prompt = build_codex_prompt(tool_run_dir, acceptance_run_dir)
    prompt_path.write_text(prompt, encoding="utf-8")

    print()
    print(f"Prompt written: {prompt_path.as_posix()}")
    print(f"Live run parent dir: {live_run_parent.as_posix()}")
    print(f"Tool smoke run dir: {tool_run_dir.as_posix()}")
    print(f"Acceptance run dir: {acceptance_run_dir.as_posix()}")
    print(f"After Codex finishes, run: {result_check_command(args.run_id_stem, stamp)}")
    print(f"Analyze only this live batch with: python tools/run_analyze.py --runs-dir {live_run_parent.as_posix()} --out-dir {(live_run_parent / '_reports').as_posix()}")
    print()
    print_countdown(max(0, args.countdown_seconds))
    print("READY: Start Codex now, then use the generated prompt.")
    print()
    print(prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
