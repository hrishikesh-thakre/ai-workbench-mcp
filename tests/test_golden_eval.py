import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai_workbench_mcp.tools.run_analyze import run_analysis_payload


ROOT = Path(__file__).resolve().parents[1]
CASES_DIR = ROOT / "evals" / "golden_cases"
SAMPLE_RUNS_DIR = ROOT / "examples" / "sample-runs"
TINY_CASE = CASES_DIR / "accepted-tiny-python-fix.json"
DOCS_CASE = CASES_DIR / "accepted-docs-only-smoke.json"


def run_golden_eval(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "tools/golden_eval.py", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def copy_sample_run(tmp_path: Path, name: str = "accepted-tiny-python-fix") -> Path:
    source = SAMPLE_RUNS_DIR / name
    target = tmp_path / name
    shutil.copytree(source, target)
    return target


class GoldenEvalTests(unittest.TestCase):
    def test_scaffold_profile_includes_public_wrapper_help(self) -> None:
        profile_text = (ROOT / "configs" / "validation_profiles.yaml").read_text(encoding="utf-8")

        self.assertIn("golden_eval_module_help", profile_text)
        self.assertIn("python -m ai_workbench_mcp.tools.golden_eval --help", profile_text)
        self.assertNotIn("python tools/golden_eval.py --help", profile_text)

    def test_root_wrapper_help_works(self) -> None:
        result = run_golden_eval("--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("golden case", result.stdout.lower())
        self.assertIn("--cases-dir", result.stdout)

    def test_golden_case_files_exist_and_are_sanitized(self) -> None:
        cases = [TINY_CASE, DOCS_CASE]
        self.assertEqual(sorted(path.name for path in CASES_DIR.glob("*.json")), sorted(path.name for path in cases))

        for case_path in cases:
            with self.subTest(case=case_path.name):
                payload = read_json(case_path)
                combined = case_path.read_text(encoding="utf-8")
                self.assertEqual(payload["schema_version"], 1)
                self.assertIn("source_run_id", payload)
                self.assertIn("required_output_terms", payload)
                self.assertNotIn("needs-review-test-fix", combined)
                self.assertNotIn("D:\\", combined)
                self.assertNotIn("C:\\Users", combined)
                self.assertNotIn("api_key:", combined.lower())
                self.assertNotIn("token=", combined.lower())
                self.assertNotIn("model output\n\n", combined.lower())

    def test_batch_smoke_passes_and_writes_direct_child_reports(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            out_dir = tmp_path / "golden_eval_smoke"

            result = run_golden_eval(
                "--cases-dir",
                str(CASES_DIR),
                "--source-runs-dir",
                str(SAMPLE_RUNS_DIR),
                "--out-dir",
                str(out_dir),
            )

            reports = sorted(out_dir.glob("*/score_report.json"))
            metadata = sorted(out_dir.glob("*/model_eval_metadata.json"))
            report_payloads = [read_json(path) for path in reports]
            metrics = run_analysis_payload(
                SimpleNamespace(
                    runs_dir=str(out_dir),
                    task_type=None,
                    since=None,
                    out_dir=str(tmp_path / "analytics"),
                    evals_dir=str(CASES_DIR),
                )
            )

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("cases_total=2", result.stdout)
        self.assertIn("cases_passed=2", result.stdout)
        self.assertEqual([path.parent.name for path in reports], ["accepted-docs-only-smoke", "accepted-tiny-python-fix"])
        self.assertEqual([path.parent.name for path in metadata], ["accepted-docs-only-smoke", "accepted-tiny-python-fix"])
        self.assertTrue(all(report["passed"] is True for report in report_payloads))
        self.assertEqual(metrics["model_eval_runs_total"], 2)
        self.assertEqual(metrics["model_eval_runs_by_provider"], {"workbench": 2})
        self.assertEqual(metrics["model_eval_pass_rate_by_provider"]["workbench"]["pass_rate"], 1.0)
        self.assertEqual(metrics["golden_case_count"], 2)

    def test_single_case_smoke_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "accepted-tiny-python-fix"
            result = run_golden_eval(
                "--case",
                str(TINY_CASE),
                "--run-dir",
                str(SAMPLE_RUNS_DIR / "accepted-tiny-python-fix"),
                "--out-dir",
                str(out_dir),
            )
            report = read_json(out_dir / "score_report.json")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(report["passed"])
        self.assertEqual(report["overall_score"], 1.0)
        self.assertEqual(report["failure_modes"], [])

    def test_missing_source_run_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = run_golden_eval(
                "--case",
                str(TINY_CASE),
                "--source-runs-dir",
                str(Path(tmpdir) / "missing"),
                "--out-dir",
                str(Path(tmpdir) / "out"),
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing_source_run", result.stdout)

    def test_invalid_case_schema_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            invalid_case = tmp_path / "invalid.json"
            write_json(invalid_case, {"schema_version": 1})

            result = run_golden_eval(
                "--case",
                str(invalid_case),
                "--run-dir",
                str(SAMPLE_RUNS_DIR / "accepted-tiny-python-fix"),
                "--out-dir",
                str(tmp_path / "out"),
            )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid_case_schema", result.stdout)

    def test_valid_scoring_failure_writes_missing_artifact_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            run_dir = copy_sample_run(tmp_path)
            (run_dir / "final_prompt.md").unlink()
            out_dir = tmp_path / "out"

            result = run_golden_eval("--case", str(TINY_CASE), "--run-dir", str(run_dir), "--out-dir", str(out_dir))
            report = read_json(out_dir / "score_report.json")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(report["passed"])
        self.assertIn("missing_artifact:final_prompt.md", report["failure_modes"])

    def test_valid_scoring_failure_reports_metadata_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            run_dir = copy_sample_run(tmp_path)
            metadata = read_json(run_dir / "task_metadata.json")
            metadata["recipe"] = "workbench-docs-only-acceptance.yaml"
            write_json(run_dir / "task_metadata.json", metadata)
            out_dir = tmp_path / "out"

            result = run_golden_eval("--case", str(TINY_CASE), "--run-dir", str(run_dir), "--out-dir", str(out_dir))
            report = read_json(out_dir / "score_report.json")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(report["passed"])
        self.assertIn("metadata_mismatch:recipe", report["failure_modes"])

    def test_valid_scoring_failure_reports_output_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            run_dir = copy_sample_run(tmp_path)
            case_payload = read_json(TINY_CASE)
            case_payload["required_output_terms"] = ["missing short phrase"]
            case_payload["forbidden_output_terms"] = ["Changed `add()`"]
            case_path = tmp_path / "case.json"
            write_json(case_path, case_payload)
            out_dir = tmp_path / "out"

            result = run_golden_eval("--case", str(case_path), "--run-dir", str(run_dir), "--out-dir", str(out_dir))
            report = read_json(out_dir / "score_report.json")

        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(report["passed"])
        self.assertIn("missing_output_term:missing short phrase", report["failure_modes"])
        self.assertIn("forbidden_output_term:Changed `add()`", report["failure_modes"])


if __name__ == "__main__":
    unittest.main()
