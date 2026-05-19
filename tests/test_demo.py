import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from ai_workbench_mcp.tools.demo import DEMO_NOTICE, DEMO_ROOT_NAME, generate_demo, main


EXPECTED_OUTCOMES = {
    "accepted": "accept",
    "needs-review": "needs_review",
    "blocked": "block",
}


class PackageDemoTests(unittest.TestCase):
    def test_generate_demo_writes_three_pr_gate_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)

            results = generate_demo(target)

            self.assertEqual([result.scenario for result in results], list(EXPECTED_OUTCOMES))
            demo_root = target / DEMO_ROOT_NAME
            self.assertTrue(demo_root.is_dir())

            for result in results:
                with self.subTest(scenario=result.scenario):
                    expected_outcome = EXPECTED_OUTCOMES[result.scenario]
                    scenario_dir = demo_root / result.scenario
                    evidence_dir = scenario_dir / "evidence"
                    comment_path = scenario_dir / "pr_comment.md"
                    decision_path = scenario_dir / "pr_decision.json"

                    self.assertEqual(result.outcome, expected_outcome)
                    self.assertEqual(result.evidence_dir, evidence_dir)
                    self.assertEqual(result.comment_path, comment_path)
                    self.assertEqual(result.decision_path, decision_path)

                    for file_name in (
                        "task_metadata.json",
                        "validation_report.json",
                        "revision_decision.json",
                        "model_output.md",
                        "run_log.jsonl",
                    ):
                        self.assertTrue((evidence_dir / file_name).is_file())
                    self.assertTrue(comment_path.is_file())
                    self.assertTrue(decision_path.is_file())

                    decision = json.loads(decision_path.read_text(encoding="utf-8"))
                    comment = comment_path.read_text(encoding="utf-8")
                    task_metadata = json.loads((evidence_dir / "task_metadata.json").read_text(encoding="utf-8"))
                    validation_report = json.loads((evidence_dir / "validation_report.json").read_text(encoding="utf-8"))
                    revision_decision = json.loads(
                        (evidence_dir / "revision_decision.json").read_text(encoding="utf-8")
                    )

                    self.assertEqual(decision["operation"], "workbench_pr_gate")
                    self.assertEqual(decision["outcome"], expected_outcome)
                    self.assertEqual(decision["evidence_source"], "acceptance_run")
                    self.assertEqual(decision["source_run_dir"], f"{DEMO_ROOT_NAME}/{result.scenario}/evidence")
                    self.assertIn("Evidence present: validation_report yes, revision_decision yes", comment)
                    self.assertIn("## Evidence", comment)
                    self.assertNotIn(str(target), json.dumps(decision, sort_keys=True))
                    self.assertNotIn(str(target), comment)

                    self.assertTrue(task_metadata["demo_fixture"])
                    self.assertTrue(validation_report["demo_fixture"])
                    self.assertTrue(revision_decision["demo_fixture"])
                    self.assertEqual(task_metadata["execution_host"], "other")
                    self.assertEqual(task_metadata["policy_pack_selection_mode"], "demo_fixture")
                    self.assertIn(DEMO_NOTICE, task_metadata["demo_notice"])
                    self.assertIn(DEMO_NOTICE, validation_report["demo_notice"])
                    self.assertIn(DEMO_NOTICE, revision_decision["demo_notice"])

    def test_main_prints_concise_absolute_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            stdout = io.StringIO()

            with contextlib.redirect_stdout(stdout):
                exit_code = main(["--target", str(target)])

            self.assertEqual(exit_code, 0)
            output = stdout.getvalue()
            demo_root = target / DEMO_ROOT_NAME
            self.assertIn(f"ai_workbench_demo_root={demo_root}", output)
            for scenario, outcome in EXPECTED_OUTCOMES.items():
                scenario_dir = demo_root / scenario
                self.assertIn(f"scenario={scenario} outcome={outcome}", output)
                self.assertIn(f"evidence_dir={scenario_dir / 'evidence'}", output)
                self.assertIn(f"pr_gate_comment={scenario_dir / 'pr_comment.md'}", output)
                self.assertIn(f"pr_gate_decision={scenario_dir / 'pr_decision.json'}", output)

    def test_generate_demo_is_idempotent_for_known_demo_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)

            first_results = generate_demo(target)
            second_results = generate_demo(target)

            self.assertEqual(
                [(result.scenario, result.outcome) for result in first_results],
                [(result.scenario, result.outcome) for result in second_results],
            )
            for result in second_results:
                decision = json.loads(result.decision_path.read_text(encoding="utf-8"))
                self.assertEqual(decision["outcome"], EXPECTED_OUTCOMES[result.scenario])


if __name__ == "__main__":
    unittest.main()
