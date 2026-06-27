from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from types import SimpleNamespace

from .supervisor.daemon import (
    SupervisorDaemon,
    install_windows_startup,
    request_stop,
    start_background,
    startup_status,
    status_rows,
    uninstall_windows_startup,
)
from .supervisor.daemon_log import read_daemon_logs, write_daemon_log
from .supervisor.daemon_state import (
    get_state_path,
    list_projects,
    register_project,
    unregister_project,
)
from .supervisor.report_browser import collect_reports, open_report_ref, resolve_report_ref


SUPERVISOR_POLICY_DIR = Path(__file__).parent / "supervisor" / "policies"
CODEX_CORE_TOOL_MATCHER = "Bash|Shell|Write|Edit|MultiEdit|ApplyPatch|apply_patch|write|edit|bash"


def _codex_tool_matcher(profile: str) -> str:
    return "*" if profile == "all" else CODEX_CORE_TOOL_MATCHER


def cmd_mcp_serve(_args: argparse.Namespace) -> int:
    from .server import main as server_main

    server_main()
    return 0


def cmd_bootstrap(args: argparse.Namespace) -> int:
    from .tools.bootstrap_assets import bootstrap_repository, print_summary

    summary = bootstrap_repository(args.target, force=args.force, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_summary(summary)
    return 2 if summary["counts"]["skipped"] else 0


def cmd_demo(args: argparse.Namespace) -> int:
    from .tools.demo import main as demo_main

    argv = ["--target", args.target]
    if args.json:
        argv.append("--json")
    return demo_main(argv)


def cmd_validate(args: argparse.Namespace) -> int:
    from .tools.validate_run import validate_run_payload

    report = validate_run_payload(
        SimpleNamespace(
            project=args.project,
            profile=args.profile,
            changed_files=args.changed_file or [],
            out_dir=args.run_dir,
            report_name=args.report_name,
            task_test_command=args.task_test_command,
        )
    )
    print(f"validation_report={Path(args.run_dir) / args.report_name}")
    print(f"overall_status={report['overall_status']}")
    print(f"sign_off_ready={str(report['sign_off_ready']).lower()}")
    return 0 if report.get("overall_status") == "passed" else 2


def cmd_gate(args: argparse.Namespace) -> int:
    from .tools.quality_loop import quality_gate_exit_code, quality_gate_payload

    decision = quality_gate_payload(
        SimpleNamespace(
            project=args.project,
            run_dir=args.run_dir,
            mode=args.mode,
            risk=args.risk,
            validation_report=args.validation_report,
            review_prompt=args.review_prompt,
            review_output=args.review_output,
        )
    )
    print(f"revision_decision={Path(args.run_dir) / 'revision_decision.json'}")
    print(f"final_status={decision['final_status']}")
    return quality_gate_exit_code(decision)


def cmd_pr_gate(args: argparse.Namespace) -> int:
    from .tools.pr_gate import pr_gate_payload

    decision = pr_gate_payload(args)
    print(f"pr_comment={args.out}")
    print(f"pr_decision={args.json_out}")
    print(f"outcome={decision['outcome']}")
    return 2 if args.fail_on_block and decision.get("outcome") == "block" else 0


def cmd_setup_codex(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir or ".").resolve()
    profile = args.profile or "core"
    read_only_shell_write = args.read_only_shell_write or "warn"
    hooks_path = project_dir / ".codex" / "hooks.json"
    hook_cmd = f'"{sys.executable}" -m ai_workbench_mcp.supervisor.codex_hooks'
    hook_handler = {
        "type": "command",
        "command": hook_cmd,
        "commandWindows": hook_cmd,
        "timeout": 30,
        "statusMessage": "Capturing AI Workbench evidence",
    }
    hooks = {
        "hooks": {
            "SessionStart": [{
                "matcher": "startup|resume|clear|compact",
                "hooks": [dict(hook_handler, statusMessage="Starting AI Workbench evidence run")],
            }],
            "PreToolUse": [{
                "matcher": _codex_tool_matcher(profile),
                "hooks": [dict(hook_handler, statusMessage="Checking AI Workbench policy")],
            }],
            "PostToolUse": [{
                "matcher": _codex_tool_matcher(profile),
                "hooks": [dict(hook_handler, statusMessage="Capturing AI Workbench tool output")],
            }],
            "Stop": [{
                "hooks": [dict(hook_handler, statusMessage="Finalizing AI Workbench evidence")],
            }],
        }
    }

    if args.dry_run:
        print(json.dumps({"hooks_path": str(hooks_path), "hooks": hooks}, indent=2))
        return 0

    hooks_path.parent.mkdir(parents=True, exist_ok=True)
    hooks_path.write_text(json.dumps(hooks, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    record = register_project(project_dir=str(project_dir), task_type=args.task_type or "audit")
    print("Codex AI Workbench hooks installed.")
    print(f"hooks={hooks_path}")
    print(f"state={get_state_path()}")
    print(f"project={record['project_dir']}")
    print(f"task_type={record['task_type']}")
    print(f"profile={profile}")
    print(f"read_only_shell_write={read_only_shell_write}")
    print("next_action=Restart Codex or start a new session, then open /hooks and trust this project hook once.")
    return 0


def cmd_supervisor(args: argparse.Namespace) -> int:
    action = args.supervisor_command
    if action in {"setup", "register"}:
        record = register_project(
            project_dir=args.project_dir,
            task_type=args.task_type or "audit",
            evidence_root=args.evidence_root,
            policy=args.policy or "",
        )
        write_daemon_log(
            "project-registered",
            project_dir=record["project_dir"],
            task_type=record["task_type"],
            evidence_root=record["evidence_root"],
        )
        print("Supervisor configured.")
        print(f"project={record['project_dir']}")
        print(f"task_type={record['task_type']}")
        print(f"runs_root={record['evidence_root']}")
        print(f"state={get_state_path()}")
        return 0

    if action == "unregister":
        removed = unregister_project(args.project_dir)
        print(f"unregistered={str(removed).lower()}")
        return 0

    if action == "list":
        print(json.dumps({"projects": list_projects()}, indent=2, ensure_ascii=False))
        return 0

    if action == "start":
        policy_dir = args.policy_dir or str(SUPERVISOR_POLICY_DIR)
        if args.foreground:
            daemon = SupervisorDaemon(
                policy_dir=policy_dir,
                poll_interval=args.interval,
                idle_seconds=args.idle_seconds,
                validation_timeout=args.validation_timeout,
            )
            daemon.run_foreground(recover=not args.no_recover)
            return 0
        pid = start_background(
            interval=args.interval,
            idle_seconds=args.idle_seconds,
            validation_timeout=args.validation_timeout,
            policy_dir=policy_dir,
            recover=not args.no_recover,
        )
        print(f"daemon_pid={pid}")
        return 0

    if action == "stop":
        path = request_stop()
        print(f"stop_requested={path}")
        return 0

    if action == "status":
        rows = status_rows()
        if args.json:
            print(json.dumps({"projects": rows}, indent=2, ensure_ascii=False))
            return 0
        if not rows:
            print("No supervised projects registered.")
            return 0
        for row in rows:
            print(f"{row['state']:24} {row['project_dir']}")
            print(f"  coverage: {row.get('coverage') or '-'}")
            print(f"  run:      {row.get('latest_run_path') or '-'}")
            print(f"  next:     {row.get('required_next_action') or '-'}")
        return 0

    if action == "logs":
        entries = read_daemon_logs(tail=args.tail, json_output=args.json)
        if args.json:
            print(json.dumps(entries, indent=2, ensure_ascii=False))
        else:
            for line in entries:
                print(line)
        return 0

    if action == "install-startup":
        result = install_windows_startup(force=args.force, dry_run=args.dry_run)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    if action == "startup-status":
        result = startup_status()
        print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else f"startup_status={result['status']}")
        return 0

    if action == "uninstall-startup":
        result = uninstall_windows_startup()
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    print("Missing supervisor subcommand.")
    return 1


def cmd_reports(args: argparse.Namespace) -> int:
    if args.reports_command == "list":
        rows, warnings = collect_reports(project_dir=args.project_dir, status=args.status, limit=args.limit)
        if args.json:
            print(json.dumps({"reports": rows, "warnings": warnings}, indent=2, ensure_ascii=False))
            return 0
        if not rows:
            print("No AI Workbench reports found.")
        for row in rows:
            print(f"{row['state']:24} {row['run_id']}")
            print(f"  project: {row['project_dir']}")
            print(f"  run: {row['run_path']}")
            print(f"  next: {row['required_next_action'] or '-'}")
        return 0

    if args.reports_command == "show":
        resolved = resolve_report_ref(args.ref, project_dir=args.project_dir)
        metadata = resolved.get("metadata") or {}
        run_path = Path(resolved["run_path"])
        path = Path(resolved.get("path") or run_path)
        if args.json:
            payload: dict[str, object] = {
                "schema": "ai-workbench.report-show.v1",
                "run_path": str(run_path),
                "metadata": metadata,
            }
            for key, file_name in (
                ("validation_report", "validation_report.json"),
                ("revision_decision", "revision_decision.json"),
            ):
                artifact_path = run_path / file_name
                if artifact_path.is_file():
                    payload[key] = json.loads(artifact_path.read_text(encoding="utf-8"))
                else:
                    payload[key] = None
            print(json.dumps(payload, indent=2, ensure_ascii=False))
            return 0
        if args.markdown:
            md_path = run_path / "model_output.md"
            if not md_path.is_file():
                md_path = Path(metadata.get("acceptance_report_md") or path)
            if md_path.suffix.lower() != ".md":
                print(f"No markdown report recorded for: {resolved['run_path']}")
                return 1
            print(md_path.read_text(encoding="utf-8", errors="replace"))
            return 0
        print(f"Run:      {resolved['run_path']}")
        print(f"Report:   {path}")
        print(f"State:    {metadata.get('state') or metadata.get('decision') or metadata.get('status') or '-'}")
        print(f"Decision: {metadata.get('decision') or '-'}")
        print(f"Next:     {metadata.get('required_next_action') or '-'}")
        return 0

    if args.reports_command == "open":
        target = open_report_ref(args.ref, project_dir=args.project_dir)
        print(f"opened={target}")
        return 0

    print("Missing reports subcommand.")
    return 1


def cmd_opencode_watch(args: argparse.Namespace) -> int:
    record = register_project(
        project_dir=args.project_dir or ".",
        task_type=args.task_type or "audit",
    )
    if args.auto_terminate:
        print("auto_terminate=unsupported")
        print("next_action=Use ai-workbench supervisor policy findings to review risky OpenCode activity.")
    print("OpenCode project registered for canonical supervisor capture.")
    print(f"project={record['project_dir']}")
    print(f"runs_root={record['evidence_root']}")
    print("Press Ctrl+C to stop and finalize active runs.")
    daemon = SupervisorDaemon(
        policy_dir=str(SUPERVISOR_POLICY_DIR),
        poll_interval=args.interval,
        idle_seconds=args.idle_seconds,
    )
    daemon.run_foreground()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-workbench", description="AI Workbench acceptance and supervision CLI")
    subparsers = parser.add_subparsers(dest="command")

    p_mcp = subparsers.add_parser("mcp", help="Run MCP server commands")
    mcp_subs = p_mcp.add_subparsers(dest="mcp_command")
    p_mcp_serve = mcp_subs.add_parser("serve", help="Serve AI Workbench MCP over stdio")
    p_mcp_serve.set_defaults(func=cmd_mcp_serve)

    p_bootstrap = subparsers.add_parser("bootstrap", help="Bootstrap AI Workbench assets into a repository")
    p_bootstrap.add_argument("--target", default=".")
    p_bootstrap.add_argument("--force", action="store_true")
    p_bootstrap.add_argument("--dry-run", action="store_true")
    p_bootstrap.add_argument("--json", action="store_true")
    p_bootstrap.set_defaults(func=cmd_bootstrap)

    p_demo = subparsers.add_parser("demo", help="Run the package demo")
    p_demo.add_argument("--target", default="./workbench-first-run")
    p_demo.add_argument("--json", action="store_true")
    p_demo.set_defaults(func=cmd_demo)

    p_validate = subparsers.add_parser("validate", help="Write validation_report.json for a run")
    p_validate.add_argument("--project", required=True)
    p_validate.add_argument("--profile")
    p_validate.add_argument("--run-dir", required=True)
    p_validate.add_argument("--report-name", default="validation_report.json")
    p_validate.add_argument("--changed-file", action="append")
    p_validate.add_argument("--task-test-command")
    p_validate.set_defaults(func=cmd_validate)

    p_gate = subparsers.add_parser("gate", help="Write revision_decision.json for a run")
    p_gate.add_argument("--project", required=True)
    p_gate.add_argument("--run-dir", required=True)
    p_gate.add_argument("--mode", default="auto")
    p_gate.add_argument("--risk", choices=["low", "medium", "high"])
    p_gate.add_argument("--validation-report")
    p_gate.add_argument("--review-prompt")
    p_gate.add_argument("--review-output")
    p_gate.set_defaults(func=cmd_gate)

    p_pr = subparsers.add_parser("pr-gate", help="Render PR-ready acceptance artifacts")
    p_pr.add_argument("--run-dir")
    p_pr.add_argument("--runs-dir")
    p_pr.add_argument("--run-id")
    p_pr.add_argument("--fallback-run-dir")
    p_pr.add_argument("--out", default="runs/pr_gate/pr_comment.md")
    p_pr.add_argument("--json-out", default="runs/pr_gate/pr_decision.json")
    p_pr.add_argument("--fail-on-block", action="store_true")
    p_pr.set_defaults(func=cmd_pr_gate)

    p_supervisor = subparsers.add_parser("supervisor", help="Manage automated evidence supervision")
    sup_subs = p_supervisor.add_subparsers(dest="supervisor_command")
    for name in ("setup", "register"):
        p = sup_subs.add_parser(name, help="Register a project for supervisor capture")
        p.add_argument("--project-dir", required=True)
        p.add_argument("--task-type", default="audit")
        p.add_argument("--evidence-root")
        p.add_argument("--policy")
        p.set_defaults(func=cmd_supervisor)
    p = sup_subs.add_parser("unregister", help="Unregister a supervised project")
    p.add_argument("--project-dir", required=True)
    p.set_defaults(func=cmd_supervisor)
    sup_subs.add_parser("list", help="List supervised projects").set_defaults(func=cmd_supervisor)
    p = sup_subs.add_parser("start", help="Start the supervisor daemon")
    p.add_argument("--foreground", action="store_true")
    p.add_argument("--interval", type=float, default=2.0)
    p.add_argument("--idle-seconds", type=float, default=300.0)
    p.add_argument("--validation-timeout", type=int, default=120)
    p.add_argument("--policy-dir")
    p.add_argument("--no-recover", action="store_true")
    p.set_defaults(func=cmd_supervisor)
    sup_subs.add_parser("stop", help="Request daemon stop").set_defaults(func=cmd_supervisor)
    p = sup_subs.add_parser("status", help="Show supervisor status")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_supervisor)
    p = sup_subs.add_parser("logs", help="Show supervisor logs")
    p.add_argument("--tail", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_supervisor)
    p = sup_subs.add_parser("install-startup", help="Install Windows login startup")
    p.add_argument("--force", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_supervisor)
    p = sup_subs.add_parser("startup-status", help="Show Windows startup status")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_supervisor)
    sup_subs.add_parser("uninstall-startup", help="Remove Windows startup command").set_defaults(func=cmd_supervisor)

    p_setup = subparsers.add_parser("setup", help="Install lifecycle integrations")
    setup_subs = p_setup.add_subparsers(dest="setup_command")
    p_codex = setup_subs.add_parser("codex", help="Install Codex lifecycle hooks")
    p_codex.add_argument("--project-dir", default=".")
    p_codex.add_argument("--task-type", default="audit")
    p_codex.add_argument("--profile", choices=["core", "all"], default="core")
    p_codex.add_argument("--read-only-shell-write", choices=["warn", "block"], default="warn")
    p_codex.add_argument("--dry-run", action="store_true")
    p_codex.set_defaults(func=cmd_setup_codex)

    p_reports = subparsers.add_parser("reports", help="Browse AI Workbench supervisor reports")
    reports_subs = p_reports.add_subparsers(dest="reports_command")
    p = reports_subs.add_parser("list", help="List reports")
    p.add_argument("--project-dir")
    p.add_argument("--status")
    p.add_argument("--limit", type=int, default=50)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_reports)
    p = reports_subs.add_parser("show", help="Show a report")
    p.add_argument("ref")
    p.add_argument("--project-dir")
    p.add_argument("--json", action="store_true")
    p.add_argument("--markdown", action="store_true")
    p.set_defaults(func=cmd_reports)
    p = reports_subs.add_parser("open", help="Open a report or run folder")
    p.add_argument("ref")
    p.add_argument("--project-dir")
    p.set_defaults(func=cmd_reports)

    p_opencode = subparsers.add_parser("opencode", help="OpenCode integrations")
    opencode_subs = p_opencode.add_subparsers(dest="opencode_command")
    p_watch = opencode_subs.add_parser("watch", help="Watch OpenCode Desktop SQLite events")
    p_watch.add_argument("--project-dir", default=".")
    p_watch.add_argument("--task-type", default="audit")
    p_watch.add_argument("--interval", type=float, default=2.0)
    p_watch.add_argument("--idle-seconds", type=float, default=300.0)
    p_watch.add_argument("--auto-terminate", action="store_true")
    p_watch.set_defaults(func=cmd_opencode_watch)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 0
    return int(func(args))


if __name__ == "__main__":
    raise SystemExit(main())
