import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai_workbench_mcp.tools.pr_gate import pr_gate_payload


ROOT = Path(__file__).resolve().parents[1]
ACCEPTED_SAMPLE = ROOT / "examples" / "sample-runs" / "accepted-tiny-python-fix"
NEEDS_REVIEW_SAMPLE = ROOT / "examples" / "sample-runs" / "needs-review-test-fix"


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def render_gate(run_dir: Path, out_dir: Path) -> tuple[dict[str, object], str]:
    comment_path = out_dir / "pr_comment.md"
    decision_path = out_dir / "pr_decision.json"
    decision = pr_gate_payload(
        SimpleNamespace(
            run_dir=str(run_dir),
            out=str(comment_path),
            json_out=str(decision_path),
        )
    )
    return decision, comment_path.read_text(encoding="utf-8")


class PrGateTests(unittest.TestCase):
    def test_accepted_sample_evidence_maps_to_accept(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            decision, comment = render_gate(ACCEPTED_SAMPLE, Path(tmpdir))

        self.assertEqual(decision["operation"], "workbench_pr_gate")
        self.assertEqual(decision["schema_version"], 1)
        self.assertEqual(decision["outcome"], "accept")
        self.assertTrue(decision["ok"])
        self.assertEqual(decision["validation_status"], "passed")
        self.assertEqual(decision["quality_gate_status"], "accepted")
        self.assertIn("# AI Workbench PR Gate: Accept", comment)
        self.assertIn("validation_report.json", comment)
        self.assertIn("revision_decision.json", comment)

    def test_missing_revision_decision_maps_to_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            run_dir = tmp_path / "run"
            shutil.copytree(ACCEPTED_SAMPLE, run_dir)
            (run_dir / "revision_decision.json").unlink()

            decision, comment = render_gate(run_dir, tmp_path / "out")

        self.assertEqual(decision["outcome"], "block")
        self.assertEqual(decision["quality_gate_status"], "unknown")
        self.assertIn("Missing required Workbench evidence: revision_decision.json.", decision["reason"])
        self.assertIn("# AI Workbench PR Gate: Block", comment)
        self.assertIn("| revision_decision | `revision_decision.json` | no |", comment)

    def test_failed_validation_or_revision_required_maps_to_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            decision, comment = render_gate(NEEDS_REVIEW_SAMPLE, Path(tmpdir))

        self.assertEqual(decision["outcome"], "block")
        self.assertEqual(decision["validation_status"], "failed")
        self.assertEqual(decision["quality_gate_status"], "revision_required")
        self.assertIn("Deterministic validation failed", decision["reason"])
        self.assertIn("# AI Workbench PR Gate: Block", comment)

    def test_review_required_without_blocker_reason_maps_to_needs_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            run_dir = tmp_path / "run"
            run_dir.mkdir()
            write_json(
                run_dir / "validation_report.json",
                {
                    "run_id": "review-run",
                    "overall_status": "needs_review",
                    "sign_off_ready": False,
                    "reason_codes": ["validation.needs_review"],
                    "reason_sources": [
                        {
                            "code": "validation.needs_review",
                            "severity": "review",
                            "summary": "Validation needs human review.",
                        }
                    ],
                },
            )
            write_json(
                run_dir / "revision_decision.json",
                {
                    "final_status": "review_required",
                    "reason": "Policy requires review.",
                    "next_action": "manual_review_handoff",
                    "reason_codes": ["quality.review_required"],
                    "reason_sources": [
                        {
                            "code": "quality.review_required",
                            "severity": "review",
                            "summary": "Quality gate requires review.",
                        }
                    ],
                },
            )
            (run_dir / "model_output.md").write_text("SECRET_RAW_MODEL_MARKER\n", encoding="utf-8")
            (run_dir / "run_log.jsonl").write_text("{}\n", encoding="utf-8")

            decision, comment = render_gate(run_dir, tmp_path / "out")

        self.assertEqual(decision["outcome"], "needs_review")
        self.assertEqual(decision["reason_codes"], ["validation.needs_review", "quality.review_required"])
        self.assertIn("# AI Workbench PR Gate: Needs Review", comment)
        self.assertIn("`validation.needs_review`", comment)
        self.assertIn("`quality.review_required`", comment)
        self.assertNotIn("SECRET_RAW_MODEL_MARKER", comment)

    def test_blocker_reason_source_maps_to_block_even_for_review_status(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            run_dir = tmp_path / "run"
            run_dir.mkdir()
            write_json(
                run_dir / "validation_report.json",
                {
                    "run_id": "blocker-run",
                    "overall_status": "needs_review",
                    "sign_off_ready": False,
                    "reason_codes": ["docs_only.source_file_blocked"],
                    "reason_sources": [
                        {
                            "code": "docs_only.source_file_blocked",
                            "severity": "blocker",
                            "summary": "Source file changed in docs-only policy.",
                        }
                    ],
                },
            )
            write_json(
                run_dir / "revision_decision.json",
                {
                    "final_status": "review_required",
                    "reason": "Review path selected.",
                    "next_action": "manual_review_handoff",
                },
            )

            decision, comment = render_gate(run_dir, tmp_path / "out")

        self.assertEqual(decision["outcome"], "block")
        self.assertIn("docs_only.source_file_blocked", decision["reason_codes"])
        self.assertIn("# AI Workbench PR Gate: Block", comment)


if __name__ == "__main__":
    unittest.main()
