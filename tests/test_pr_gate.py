import json
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai_workbench_mcp.tools.pr_gate import pr_gate_payload
from ai_workbench_mcp.tools.pr_gate_comment import (
    COMMENT_MARKER,
    body_with_marker,
    load_comment_body,
    upsert_pr_gate_comment,
)


ROOT = Path(__file__).resolve().parents[1]
ACCEPTED_SAMPLE = ROOT / "examples" / "sample-runs" / "accepted-tiny-python-fix"
NEEDS_REVIEW_SAMPLE = ROOT / "examples" / "sample-runs" / "needs-review-test-fix"


def comment_outcome_label(outcome: str) -> str:
    return {
        "accept": "Accept",
        "needs_review": "Needs Review",
        "block": "Block",
    }.get(outcome, outcome)


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def render_gate(run_dir: Path, out_dir: Path) -> tuple[dict[str, object], str]:
    return render_gate_args(out_dir, run_dir=str(run_dir))


def render_gate_args(out_dir: Path, **kwargs: object) -> tuple[dict[str, object], str]:
    comment_path = out_dir / "pr_comment.md"
    decision_path = out_dir / "pr_decision.json"
    decision = pr_gate_payload(
        SimpleNamespace(
            run_dir=kwargs.get("run_dir"),
            runs_dir=kwargs.get("runs_dir"),
            run_id=kwargs.get("run_id"),
            fallback_run_dir=kwargs.get("fallback_run_dir"),
            out=str(comment_path),
            json_out=str(decision_path),
        )
    )
    return decision, comment_path.read_text(encoding="utf-8")


class FakeGraphQLRunner:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = list(responses)
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], **_kwargs: object) -> SimpleNamespace:
        self.commands.append(command)
        response = self.responses.pop(0)
        return SimpleNamespace(returncode=0, stdout=json.dumps(response), stderr="")


