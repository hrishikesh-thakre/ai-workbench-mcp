import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai_workbench_mcp.cli import SUPERVISOR_POLICY_DIR
from ai_workbench_mcp.supervisor.daemon import SupervisorDaemon, status_rows
from ai_workbench_mcp.supervisor.daemon_state import make_project_record, normalize_project_path, save_state
from ai_workbench_mcp.supervisor.evidence_builder import EvidenceRunBuilder
from ai_workbench_mcp.supervisor.report_browser import collect_reports, resolve_report_ref
from ai_workbench_mcp.tools.pr_gate import pr_gate_payload


CANONICAL_WORKBENCH_ARTIFACTS = {
    "task_metadata.json",
    "final_prompt.md",
    "model_selection.json",
    "model_output.md",
    "run_log.jsonl",
    "validation_report.json",
    "revision_decision.json",
}


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def init_repo(root: Path) -> None:
    root.mkdir()
    source_dir = root / "source_files"
    source_dir.mkdir()
    (source_dir / "example_module.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "ci@example.com"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "CI"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=root, check=True, capture_output=True)


def add_python_test_fixture(root: Path, expected_value: int) -> None:
    (root / "pyproject.toml").write_text("[project]\nname = \"fixture\"\nversion = \"0.0.1\"\n", encoding="utf-8")
    tests_dir = root / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_example.py").write_text(
        "from source_files.example_module import value\n\n"
        "def test_value():\n"
        f"    assert value() == {expected_value}\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "add test fixture"], cwd=root, check=True, capture_output=True)


def pr_gate_for(run_path: Path, project_root: Path) -> dict[str, object]:
    return pr_gate_payload(
        SimpleNamespace(
            run_dir=str(run_path),
            runs_dir="",
            run_id="",
            fallback_run_dir="",
            out=str(project_root / "runs" / "pr_gate" / "pr_comment.md"),
            json_out=str(project_root / "runs" / "pr_gate" / "pr_decision.json"),
            fail_on_block=False,
        )
    )


def finalize_supervised_run(
    root: Path,
    *,
    task_type: str = "audit",
    run_validation_step: bool = False,
    late_snapshot: bool = False,
) -> Path:
    builder = EvidenceRunBuilder.create(
        str(root),
        str(root / "runs"),
        task_type,
        "codex",
        "session1",
        late_snapshot=late_snapshot,
    )
    status_output = "(clean)" if task_type == "audit" else " M source_files/example_module.py"
    builder.append_event(
        {
            "tool_name": "shell",
            "command": "git status --short",
            "content": status_output,
            "session_id": "session1",
        }
    )
    metadata = builder.finalize(str(SUPERVISOR_POLICY_DIR), run_validation_step=run_validation_step)
    return Path(str(metadata["acceptance_report_json"])).parent


class SupervisorWorkbenchContractTests(unittest.TestCase):
    def test_supervised_audit_writes_complete_workbench_artifacts_and_accepts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "repo"
            init_repo(root)

            run_path = finalize_supervised_run(root)
            decision = pr_gate_for(run_path, root)

            self.assertEqual(decision["outcome"], "accept")
            for artifact in CANONICAL_WORKBENCH_ARTIFACTS:
                with self.subTest(artifact=artifact):
                    self.assertTrue((run_path / artifact).is_file())

            validation = json.loads((run_path / "validation_report.json").read_text(encoding="utf-8"))
            revision = json.loads((run_path / "revision_decision.json").read_text(encoding="utf-8"))
            metadata = json.loads((run_path / "metadata.json").read_text(encoding="utf-8"))
            latest = json.loads((root / "runs" / "latest.json").read_text(encoding="utf-8"))
            self.assertEqual(validation["overall_status"], "passed")
            self.assertTrue(validation["sign_off_ready"])
            self.assertEqual(revision["final_status"], "accepted")
            self.assertEqual(metadata["status"], "accept")
            self.assertEqual(metadata["decision"], "accept")
            self.assertEqual(metadata["supporting_acceptance_decision"], "ACCEPT")
            self.assertEqual(latest["status"], "accept")
            rows, warnings = collect_reports(project_dir=str(root), status="accept")
            self.assertEqual(warnings, [])
            self.assertEqual(rows[0]["state"], "accept")
            self.assertEqual(rows[0]["supporting_acceptance_decision"], "ACCEPT")
            self.assertTrue(rows[0]["validation_report_json"].endswith("validation_report.json"))
            self.assertTrue(rows[0]["revision_decision_json"].endswith("revision_decision.json"))
            resolved = resolve_report_ref("latest", project_dir=str(root))
            self.assertTrue(str(resolved["path"]).endswith("revision_decision.json"))

            env = os.environ.copy()
            src_path = str(Path(__file__).resolve().parents[1] / "src")
            env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
            show = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ai_workbench_mcp.cli",
                    "reports",
                    "show",
                    "latest",
                    "--project-dir",
                    str(root),
                    "--json",
                ],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )
            self.assertEqual(show.returncode, 0, show.stderr)
            show_payload = json.loads(show.stdout)
            self.assertEqual(show_payload["validation_report"]["overall_status"], "passed")
            self.assertEqual(show_payload["revision_decision"]["final_status"], "accepted")

    def test_supervisor_status_preserves_final_workbench_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "repo"
            init_repo(root)
            run_path = finalize_supervised_run(root)
            state_path = Path(tmpdir) / "state.json"
            record = make_project_record(str(root))
            record.update({
                "latest_decision": "accept",
                "latest_run_path": str(run_path),
                "latest_next_action": "none",
            })
            save_state(
                {
                    "version": 1,
                    "daemon": {},
                    "projects": {normalize_project_path(str(root)): record},
                },
                state_path,
            )

            rows = status_rows(state_path=state_path, opencode_db=str(Path(tmpdir) / "missing-opencode.db"))

            self.assertEqual(rows[0]["state"], "accept")
            self.assertEqual(rows[0]["decision"], "accept")

    def test_report_browser_uses_canonical_artifacts_over_stale_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "repo"
            run_path = root / "runs" / "stale-accept"
            write_json(
                run_path / "metadata.json",
                {
                    "run_id": "stale-accept",
                    "project_dir": str(root),
                    "status": "accept",
                    "decision": "accept",
                    "finalized_at": "2026-06-27T00:00:00Z",
                    "required_next_action": "none",
                },
            )
            write_json(
                run_path / "validation_report.json",
                {
                    "run_id": "stale-accept",
                    "overall_status": "failed",
                    "sign_off_ready": False,
                    "reason_sources": [
                        {
                            "code": "validation.failed",
                            "severity": "blocker",
                            "summary": "Canonical validation failed.",
                        }
                    ],
                },
            )
            write_json(
                run_path / "revision_decision.json",
                {
                    "run_id": "stale-accept",
                    "final_status": "revision_required",
                    "reason": "Fix deterministic validation.",
                    "next_action": "Fix deterministic validation.",
                },
            )

            accepted_rows, accepted_warnings = collect_reports(project_dir=str(root), status="accept")
            blocked_rows, blocked_warnings = collect_reports(project_dir=str(root), status="block")
            resolved = resolve_report_ref("latest", project_dir=str(root))

            self.assertEqual(accepted_warnings, [])
            self.assertEqual(blocked_warnings, [])
            self.assertEqual(accepted_rows, [])
            self.assertEqual(len(blocked_rows), 1)
            self.assertEqual(blocked_rows[0]["state"], "block")
            self.assertEqual(blocked_rows[0]["decision"], "block")
            self.assertEqual(blocked_rows[0]["validation_status"], "failed")
            self.assertEqual(blocked_rows[0]["quality_gate_status"], "revision_required")
            self.assertTrue(blocked_rows[0]["canonical_evidence_evaluated"])
            self.assertEqual(resolved["metadata"]["state"], "block")
            self.assertEqual(resolved["metadata"]["decision"], "block")

    def test_supervisor_status_uses_canonical_artifacts_over_stale_latest_decision(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "repo"
            run_path = root / "runs" / "stale-status"
            write_json(
                run_path / "metadata.json",
                {
                    "run_id": "stale-status",
                    "project_dir": str(root),
                    "status": "accept",
                    "decision": "accept",
                    "finalized_at": "2026-06-27T00:00:00Z",
                    "required_next_action": "none",
                },
            )
            write_json(
                run_path / "validation_report.json",
                {
                    "run_id": "stale-status",
                    "overall_status": "failed",
                    "sign_off_ready": False,
                    "reason_sources": [
                        {
                            "code": "validation.failed",
                            "severity": "blocker",
                            "summary": "Canonical validation failed.",
                        }
                    ],
                },
            )
            write_json(
                run_path / "revision_decision.json",
                {
                    "run_id": "stale-status",
                    "final_status": "revision_required",
                    "reason": "Fix deterministic validation.",
                    "next_action": "Fix deterministic validation.",
                },
            )
            state_path = Path(tmpdir) / "state.json"
            record = make_project_record(str(root))
            record.update({
                "latest_decision": "accept",
                "latest_run_path": str(run_path),
                "latest_next_action": "none",
            })
            save_state(
                {
                    "version": 1,
                    "daemon": {},
                    "projects": {normalize_project_path(str(root)): record},
                },
                state_path,
            )

            rows = status_rows(state_path=state_path, opencode_db=str(Path(tmpdir) / "missing-opencode.db"))

            self.assertEqual(rows[0]["state"], "block")
            self.assertEqual(rows[0]["decision"], "block")
            self.assertEqual(rows[0]["required_next_action"], "Fix deterministic validation.")

    def test_daemon_rebuilds_legacy_finalized_run_without_canonical_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "repo"
            init_repo(root)
            builder = EvidenceRunBuilder.create(
                str(root),
                str(root / "runs"),
                "audit",
                "codex",
                "legacy-session",
            )
            supporting_report = builder.run_path / "acceptance_report_supporting.json"
            write_json(supporting_report, {"decision": "ACCEPT"})
            metadata = json.loads((builder.run_path / "metadata.json").read_text(encoding="utf-8"))
            metadata.update(
                {
                    "status": "accept",
                    "decision": "accept",
                    "finalized_at": "2026-06-27T00:00:00Z",
                    "required_next_action": "none",
                    "acceptance_report_json": str(supporting_report),
                }
            )
            write_json(builder.run_path / "metadata.json", metadata)
            self.assertFalse((builder.run_path / "validation_report.json").exists())
            self.assertFalse((builder.run_path / "revision_decision.json").exists())

            state_path = Path(tmpdir) / "state.json"
            project_key = normalize_project_path(str(root))
            record = make_project_record(str(root))
            record.update(
                {
                    "current_run_id": builder.run_id,
                    "current_run_path": str(builder.run_path),
                    "current_agent": builder.agent,
                    "current_session_id": builder.session_id,
                    "latest_run_path": str(builder.run_path),
                }
            )
            save_state({"version": 1, "daemon": {}, "projects": {project_key: record}}, state_path)
            daemon = SupervisorDaemon(
                policy_dir=str(SUPERVISOR_POLICY_DIR),
                state_path=state_path,
                opencode_db=str(Path(tmpdir) / "missing-opencode.db"),
            )

            daemon._finalize_project(project_key, reason="legacy-rebuild-test")

            self.assertTrue((builder.run_path / "validation_report.json").is_file())
            self.assertTrue((builder.run_path / "revision_decision.json").is_file())

    def test_supervised_code_change_with_no_validation_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "repo"
            init_repo(root)
            (root / "source_files" / "example_module.py").write_text("def value():\n    return 2\n", encoding="utf-8")

            run_path = finalize_supervised_run(root, task_type="code_change", run_validation_step=False)
            decision = pr_gate_for(run_path, root)

            self.assertEqual(decision["outcome"], "block")
            validation = json.loads((run_path / "validation_report.json").read_text(encoding="utf-8"))
            revision = json.loads((run_path / "revision_decision.json").read_text(encoding="utf-8"))
            metadata = json.loads((run_path / "metadata.json").read_text(encoding="utf-8"))
            self.assertEqual(validation["overall_status"], "failed")
            self.assertEqual(revision["final_status"], "revision_required")
            self.assertEqual(metadata["status"], "block")
            self.assertIn("validation evidence", metadata["required_next_action"])
            self.assertIn("supervisor.validation_blocked", validation["reason_codes"])
            test_output = (run_path / "validation" / "test_output.txt").read_text(encoding="utf-8")
            self.assertIn("AI_WORKBENCH_VALIDATION_MISSING", test_output)

    def test_supervised_code_change_with_passing_validation_accepts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "repo"
            init_repo(root)
            add_python_test_fixture(root, expected_value=2)
            (root / "source_files" / "example_module.py").write_text("def value():\n    return 2\n", encoding="utf-8")

            run_path = finalize_supervised_run(root, task_type="code_change", run_validation_step=True)
            decision = pr_gate_for(run_path, root)

            self.assertEqual(decision["outcome"], "accept")
            validation = json.loads((run_path / "validation_report.json").read_text(encoding="utf-8"))
            revision = json.loads((run_path / "revision_decision.json").read_text(encoding="utf-8"))
            self.assertEqual(validation["overall_status"], "passed")
            self.assertEqual(revision["final_status"], "accepted")

    def test_late_snapshot_never_silently_accepts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir) / "repo"
            init_repo(root)

            run_path = finalize_supervised_run(root, late_snapshot=True)
            decision = pr_gate_for(run_path, root)

            self.assertIn(decision["outcome"], {"needs_review", "block"})
            self.assertNotEqual(decision["outcome"], "accept")
            validation = json.loads((run_path / "validation_report.json").read_text(encoding="utf-8"))
            metadata = json.loads((run_path / "metadata.json").read_text(encoding="utf-8"))
            self.assertIn("supervisor.late_snapshot", validation["reason_codes"])
            self.assertIn(metadata["status"], {"needs_review", "block"})
            self.assertNotEqual(metadata["status"], "accept")


class UnifiedCliSmokeTests(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        src_path = str(Path(__file__).resolve().parents[1] / "src")
        env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
        return subprocess.run(
            [sys.executable, "-m", "ai_workbench_mcp.cli", *args],
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )

    def test_unified_cli_public_smoke(self) -> None:
        for args in (
            ("--help",),
            ("mcp", "serve", "--help"),
            ("supervisor", "status", "--json"),
            ("setup", "codex", "--project-dir", ".", "--dry-run"),
        ):
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
