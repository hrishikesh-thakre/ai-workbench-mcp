from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


TOOL_SMOKE_OPERATIONS = {"workbench_open_run", "workbench_select_model"}
ACCEPTANCE_OPERATIONS = {
    "workbench_open_run",
    "workbench_select_model",
    "workbench_record_execution",
    "workbench_validate_run",
    "workbench_quality_gate",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check a bounded Codex local/IDE live-test result without launching Codex or MCP."
    )
    parser.add_argument(
        "--stamp",
        help="Timestamp suffix emitted by tools/codex_live_test_handoff.py, for example 20260513-232125.",
    )
    parser.add_argument(
        "--run-id-stem",
        default="codex-live",
        help="Stem used by the handoff helper. Defaults to codex-live.",
    )
    parser.add_argument(
        "--tool-run-dir",
        help="Explicit tool-smoke run directory. Optional when --stamp is provided.",
    )
    parser.add_argument(
        "--acceptance-run-dir",
        help="Explicit acceptance-smoke run directory. Optional when --stamp is provided.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a machine-readable JSON result instead of the text report.",
    )
    return parser


def unique_run_dirs(stem: str, stamp: str) -> tuple[Path, Path]:
    safe_stem = stem.strip().replace("\\", "-").replace("/", "-") or "codex-live"
    parent = Path("runs") / f"{safe_stem}-{stamp}"
    return (
        parent / "tool-smoke",
        parent / "tiny-python-fix",
    )


def legacy_run_dirs(stem: str, stamp: str) -> tuple[Path, Path]:
    safe_stem = stem.strip().replace("\\", "-").replace("/", "-") or "codex-live"
    return (
        Path("runs") / f"{safe_stem}-{stamp}-tool-smoke",
        Path("runs") / f"{safe_stem}-{stamp}-tiny-python-fix",
    )


def read_json_file(path: Path) -> tuple[dict[str, Any], str | None]:
    if not path.exists():
        return {}, f"missing {path.as_posix()}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {}, f"invalid JSON in {path.as_posix()}: {exc}"
    if not isinstance(payload, dict):
        return {}, f"expected object JSON in {path.as_posix()}"
    return payload, None


def read_text_file(path: Path) -> tuple[str, str | None]:
    if not path.exists():
        return "", f"missing {path.as_posix()}"
    try:
        return path.read_text(encoding="utf-8"), None
    except Exception as exc:
        return "", f"could not read {path.as_posix()}: {exc}"


def metadata_line(text: str, label: str) -> str | None:
    match = re.search(rf"^- {re.escape(label)}: `([^`]+)`$", text, flags=re.MULTILINE)
    return match.group(1) if match else None


def event_operations(path: Path) -> tuple[set[str], list[dict[str, Any]], str | None]:
    if not path.exists():
        return set(), [], f"missing {path.as_posix()}"
    operations: set[str] = set()
    entries: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            return operations, entries, f"invalid JSONL at {path.as_posix()}:{line_number}: {exc}"
        if not isinstance(payload, dict):
            continue
        entries.append(payload)
        operation = payload.get("operation")
        if isinstance(operation, str):
            operations.add(operation)
    return operations, entries, None


def add_check(checks: list[dict[str, Any]], name: str, passed: bool, detail: str, value: Any = None) -> None:
    check: dict[str, Any] = {
        "name": name,
        "status": "passed" if passed else "failed",
        "detail": detail,
    }
    if value is not None:
        check["value"] = value
    checks.append(check)


