import json
import os
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def source_env() -> dict[str, str]:
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src_path if not current else f"{src_path}{os.pathsep}{current}"
    return env


def run_python(args: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        env=source_env(),
        capture_output=True,
        text=True,
        check=False,
    )


class CliReleaseSmokeTests(unittest.TestCase):
    def test_package_module_demo_renders_all_pr_gate_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_python(["-m", "ai_workbench_mcp.tools.demo", "--target", tmpdir])

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("scenario=accepted outcome=accept", result.stdout)
            self.assertIn("scenario=needs-review outcome=needs_review", result.stdout)
            self.assertIn("scenario=blocked outcome=block", result.stdout)

            demo_root = Path(tmpdir) / "ai-workbench-demo"
            expected = {
                "accepted": "accept",
                "needs-review": "needs_review",
                "blocked": "block",
            }
            for folder, outcome in expected.items():
                with self.subTest(folder=folder):
                    decision_path = demo_root / folder / "pr_decision.json"
                    comment_path = demo_root / folder / "pr_comment.md"
                    evidence_dir = demo_root / folder / "evidence"
                    decision = json.loads(decision_path.read_text(encoding="utf-8"))

                    self.assertEqual(decision["outcome"], outcome)
                    self.assertEqual(decision["evidence_source"], "acceptance_run")
                    self.assertTrue(comment_path.is_file())
                    self.assertTrue((evidence_dir / "validation_report.json").is_file())
                    self.assertTrue((evidence_dir / "revision_decision.json").is_file())
                    self.assertTrue((evidence_dir / "run_log.jsonl").is_file())

    def test_root_cli_wrappers_and_package_modules_keep_same_help_surface(self) -> None:
        command_flags = {
            "bootstrap_assets": ("--target-dir", "--groups", "--dry-run"),
            "model_select": ("--project", "--task-type", "--out"),
            "validate_run": ("--project", "--profile", "--out-dir"),
            "quality_loop": ("--project", "--run-dir", "--mode"),
            "run_analyze": ("--runs-dir", "--out-dir", "--evidence-scope"),
            "pr_gate": ("--run-dir", "--fallback-run-dir", "--json-out"),
        }

        for tool_name, flags in command_flags.items():
            with self.subTest(tool=tool_name):
                wrapper = run_python([str(ROOT / "tools" / f"{tool_name}.py"), "--help"])
                module = run_python(["-m", f"ai_workbench_mcp.tools.{tool_name}", "--help"])

                self.assertEqual(wrapper.returncode, 0, wrapper.stderr)
                self.assertEqual(module.returncode, 0, module.stderr)
                self.assertIn("usage:", wrapper.stdout)
                self.assertIn("usage:", module.stdout)
                for flag in flags:
                    self.assertIn(flag, wrapper.stdout)
                    self.assertIn(flag, module.stdout)

    def test_root_pr_gate_wrapper_matches_packaged_module_decision_shape(self) -> None:
        evidence_dir = ROOT / "examples" / "pr-gate-outcomes" / "accepted" / "evidence"
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            wrapper_decision = tmp / "wrapper" / "pr_decision.json"
            module_decision = tmp / "module" / "pr_decision.json"
            wrapper_comment = tmp / "wrapper" / "pr_comment.md"
            module_comment = tmp / "module" / "pr_comment.md"

            wrapper = run_python(
                [
                    str(ROOT / "tools" / "pr_gate.py"),
                    "--run-dir",
                    str(evidence_dir),
                    "--out",
                    str(wrapper_comment),
                    "--json-out",
                    str(wrapper_decision),
                ]
            )
            module = run_python(
                [
                    "-m",
                    "ai_workbench_mcp.tools.pr_gate",
                    "--run-dir",
                    str(evidence_dir),
                    "--out",
                    str(module_comment),
                    "--json-out",
                    str(module_decision),
                ]
            )

            self.assertEqual(wrapper.returncode, 0, wrapper.stderr)
            self.assertEqual(module.returncode, 0, module.stderr)
            wrapper_payload = json.loads(wrapper_decision.read_text(encoding="utf-8"))
            module_payload = json.loads(module_decision.read_text(encoding="utf-8"))

            for field in (
                "schema_version",
                "operation",
                "outcome",
                "evidence_source",
                "validation_status",
                "quality_gate_status",
                "reason_codes",
            ):
                with self.subTest(field=field):
                    self.assertEqual(wrapper_payload[field], module_payload[field])
            self.assertEqual(wrapper_payload["outcome"], "accept")

    def test_root_validate_run_wrapper_executes_scaffold_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir) / "wrapper-scaffold"

            result = run_python(
                [
                    str(ROOT / "tools" / "validate_run.py"),
                    "--project",
                    "ai_workbench_mcp",
                    "--profile",
                    "scaffold",
                    "--out-dir",
                    str(run_dir),
                ]
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("overall_status=passed", result.stdout)

            report = json.loads((run_dir / "validation_report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["overall_status"], "passed")
            self.assertTrue(report["sign_off_ready"])
            self.assertGreater(report["summary"]["commands_passed"], 0)
            self.assertIn(
                "validate_run_help",
                {str(command.get("name")) for command in report["commands_run"]},
            )

    def test_root_tool_shims_stay_thin_compatibility_wrappers(self) -> None:
        executable_shims = {
            "bootstrap_assets": "ai_workbench_mcp.tools.bootstrap_assets",
            "context_scout": "ai_workbench_mcp.tools.context_scout",
            "golden_eval": "ai_workbench_mcp.tools.golden_eval",
            "model_handoff": "ai_workbench_mcp.tools.model_handoff",
            "model_select": "ai_workbench_mcp.tools.model_select",
            "policy_pack_select": "ai_workbench_mcp.tools.policy_pack_select",
            "pr_gate_comment": "ai_workbench_mcp.tools.pr_gate_comment",
            "pr_gate": "ai_workbench_mcp.tools.pr_gate",
            "quality_loop": "ai_workbench_mcp.tools.quality_loop",
            "run_analyze": "ai_workbench_mcp.tools.run_analyze",
            "run_log": "ai_workbench_mcp.tools.run_log",
            "validate_run": "ai_workbench_mcp.tools.validate_run",
        }
        import_shims = {
            "config_loader": "ai_workbench_mcp.tools.config_loader",
            "response_format": "ai_workbench_mcp.tools.response_format",
        }

        for tool_name, module_name in executable_shims.items():
            with self.subTest(tool=tool_name):
                text = (ROOT / "tools" / f"{tool_name}.py").read_text(encoding="utf-8")
                self.assertIn(f"from {module_name} import main", text)
                self.assertIn("raise SystemExit(main())", text)
                self.assertNotIn("argparse", text)

        for tool_name, module_name in import_shims.items():
            with self.subTest(tool=tool_name):
                text = (ROOT / "tools" / f"{tool_name}.py").read_text(encoding="utf-8")
                self.assertIn(f"from {module_name} import", text)
                self.assertIn("__all__", text)
                self.assertNotIn("argparse", text)

    def test_console_script_metadata_covers_package_first_surfaces(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        scripts = pyproject["project"]["scripts"]

        self.assertEqual(scripts["ai-workbench-mcp"], "ai_workbench_mcp.server:main")
        self.assertEqual(scripts["ai-workbench-bootstrap"], "ai_workbench_mcp.tools.bootstrap_assets:bootstrap_main")
        self.assertEqual(scripts["ai-workbench-bootstrap-assets"], "ai_workbench_mcp.tools.bootstrap_assets:main")
        self.assertEqual(scripts["ai-workbench-demo"], "ai_workbench_mcp.tools.demo:main")


if __name__ == "__main__":
    unittest.main()