class PrGateTests(unittest.TestCase):
    def assert_scan_first_section(self, comment: str, decision: dict[str, object]) -> None:
        lines = comment.splitlines()
        self.assertGreaterEqual(len(lines), 6)
        self.assertEqual(lines[0], f"# AI Workbench PR Gate: {comment_outcome_label(str(decision['outcome']))}")
        self.assertEqual(lines[2], f"Decision: {comment_outcome_label(str(decision['outcome']))}")
        self.assertTrue(lines[3].startswith("Why: "))
        self.assertTrue(lines[4].startswith("Required next action: "))
        self.assertTrue(lines[5].startswith("Evidence present: validation_report "))

    def test_accepted_sample_evidence_maps_to_accept(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            decision, comment = render_gate(ACCEPTED_SAMPLE, Path(tmpdir))

        self.assertEqual(decision["operation"], "workbench_pr_gate")
        self.assertEqual(decision["schema_version"], 1)
        self.assertEqual(decision["outcome"], "accept")
        self.assertTrue(decision["ok"])
        self.assertEqual(decision["evidence_source"], "acceptance_run")
        self.assertEqual(decision["source_run_dir"], "examples/sample-runs/accepted-tiny-python-fix")
        self.assertEqual(decision["validation_status"], "passed")
        self.assertEqual(decision["quality_gate_status"], "accepted")
        self.assert_scan_first_section(comment, decision)
        self.assertIn("# AI Workbench PR Gate: Accept", comment)
        self.assertIn("Decision: Accept", comment)
        self.assertIn("Why: Validation passed and the quality gate accepted the run.", comment)
        self.assertIn("Evidence present: validation_report yes, revision_decision yes", comment)
        self.assertIn("**Evidence source:** `acceptance_run`", comment)
        self.assertIn("validation_report.json", comment)
        self.assertIn("revision_decision.json", comment)

    def test_runs_dir_and_run_id_resolve_explicit_acceptance_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            decision, comment = render_gate_args(
                Path(tmpdir),
                runs_dir=str(ROOT / "examples" / "sample-runs"),
                run_id="accepted-tiny-python-fix",
            )

        self.assertEqual(decision["outcome"], "accept")
        self.assertEqual(decision["evidence_source"], "acceptance_run")
        self.assertEqual(decision["source_run_dir"], "examples/sample-runs/accepted-tiny-python-fix")
        self.assert_scan_first_section(comment, decision)
        self.assertIn("# AI Workbench PR Gate: Accept", comment)

    def test_policy_pack_name_is_read_from_validation_report_policy_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            run_dir = tmp_path / "run"
            run_dir.mkdir()
            write_json(
                run_dir / "validation_report.json",
                {
                    "run_id": "policy-pack-run",
                    "profile": "legacy_profile_should_not_win",
                    "policy_pack": {"name": "docs_only"},
                    "overall_status": "passed",
                    "sign_off_ready": True,
                },
            )
            write_json(
                run_dir / "revision_decision.json",
                {
                    "run_id": "policy-pack-run",
                    "final_status": "accepted",
                },
            )

            decision, comment = render_gate(run_dir, tmp_path / "out")

        self.assertEqual(decision["outcome"], "accept")
        self.assertEqual(decision["policy_pack"], "docs_only")
        self.assertIn("**Policy pack:** `docs_only`", comment)

    def test_policy_pack_name_falls_back_to_legacy_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            run_dir = tmp_path / "run"
            run_dir.mkdir()
            write_json(
                run_dir / "validation_report.json",
                {
                    "run_id": "legacy-profile-run",
                    "profile": "low_risk_bug_fix",
                    "overall_status": "passed",
                    "sign_off_ready": True,
                },
            )
            write_json(
                run_dir / "revision_decision.json",
                {
                    "run_id": "legacy-profile-run",
                    "final_status": "accepted",
                },
            )

            decision, comment = render_gate(run_dir, tmp_path / "out")

        self.assertEqual(decision["outcome"], "accept")
        self.assertEqual(decision["policy_pack"], "low_risk_bug_fix")
        self.assertIn("**Policy pack:** `low_risk_bug_fix`", comment)

    def test_missing_validation_report_maps_to_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            run_dir = tmp_path / "run"
            shutil.copytree(ACCEPTED_SAMPLE, run_dir)
            (run_dir / "validation_report.json").unlink()

            decision, comment = render_gate(run_dir, tmp_path / "out")

        self.assertEqual(decision["outcome"], "block")
        self.assertEqual(decision["validation_status"], "unknown")
        self.assertEqual(decision["quality_gate_status"], "accepted")
        self.assertIn("Missing required Workbench evidence: validation_report.json.", decision["reason"])
        self.assert_scan_first_section(comment, decision)
        self.assertIn("Evidence present: validation_report no, revision_decision yes", comment)

    def test_missing_revision_decision_maps_to_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            run_dir = tmp_path / "run"
            shutil.copytree(ACCEPTED_SAMPLE, run_dir)
            (run_dir / "revision_decision.json").unlink()

            decision, comment = render_gate(run_dir, tmp_path / "out")

        self.assertEqual(decision["outcome"], "block")
        self.assertEqual(decision["evidence_source"], "acceptance_run")
        self.assertEqual(decision["quality_gate_status"], "unknown")
        self.assertIn("Missing required Workbench evidence: revision_decision.json.", decision["reason"])
        self.assertIn("# AI Workbench PR Gate: Block", comment)
        self.assertIn("Evidence present: validation_report yes, revision_decision no", comment)
        self.assertIn("| revision_decision | `revision_decision.json` | no |", comment)

    def test_invalid_json_evidence_maps_to_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            run_dir = tmp_path / "run"
            shutil.copytree(ACCEPTED_SAMPLE, run_dir)
            (run_dir / "validation_report.json").write_text("{not json", encoding="utf-8")

            decision, comment = render_gate(run_dir, tmp_path / "out")

        self.assertEqual(decision["outcome"], "block")
        self.assertEqual(decision["validation_status"], "unknown")
        self.assertEqual(decision["quality_gate_status"], "accepted")
        self.assertIn("Unreadable Workbench evidence: validation_report.json", decision["reason"])
        self.assert_scan_first_section(comment, decision)
        self.assertIn("Evidence present: validation_report yes, revision_decision yes", comment)

    def test_fallback_scaffold_blocks_with_acceptance_evidence_missing_reason(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            fallback_dir = tmp_path / "ci_scaffold"
            fallback_dir.mkdir()
            write_json(
                fallback_dir / "validation_report.json",
                {
                    "run_id": "ci_scaffold",
                    "overall_status": "passed",
                    "sign_off_ready": True,
                    "reason_codes": ["validation.accepted"],
                },
            )
            (fallback_dir / "model_output.md").write_text("SECRET_RAW_MODEL_MARKER\n", encoding="utf-8")

            decision, comment = render_gate_args(tmp_path / "out", fallback_run_dir=str(fallback_dir))

        self.assertEqual(decision["outcome"], "block")
        self.assertEqual(decision["evidence_source"], "fallback_scaffold")
        self.assertEqual(decision["validation_status"], "passed")
        self.assertEqual(decision["quality_gate_status"], "unknown")
        self.assertEqual(decision["reason"], "No complete Workbench acceptance evidence found for this PR.")
        self.assertEqual(decision["reason_codes"], ["validation.accepted", "pr_gate.acceptance_evidence_missing"])
        self.assert_scan_first_section(comment, decision)
        self.assertIn("# AI Workbench PR Gate: Block", comment)
        self.assertIn("Decision: Block", comment)
        self.assertIn("Evidence present: validation_report yes, revision_decision no", comment)
        self.assertIn("No complete Workbench acceptance evidence found for this PR.", comment)
        self.assertIn("`pr_gate.acceptance_evidence_missing`", comment)
        self.assertNotIn("SECRET_RAW_MODEL_MARKER", comment)

    def test_explicit_scaffold_profile_blocks_even_with_accepted_quality_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            run_dir = tmp_path / "run"
            run_dir.mkdir()
            write_json(
                run_dir / "validation_report.json",
                {
                    "run_id": "ci_scaffold",
                    "profile": "scaffold",
                    "overall_status": "passed",
                    "sign_off_ready": True,
                    "reason_codes": ["validation.accepted"],
                },
            )
            write_json(
                run_dir / "revision_decision.json",
                {
                    "final_status": "accepted",
                    "reason": "No quality loop triggers detected.",
                    "next_action": "none",
                    "reason_codes": ["quality_gate.accepted"],
                },
            )
            (run_dir / "model_output.md").write_text("SECRET_RAW_MODEL_MARKER\n", encoding="utf-8")
            (run_dir / "provider.log").write_text("SECRET_PROVIDER_LOG_MARKER\n", encoding="utf-8")
            (run_dir / "run_log.jsonl").write_text("{}\n", encoding="utf-8")

            decision, comment = render_gate(run_dir, tmp_path / "out")

        self.assertEqual(decision["outcome"], "block")
        self.assertEqual(decision["evidence_source"], "acceptance_run")
        self.assertEqual(decision["validation_status"], "passed")
        self.assertEqual(decision["quality_gate_status"], "accepted")
        self.assertEqual(
            decision["reason_codes"],
            ["validation.accepted", "quality_gate.accepted", "pr_gate.acceptance_evidence_missing"],
        )
        self.assertIn("`pr_gate.acceptance_evidence_missing`", comment)
        self.assertIn("Evidence present: validation_report yes, revision_decision yes", comment)
        self.assertNotIn("SECRET_RAW_MODEL_MARKER", comment)
        self.assertNotIn("SECRET_PROVIDER_LOG_MARKER", comment)

    def test_failed_validation_or_revision_required_maps_to_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            decision, comment = render_gate(NEEDS_REVIEW_SAMPLE, Path(tmpdir))

        self.assertEqual(decision["outcome"], "block")
        self.assertEqual(decision["validation_status"], "failed")
        self.assertEqual(decision["quality_gate_status"], "revision_required")
        self.assertIn("Deterministic validation failed", decision["reason"])
        self.assert_scan_first_section(comment, decision)
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
        self.assert_scan_first_section(comment, decision)
        self.assertIn("# AI Workbench PR Gate: Needs Review", comment)
        self.assertIn("Decision: Needs Review", comment)
        self.assertIn("Why: Policy requires review.", comment)
        self.assertIn("Evidence present: validation_report yes, revision_decision yes", comment)
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
        self.assertEqual(decision["reason"], "Source file changed in docs-only policy.")
        self.assertIn("docs_only.source_file_blocked", decision["reason_codes"])
        self.assertIn("# AI Workbench PR Gate: Block", comment)

    def test_pr_comment_marker_is_added_once(self) -> None:
        body = body_with_marker("# AI Workbench PR Gate: Block\n")
        self.assertTrue(body.startswith(COMMENT_MARKER))
        self.assertEqual(body.count(COMMENT_MARKER), 1)

        marked_again = body_with_marker(body)
        self.assertEqual(marked_again.count(COMMENT_MARKER), 1)

    def test_pr_comment_body_does_not_embed_decision_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            comment_path = tmp_path / "comment.md"
            decision_path = tmp_path / "decision.json"
            comment_path.write_text("# AI Workbench PR Gate: Block\n", encoding="utf-8")
            write_json(decision_path, {"outcome": "block", "private_marker": "SECRET_DECISION_MARKER"})

            body = load_comment_body(comment_path, decision_path)

        self.assertIn(COMMENT_MARKER, body)
        self.assertIn("# AI Workbench PR Gate: Block", body)
        self.assertNotIn("SECRET_DECISION_MARKER", body)

    def test_pr_comment_helper_creates_marker_comment_when_missing(self) -> None:
        runner = FakeGraphQLRunner(
            [
                {
                    "data": {
                        "repository": {
                            "pullRequest": {
                                "id": "PR_node",
                                "comments": {"nodes": []},
                            }
                        }
                    }
                },
                {
                    "data": {
                        "addComment": {
                            "commentEdge": {
                                "node": {
                                    "id": "comment_node",
                                    "url": "https://github.example/comment",
                                }
                            }
                        }
                    }
                },
            ]
        )

        result = upsert_pr_gate_comment(
            repo="owner/repo",
            pr_number=7,
            body=body_with_marker("# AI Workbench PR Gate: Block"),
            runner=runner,
        )

        self.assertEqual(result["operation"], "workbench_pr_gate_comment")
        self.assertEqual(result["action"], "created")
        self.assertEqual(result["comment_id"], "comment_node")
        self.assertEqual(result["comment_url"], "https://github.example/comment")
        self.assertIn("addComment", " ".join(runner.commands[1]))
        self.assertTrue(any(arg == "number=7" for arg in runner.commands[0]))
        self.assertTrue(any(arg.startswith("body=") and COMMENT_MARKER in arg for arg in runner.commands[1]))

    def test_pr_comment_helper_updates_existing_marker_comment(self) -> None:
        runner = FakeGraphQLRunner(
            [
                {
                    "data": {
                        "repository": {
                            "pullRequest": {
                                "id": "PR_node",
                                "comments": {
                                    "nodes": [
                                        {
                                            "id": "old_comment",
                                            "body": f"{COMMENT_MARKER}\n\nold body",
                                            "url": "https://github.example/old",
                                        }
                                    ]
                                },
                            }
                        }
                    }
                },
                {
                    "data": {
                        "updateIssueComment": {
                            "issueComment": {
                                "id": "old_comment",
                                "url": "https://github.example/old",
                            }
                        }
                    }
                },
            ]
        )

        result = upsert_pr_gate_comment(
            repo="owner/repo",
            pr_number=7,
            body=body_with_marker("# AI Workbench PR Gate: Needs Review"),
            runner=runner,
        )

        self.assertEqual(result["action"], "updated")
        self.assertEqual(result["comment_id"], "old_comment")
        self.assertIn("updateIssueComment", " ".join(runner.commands[1]))
        self.assertTrue(any(arg == "id=old_comment" for arg in runner.commands[1]))


if __name__ == "__main__":
    unittest.main()