def check_tool_smoke(run_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    metadata, metadata_error = read_json_file(run_dir / "task_metadata.json")
    selection, selection_error = read_json_file(run_dir / "model_selection.json")
    operations, _, events_error = event_operations(run_dir / "events.jsonl")

    add_check(checks, "tool_run_dir_exists", run_dir.exists(), run_dir.as_posix())
    add_check(
        checks,
        "tool_metadata_present",
        metadata_error is None,
        metadata_error or "task_metadata.json present",
    )
    add_check(
        checks,
        "tool_execution_host",
        metadata.get("execution_host") == "codex",
        "task_metadata.execution_host should be codex",
        metadata.get("execution_host"),
    )
    add_check(
        checks,
        "tool_model_selection_present",
        selection_error is None,
        selection_error or "model_selection.json present",
    )
    add_check(
        checks,
        "tool_model_selection_status",
        selection.get("status") == "selected",
        "model_selection.status should be selected",
        selection.get("status"),
    )
    add_check(
        checks,
        "tool_events_present",
        events_error is None,
        events_error or "events.jsonl present",
    )
    missing_operations = sorted(TOOL_SMOKE_OPERATIONS - operations)
    add_check(
        checks,
        "tool_events_operations",
        not missing_operations,
        "tool smoke events should include open and select",
        sorted(operations),
    )

    summary = {
        "run_dir": run_dir.as_posix(),
        "execution_host": metadata.get("execution_host"),
        "model_selection_status": selection.get("status"),
        "event_operations": sorted(operations),
    }
    return summary, checks


def check_acceptance_smoke(run_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    checks: list[dict[str, Any]] = []
    metadata, metadata_error = read_json_file(run_dir / "task_metadata.json")
    selection, selection_error = read_json_file(run_dir / "model_selection.json")
    validation, validation_error = read_json_file(run_dir / "validation_report.json")
    decision, decision_error = read_json_file(run_dir / "revision_decision.json")
    final_prompt, final_prompt_error = read_text_file(run_dir / "final_prompt.md")
    model_output, model_output_error = read_text_file(run_dir / "model_output.md")
    operations, events, events_error = event_operations(run_dir / "events.jsonl")

    output_host = metadata_line(model_output, "Execution Host")
    response_source = metadata_line(model_output, "Response Source")
    final_prompt_host = metadata_line(final_prompt, "Execution Host")
    final_prompt_mode = metadata_line(final_prompt, "Mode")

    record_event_sources = [
        entry.get("summary", {}).get("response_source")
        for entry in events
        if entry.get("operation") == "workbench_record_execution" and isinstance(entry.get("summary"), dict)
    ]
    record_event_hosts = [
        entry.get("summary", {}).get("execution_host")
        for entry in events
        if entry.get("operation") == "workbench_record_execution" and isinstance(entry.get("summary"), dict)
    ]

    add_check(checks, "acceptance_run_dir_exists", run_dir.exists(), run_dir.as_posix())
    add_check(
        checks,
        "acceptance_metadata_present",
        metadata_error is None,
        metadata_error or "task_metadata.json present",
    )
    add_check(
        checks,
        "acceptance_execution_host",
        metadata.get("execution_host") == "codex",
        "task_metadata.execution_host should be codex",
        metadata.get("execution_host"),
    )
    add_check(
        checks,
        "acceptance_final_prompt_present",
        final_prompt_error is None,
        final_prompt_error or "final_prompt.md present",
    )
    add_check(
        checks,
        "acceptance_final_prompt_host",
        final_prompt_host == "codex" and final_prompt_mode == "codex",
        "final_prompt.md should include Execution Host and Mode codex",
        {"execution_host": final_prompt_host, "mode": final_prompt_mode},
    )
    add_check(
        checks,
        "acceptance_model_selection_present",
        selection_error is None,
        selection_error or "model_selection.json present",
    )
    add_check(
        checks,
        "acceptance_model_selection_status",
        selection.get("status") == "selected",
        "model_selection.status should be selected",
        selection.get("status"),
    )
    add_check(
        checks,
        "acceptance_model_output_present",
        model_output_error is None,
        model_output_error or "model_output.md present",
    )
    add_check(
        checks,
        "acceptance_model_output_host",
        output_host == "codex",
        "model_output.md Execution Host should be codex",
        output_host,
    )
    add_check(
        checks,
        "acceptance_response_source",
        response_source == "codex",
        "model_output.md Response Source should be codex",
        response_source,
    )
    add_check(
        checks,
        "acceptance_validation_present",
        validation_error is None,
        validation_error or "validation_report.json present",
    )
    add_check(
        checks,
        "acceptance_validation_passed",
        validation.get("overall_status") == "passed" and validation.get("sign_off_ready") is True,
        "validation should pass and be sign-off ready",
        {
            "overall_status": validation.get("overall_status"),
            "sign_off_ready": validation.get("sign_off_ready"),
            "confidence": validation.get("confidence"),
        },
    )
    add_check(
        checks,
        "acceptance_quality_gate_present",
        decision_error is None,
        decision_error or "revision_decision.json present",
    )
    add_check(
        checks,
        "acceptance_quality_gate_accepted",
        decision.get("final_status") == "accepted",
        "quality gate final_status should be accepted",
        decision.get("final_status"),
    )
    add_check(
        checks,
        "acceptance_events_present",
        events_error is None,
        events_error or "events.jsonl present",
    )
    missing_operations = sorted(ACCEPTANCE_OPERATIONS - operations)
    add_check(
        checks,
        "acceptance_events_operations",
        not missing_operations,
        "acceptance events should include the five acceptance operations",
        sorted(operations),
    )
    add_check(
        checks,
        "acceptance_record_event_metadata",
        "codex" in record_event_sources and "codex" in record_event_hosts,
        "record-execution event should carry codex source and host",
        {"execution_host": record_event_hosts, "response_source": record_event_sources},
    )

    summary = {
        "run_dir": run_dir.as_posix(),
        "execution_host": metadata.get("execution_host"),
        "response_source": response_source,
        "model_selection_status": selection.get("status"),
        "validation_status": validation.get("overall_status"),
        "sign_off_ready": validation.get("sign_off_ready"),
        "confidence": validation.get("confidence"),
        "quality_gate_status": decision.get("final_status"),
        "event_operations": sorted(operations),
    }
    return summary, checks


def print_text_report(result: dict[str, Any]) -> None:
    status = "PASS" if result["ok"] else "FAIL"
    print("Codex local/IDE live-test result check")
    print(f"RESULT: {status}")
    print()

    tool = result["summary"]["tool_smoke"]
    acceptance = result["summary"]["acceptance_smoke"]
    print("Tool smoke:")
    print(f"- run_dir: {tool['run_dir']}")
    print(f"- execution_host: {tool.get('execution_host')}")
    print(f"- model_selection: {tool.get('model_selection_status')}")
    print()
    print("Acceptance smoke:")
    print(f"- run_dir: {acceptance['run_dir']}")
    print(f"- execution_host: {acceptance.get('execution_host')}")
    print(f"- response_source: {acceptance.get('response_source')}")
    print(f"- validation: {acceptance.get('validation_status')}")
    print(f"- sign_off_ready: {acceptance.get('sign_off_ready')}")
    print(f"- confidence: {acceptance.get('confidence')}")
    print(f"- quality_gate: {acceptance.get('quality_gate_status')}")

    failed = [check for check in result["checks"] if check["status"] != "passed"]
    if failed:
        print()
        print("Failures:")
        for check in failed:
            value = check.get("value")
            suffix = f" ({value})" if value is not None else ""
            print(f"- {check['name']}: {check['detail']}{suffix}")


def resolve_run_dirs(args: argparse.Namespace) -> tuple[Path, Path]:
    if args.stamp:
        default_tool_run_dir, default_acceptance_run_dir = unique_run_dirs(args.run_id_stem, args.stamp)
        old_tool_run_dir, old_acceptance_run_dir = legacy_run_dirs(args.run_id_stem, args.stamp)
        if not default_tool_run_dir.exists() and not default_acceptance_run_dir.exists():
            if old_tool_run_dir.exists() or old_acceptance_run_dir.exists():
                default_tool_run_dir, default_acceptance_run_dir = old_tool_run_dir, old_acceptance_run_dir
    else:
        default_tool_run_dir, default_acceptance_run_dir = None, None

    tool_run_dir = Path(args.tool_run_dir) if args.tool_run_dir else default_tool_run_dir
    acceptance_run_dir = Path(args.acceptance_run_dir) if args.acceptance_run_dir else default_acceptance_run_dir

    if tool_run_dir is None or acceptance_run_dir is None:
        raise ValueError("Provide --stamp or both --tool-run-dir and --acceptance-run-dir.")

    return tool_run_dir, acceptance_run_dir


def build_result(tool_run_dir: Path, acceptance_run_dir: Path) -> dict[str, Any]:
    tool_summary, tool_checks = check_tool_smoke(tool_run_dir)
    acceptance_summary, acceptance_checks = check_acceptance_smoke(acceptance_run_dir)
    checks = [*tool_checks, *acceptance_checks]
    return {
        "ok": all(check["status"] == "passed" for check in checks),
        "summary": {
            "tool_smoke": tool_summary,
            "acceptance_smoke": acceptance_summary,
        },
        "checks": checks,
    }


def main() -> int:
    args = build_parser().parse_args()
    try:
        tool_run_dir, acceptance_run_dir = resolve_run_dirs(args)
        result = build_result(tool_run_dir, acceptance_run_dir)
    except Exception as exc:
        result = {
            "ok": False,
            "summary": {
                "tool_smoke": {"run_dir": args.tool_run_dir},
                "acceptance_smoke": {"run_dir": args.acceptance_run_dir},
            },
            "checks": [
                {
                    "name": "arguments",
                    "status": "failed",
                    "detail": str(exc),
                }
            ],
        }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_text_report(result)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
