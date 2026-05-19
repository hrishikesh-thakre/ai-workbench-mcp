import json
import inspect
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_workbench_mcp.contracts import (
    SCHEMA_VERSION,
    V03_ACCEPTANCE_REQUIRED_ARTIFACTS,
    V03_COMPLETE_RUN_ARTIFACTS,
    V03_POLICY_PACK_NAMES,
    V03_POLICY_PACK_REASON_CODE_KEYS,
    V03_POLICY_PACK_REQUIRED_FIELDS,
    V03_PR_GATE_EVIDENCE,
    V03_PR_GATE_EVIDENCE_SOURCES,
    V03_PR_GATE_OUTCOMES,
    error_envelope,
    response_envelope,
)
from ai_workbench_mcp.core import (
    model_selection_file_response,
    model_selection_response,
    policy_pack_selection_response,
    quality_gate_response,
    quality_gate,
    run_analysis_file_response,
    run_analysis_response,
    analyze_runs,
    select_model,
    select_policy_pack,
    validate_run,
    validation_response,
)
from ai_workbench_mcp.tools.pr_gate import (
    ACCEPTANCE_EVIDENCE_MISSING_CODE,
    OUTCOME_LABELS,
    OPERATION as PR_GATE_OPERATION,
    STANDARD_EVIDENCE,
)
from ai_workbench_mcp.tools.pr_gate_comment import COMMENT_MARKER
from ai_workbench_mcp.tools.policy_packs import (
    PRODUCT_POLICY_PACK_NAMES,
    REQUIRED_LIST_FIELDS,
    REQUIRED_REASON_CODE_KEYS,
    load_policy_pack_catalog,
)


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_V02_BASELINE = ROOT / "docs" / "contracts" / "v0.2-contract-baseline.md"
CONTRACT_V03_BASELINE = ROOT / "docs" / "contracts" / "v0.3-contract-baseline.md"
CONTRACT_FIXTURES = ROOT / "tests" / "fixtures" / "contracts"
ANALYTICS_CONTRACT_KEYS = (
    "runs_total",
    "runs_passed",
    "runs_failed",
    "runs_needs_review",
    "evidence_scope",
    "excluded_runs_total",
    "workflow_signoff_pass_rate",
    "workflow_needs_review_rate",
    "average_confidence",
    "accepted_runs_total",
    "failed_runs_total",
    "review_required_runs_total",
    "other_runs_total",
    "execution_host_counts",
    "response_source_counts",
    "accepted_runs_by_recipe",
    "accepted_runs_by_validation_profile",
    "accepted_runs_by_selected_tier",
    "accepted_runs_by_execution_host",
    "accepted_runs_by_response_source",
    "model_tier_usage",
    "validation_profiles_used",
    "quality_gate_outcomes",
    "outcome_counts",
    "cost_tracking",
    "time_tracking",
    "run_cost_time",
    "workflow_kpis",
)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_contract_fixture(name: str) -> dict[str, object]:
    return json.loads((CONTRACT_FIXTURES / name).read_text(encoding="utf-8"))


def normalize_contract_fixture_paths(value: object) -> object:
    if isinstance(value, dict):
        return {key: normalize_contract_fixture_paths(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize_contract_fixture_paths(item) for item in value]
    if isinstance(value, str):
        return value.replace("\\", "/")
    return value


def analytics_contract_projection(metrics: dict[str, object]) -> dict[str, object]:
    return {key: metrics[key] for key in ANALYTICS_CONTRACT_KEYS}


class ContractEnvelopeTests(unittest.TestCase):
    def test_response_envelope_has_stable_common_fields(self) -> None:
        response = response_envelope(
            operation="workbench_example",
            status="completed",
            ok=True,
            artifacts={"report": Path("runs/example/report.json")},
            summary={"count": 1},
        )

        self.assertEqual(
            list(response),
            ["schema_version", "operation", "status", "ok", "artifacts", "summary", "errors"],
        )
        self.assertEqual(response["schema_version"], 1)
        self.assertEqual(response["operation"], "workbench_example")
        self.assertEqual(response["status"], "completed")
        self.assertTrue(response["ok"])
        self.assertEqual(response["artifacts"]["report"], str(Path("runs/example/report.json")))
        self.assertEqual(response["errors"], [])
        self.assertEqual(json.loads(json.dumps(response))["summary"]["count"], 1)
        self.assertEqual(normalize_contract_fixture_paths(response), load_contract_fixture("response_envelope.json"))

    def test_error_envelope_marks_response_not_ok(self) -> None:
        response = error_envelope(
            operation="workbench_validate_run",
            code="missing_artifact",
            message="validation_report.json was not found.",
        )

        self.assertFalse(response["ok"])
        self.assertEqual(response["status"], "error")
        self.assertEqual(response["errors"][0]["code"], "missing_artifact")
        self.assertEqual(response, load_contract_fixture("error_envelope.json"))


class ContractDocumentationTests(unittest.TestCase):
    def test_v02_contract_baseline_documents_current_public_surfaces(self) -> None:
        text = CONTRACT_V02_BASELINE.read_text(encoding="utf-8")

        required_phrases = [
            "Status: v0.2 alpha contract baseline, not v1-stable",
            "v0.3-contract-baseline.md",
            "Consumers must tolerate additive fields.",
            "older committed sample runs that omit newer additive fields",
            "`runs/<run_id>/` remains the local evidence ledger",
            "validation_report.json",
            "revision_decision.json",
            "model_selection.json",
            "model_output.md",
            "run_log.jsonl",
            'overall_status="passed"',
            "sign_off_ready=true",
            'final_status="accepted"',
            "policy_pack",
            "reason_sources",
            "reason_codes",
            "severity=\"blocker\"",
            "configs/validation_profiles.yaml",
            "docs_only",
            "low_risk_bug_fix",
            "test_fix",
            "api_contract_change",
            "security_privacy_sensitive",
            "run_metrics.json",
            "run_summary.md",
            "run_dashboard.html",
            "routing_feedback_candidates",
            "cost_tracking",
            "time_tracking",
            "pr_comment.md",
            "pr_decision.json",
            "evidence_source",
            "acceptance_run",
            "fallback_scaffold",
            "missing",
            "AI Workbench PR Gate: Accept|Needs Review|Block",
            COMMENT_MARKER,
            ACCEPTANCE_EVIDENCE_MISSING_CODE,
            PR_GATE_OPERATION,
            "Deliberately Not Stable Yet",
        ]

        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        for label, file_name in STANDARD_EVIDENCE:
            with self.subTest(evidence=label):
                self.assertIn(label, text)
                self.assertIn(file_name, text)

    def test_v02_contract_baseline_documents_mcp_envelope(self) -> None:
        text = CONTRACT_V02_BASELINE.read_text(encoding="utf-8")

        self.assertIn(f'"schema_version": {SCHEMA_VERSION}', text)
        for field in ("operation", "status", "ok", "artifacts", "summary", "errors"):
            with self.subTest(field=field):
                self.assertIn(f'"{field}"', text)
        for operation in (
            "workbench_open_run",
            "workbench_select_model",
            "workbench_record_execution",
            "workbench_validate_run",
            "workbench_quality_gate",
            "workbench_analyze_runs",
        ):
            with self.subTest(operation=operation):
                self.assertIn(operation, text)

    def test_v02_contract_baseline_is_linked_from_primary_docs(self) -> None:
        docs = [
            ROOT / "README.md",
            ROOT / "docs" / "ai" / "START_HERE.md",
            ROOT / "docs" / "ai" / "PROJECT_MAP.md",
            ROOT / "docs" / "github" / "pr-gate.md",
        ]

        for path in docs:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIn(
                    "v0.2-contract-baseline.md",
                    path.read_text(encoding="utf-8"),
                )

    def test_v03_contract_baseline_documents_semantic_pr_acceptance_alpha(self) -> None:
        text = CONTRACT_V03_BASELINE.read_text(encoding="utf-8")

        required_phrases = [
            "Status: v0.3 semantic PR acceptance alpha contract baseline, not v1-stable",
            "v0.2-contract-baseline.md",
            "Complete Run Evidence",
            "validation_report.json",
            "revision_decision.json",
            'overall_status="passed"',
            "sign_off_ready=true",
            'final_status="accepted"',
            "Policy-Pack Catalog",
            "configs/policy_packs.yaml",
            "schema_version: 1",
            "Advisory Policy-Pack Selector",
            "workbench_select_policy_pack",
            "recommended_policy_pack",
            "recommended_validation_profile",
            "profile_selection_mode",
            "matched_signals",
            "security/privacy -> api/MCP contract -> docs-only -> known failing test repair -> low-risk bug fix",
            "PR Decision JSON",
            PR_GATE_OPERATION,
            "accept",
            "needs_review",
            "block",
            "acceptance_run",
            "fallback_scaffold",
            "missing",
            ACCEPTANCE_EVIDENCE_MISSING_CODE,
            "recovery_steps",
            "PR Comment Surface",
            "Evidence present: validation_report yes|no, revision_decision yes|no",
            "Recovery",
            COMMENT_MARKER,
            "GitHub Workflow Template Boundary",
            ".github/workflows/ai-workbench-pr-gate.yml",
            "Package And Bootstrap Boundary",
            "ai-workbench-mcp==0.6.0a0",
            "ai-workbench-bootstrap --target .",
            "ai-workbench-bootstrap-assets",
            "Machine-Readable Contract Fixtures",
            "tests/fixtures/contracts/response_envelope.json",
            "tests/fixtures/contracts/pr_gate_decisions.json",
            "tests/fixtures/contracts/analytics_single_accepted_run_projection.json",
            "pre-v1 regression guards",
            "Deliberately Not Stable Yet",
        ]

        for phrase in required_phrases:
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, text)

        for artifact in V03_COMPLETE_RUN_ARTIFACTS:
            with self.subTest(artifact=artifact):
                self.assertIn(artifact, text)
        for artifact in V03_ACCEPTANCE_REQUIRED_ARTIFACTS:
            with self.subTest(required_artifact=artifact):
                self.assertIn(artifact, text)
        for label, file_name in V03_PR_GATE_EVIDENCE:
            with self.subTest(evidence=label):
                self.assertIn(label, text)
                self.assertIn(file_name, text)
        for pack_name in V03_POLICY_PACK_NAMES:
            with self.subTest(policy_pack=pack_name):
                self.assertIn(pack_name, text)
        for field in V03_POLICY_PACK_REQUIRED_FIELDS:
            with self.subTest(policy_field=field):
                self.assertIn(field, text)
        for key in V03_POLICY_PACK_REASON_CODE_KEYS:
            with self.subTest(reason_code_key=key):
                self.assertIn(key, text)

    def test_v03_contract_constants_match_landed_implementations(self) -> None:
        manifest = load_contract_fixture("complete_run_manifest.json")
        self.assertEqual(manifest["contract_status"], "v0.x-pre-v1")
        self.assertEqual(manifest["complete_run_artifacts"], list(V03_COMPLETE_RUN_ARTIFACTS))
        self.assertEqual(manifest["acceptance_required_artifacts"], list(V03_ACCEPTANCE_REQUIRED_ARTIFACTS))
        self.assertEqual(manifest["pr_gate_evidence"], [list(item) for item in V03_PR_GATE_EVIDENCE])
        self.assertEqual(manifest["pr_gate_outcomes"], list(V03_PR_GATE_OUTCOMES))
        self.assertEqual(manifest["pr_gate_evidence_sources"], list(V03_PR_GATE_EVIDENCE_SOURCES))

        self.assertEqual(V03_PR_GATE_EVIDENCE, STANDARD_EVIDENCE)
        self.assertEqual(V03_PR_GATE_OUTCOMES, tuple(OUTCOME_LABELS))
        self.assertEqual(V03_PR_GATE_EVIDENCE_SOURCES, ("acceptance_run", "fallback_scaffold", "missing"))
        self.assertEqual(V03_POLICY_PACK_NAMES, PRODUCT_POLICY_PACK_NAMES)
        self.assertEqual(
            V03_POLICY_PACK_REQUIRED_FIELDS,
            ("name", "version", "validation_profile", "source", *REQUIRED_LIST_FIELDS, "reason_codes"),
        )
        self.assertEqual(V03_POLICY_PACK_REASON_CODE_KEYS, REQUIRED_REASON_CODE_KEYS)

        catalog = load_policy_pack_catalog()
        self.assertEqual(tuple(catalog), V03_POLICY_PACK_NAMES)
        for pack_name, pack in catalog.items():
            with self.subTest(policy_pack=pack_name):
                self.assertEqual(tuple(pack), V03_POLICY_PACK_REQUIRED_FIELDS)
                self.assertEqual(tuple(pack["reason_codes"]), V03_POLICY_PACK_REASON_CODE_KEYS)
                self.assertEqual(pack["required_evidence"], ["model_selection.json", "model_output.md", "run_log.jsonl"])

    def test_v03_pr_gate_demo_decisions_follow_contract_shape(self) -> None:
        expected_fields = {
            "schema_version",
            "operation",
            "outcome",
            "ok",
            "run_id",
            "evidence_source",
            "source_run_dir",
            "policy_pack",
            "validation_profile",
            "policy_pack_selection_mode",
            "validation_status",
            "quality_gate_status",
            "reason",
            "reason_codes",
            "evidence",
            "required_next_action",
        }
        demos = {
            "accepted": "accept",
            "needs-review": "needs_review",
            "blocked": "block",
        }
        expected_evidence = dict(V03_PR_GATE_EVIDENCE)
        fixture = load_contract_fixture("pr_gate_decisions.json")

        for slug, expected_outcome in demos.items():
            with self.subTest(demo=slug):
                demo_dir = ROOT / "examples" / "pr-gate-outcomes" / slug
                decision = json.loads((demo_dir / "pr_decision.json").read_text(encoding="utf-8"))
                comment = (demo_dir / "pr_comment.md").read_text(encoding="utf-8")

                self.assertEqual(decision, fixture[slug])
                self.assertTrue(expected_fields.issubset(decision))
                self.assertEqual(decision["schema_version"], SCHEMA_VERSION)
                self.assertEqual(decision["operation"], PR_GATE_OPERATION)
                self.assertEqual(decision["outcome"], expected_outcome)
                self.assertIsInstance(decision["policy_pack"], str)
                self.assertIsInstance(decision["validation_profile"], str)
                self.assertIsInstance(decision["policy_pack_selection_mode"], str)
                self.assertIn(decision["outcome"], V03_PR_GATE_OUTCOMES)
                self.assertIn(decision["evidence_source"], V03_PR_GATE_EVIDENCE_SOURCES)
                self.assertIsInstance(decision["reason_codes"], list)
                self.assertIsInstance(decision["required_next_action"], str)

                evidence = {entry["label"]: entry for entry in decision["evidence"]}
                self.assertEqual({label: entry["path"] for label, entry in evidence.items()}, expected_evidence)
                for artifact in V03_ACCEPTANCE_REQUIRED_ARTIFACTS:
                    label = next(label for label, path in V03_PR_GATE_EVIDENCE if path == artifact)
                    self.assertTrue(evidence[label]["present"])

                self.assertIn(f"# AI Workbench PR Gate: {OUTCOME_LABELS[expected_outcome]}", comment)
                self.assertIn("Decision:", comment)
                self.assertIn("**Policy pack:**", comment)
                self.assertIn("Why:", comment)
                self.assertIn("Required next action:", comment)
                self.assertIn("Evidence present: validation_report yes, revision_decision yes", comment)
                self.assertIn("This artifact is generated from Workbench evidence only.", comment)

    def test_v03_contract_baseline_is_linked_from_owned_docs(self) -> None:
        docs = [
            CONTRACT_V02_BASELINE,
            ROOT / "docs" / "github" / "pr-gate.md",
        ]

        for path in docs:
            with self.subTest(path=path.relative_to(ROOT)):
                self.assertIn(
                    "v0.3-contract-baseline.md",
                    path.read_text(encoding="utf-8"),
                )


class OperationContractTests(unittest.TestCase):
    def test_model_selection_response_summarizes_selected_model(self) -> None:
        response = model_selection_response(
            {
                "run_id": "run1",
                "project": "ai_workbench_mcp",
                "status": "selected",
                "selected_tier": "local_coding",
                "selected_model": {"provider": "goose", "model": "example-model"},
                "risk": "medium",
                "validation_strength": "strong",
                "complexity_score": 8,
                "complexity_band": "easy",
                "matched_rule": "bounded_work_local_default",
                "reason": "Recoverable bounded coding work can start locally.",
                "routing_feedback": {
                    "status": "advisory",
                    "recommendation": "prefer_current_tier",
                    "candidate_key": "recipe|profile|local_coding|medium|easy",
                },
            },
            artifacts={"model_selection": "runs/run1/model_selection.json"},
        )

        self.assertEqual(response["operation"], "workbench_select_model")
        self.assertEqual(response["status"], "selected")
        self.assertTrue(response["ok"])
        self.assertEqual(response["summary"]["selected_tier"], "local_coding")
        self.assertEqual(response["summary"]["provider"], "goose")
        self.assertEqual(response["summary"]["model"], "example-model")
        self.assertEqual(response["summary"]["routing_feedback_status"], "advisory")
        self.assertEqual(response["summary"]["routing_feedback_recommendation"], "prefer_current_tier")

    def test_policy_pack_selection_response_summarizes_advisory_recommendation(self) -> None:
        response = policy_pack_selection_response(
            {
                "status": "selected",
                "ok": True,
                "recommended_policy_pack": "docs_only",
                "recommended_validation_profile": "docs_only",
                "profile_selection_mode": "auto_advisory",
                "reason": "Only documentation files changed.",
                "matched_signals": ["doc_file:README.md"],
                "confidence": 0.7,
                "candidate_policy_packs": ["docs_only", "low_risk_bug_fix"],
            }
        )

        self.assertEqual(response["operation"], "workbench_select_policy_pack")
        self.assertEqual(response["status"], "selected")
        self.assertTrue(response["ok"])
        self.assertEqual(response["summary"]["recommended_policy_pack"], "docs_only")
        self.assertEqual(response["summary"]["recommended_validation_profile"], "docs_only")
        self.assertEqual(response["summary"]["profile_selection_mode"], "auto_advisory")
        self.assertEqual(response["summary"]["matched_signals"], ["doc_file:README.md"])
        self.assertEqual(response["summary"]["confidence"], 0.7)

    def test_validation_response_requires_passed_signoff_for_ok(self) -> None:
        response = validation_response(
            {
                "run_id": "run1",
                "project": "ai_workbench_mcp",
                "profile": "run_signoff",
                "overall_status": "needs_review",
                "sign_off_ready": False,
                "confidence": 0.75,
                "summary": {
                    "commands_passed": 2,
                    "commands_failed": 0,
                    "checks_passed": 3,
                    "checks_needs_review": 1,
                    "checks_failed": 0,
                },
            }
        )

        self.assertEqual(response["operation"], "workbench_validate_run")
        self.assertEqual(response["status"], "needs_review")
        self.assertFalse(response["ok"])
        self.assertEqual(response["summary"]["checks_needs_review"], 1)

    def test_quality_gate_response_only_accepts_accepted_decision(self) -> None:
        response = quality_gate_response(
            {
                "loop_type": "alternate_model_review",
                "required": True,
                "reason": "Validation failed.",
                "next_action": "manual_review_handoff",
                "accepted_pass": 0,
                "final_status": "review_required",
                "blocking_findings": ["validation failed"],
                "non_blocking_findings": [],
                "authoritative_model_output": "model_output.md",
                "authoritative_validation_report": "validation_report.json",
            }
        )

        self.assertEqual(response["operation"], "workbench_quality_gate")
        self.assertEqual(response["status"], "review_required")
        self.assertFalse(response["ok"])
        self.assertEqual(response["summary"]["blocking_findings"], 1)

    def test_run_analysis_response_reports_completed_metrics(self) -> None:
        response = run_analysis_response(
            {
                "runs_total": 4,
                "runs_passed": 3,
                "runs_failed": 0,
                "runs_needs_review": 1,
                "workflow_signoff_pass_rate": 0.75,
                "workflow_needs_review_rate": 0.25,
                "average_confidence": 0.9,
            }
        )

        self.assertEqual(response["operation"], "workbench_analyze_runs")
        self.assertEqual(response["status"], "completed")
        self.assertTrue(response["ok"])
        self.assertEqual(response["summary"]["runs_total"], 4)

    def test_file_wrapper_reads_json_artifact_and_records_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "model_selection.json"
            artifact.write_text(
                json.dumps(
                    {
                        "status": "selected",
                        "selected_tier": "frontier",
                        "selected_model": {"provider": "litellm", "model": "openai/gpt-5.5"},
                    }
                ),
                encoding="utf-8",
            )

            response = model_selection_file_response(artifact)

        self.assertTrue(response["ok"])
        self.assertEqual(response["summary"]["selected_tier"], "frontier")
        self.assertEqual(response["artifacts"]["model_selection"], str(artifact))

    def test_select_model_direct_call_writes_artifact_and_wraps_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "model_selection.json"

            with patch("ai_workbench_mcp.core.subprocess.run", side_effect=AssertionError("subprocess not expected")):
                response = select_model(
                    project="ai_workbench_mcp",
                    task_type="implement",
                    risk="medium",
                    out=artifact,
                    prompt="implement_request_change_request",
                    complexity_score=13,
                )
            written = json.loads(artifact.read_text(encoding="utf-8"))
            events = read_jsonl(Path(tmpdir) / "events.jsonl")

        self.assertEqual(written["selected_tier"], "local_coding")
        self.assertTrue(response["ok"])
        self.assertEqual(response["operation"], "workbench_select_model")
        self.assertEqual(response["status"], "selected")
        self.assertEqual(response["summary"]["selected_tier"], "local_coding")
        self.assertEqual(response["summary"]["provider"], "goose")
        self.assertEqual(response["summary"]["model"], "unsloth/gemma-4-E4B-it-GGUF:Q4_K_M")
        self.assertEqual(response["summary"]["risk"], "medium")
        self.assertEqual(response["summary"]["validation_strength"], "medium")
        self.assertEqual(response["summary"]["complexity_band"], "moderate")
        self.assertEqual(response["summary"]["matched_rule"], "easy_moderate_local_coding")
        self.assertEqual(written["routing_feedback"]["status"], "not_provided")
        self.assertEqual(response["summary"]["routing_feedback_status"], "not_provided")
        self.assertEqual(response["artifacts"]["events"], str(Path(tmpdir) / "events.jsonl"))
        self.assertEqual(events[0]["operation"], "workbench_select_model")
        self.assertEqual(events[0]["artifacts"]["events"], str(Path(tmpdir) / "events.jsonl"))

    def test_select_policy_pack_direct_call_wraps_payload(self) -> None:
        response = select_policy_pack(
            task_text="Docs-only update for README.",
            changed_files=["README.md"],
            risk="low",
        )

        self.assertTrue(response["ok"])
        self.assertEqual(response["operation"], "workbench_select_policy_pack")
        self.assertEqual(response["status"], "selected")
        self.assertEqual(response["summary"]["recommended_policy_pack"], "docs_only")
        self.assertEqual(response["summary"]["recommended_validation_profile"], "docs_only")
        self.assertEqual(response["summary"]["profile_selection_mode"], "auto_advisory")
        self.assertIn("doc_file:README.md", response["summary"]["matched_signals"])

    def test_event_write_failure_does_not_change_core_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact = Path(tmpdir) / "model_selection.json"

            with patch("ai_workbench_mcp.events.append_response_event", side_effect=OSError("readonly")):
                response = select_model(
                    project="ai_workbench_mcp",
                    task_type="implement",
                    risk="medium",
                    out=artifact,
                    prompt="implement_request_change_request",
                    complexity_score=13,
                )

        self.assertTrue(response["ok"])
        self.assertEqual(response["status"], "selected")
        self.assertEqual(response["artifacts"]["model_selection"], str(artifact))
        self.assertNotIn("events", response["artifacts"])

    def test_select_model_rejects_invalid_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            response = select_model(
                project="ai_workbench_mcp",
                task_type="implement",
                risk="urgent",
                out=Path(tmpdir) / "model_selection.json",
            )

        self.assertEqual(response["operation"], "workbench_select_model")
        self.assertFalse(response["ok"])
        self.assertEqual(response["errors"][0]["code"], "model_selection_failed")
        self.assertIn("risk must be one of", response["errors"][0]["message"])

    def test_validate_run_direct_call_writes_artifact_and_wraps_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            real_subprocess_run = subprocess.run

            def guarded_subprocess_run(*args, **kwargs):
                caller = inspect.stack()[1]
                if Path(caller.filename).name == "core.py":
                    raise AssertionError("core subprocess.run not expected")
                return real_subprocess_run(*args, **kwargs)

            with (
                patch("ai_workbench_mcp.core.run_tool", side_effect=AssertionError("run_tool not expected")),
                patch("ai_workbench_mcp.core.subprocess.run", side_effect=guarded_subprocess_run),
            ):
                response = validate_run(
                    project="ai_workbench_mcp",
                    out_dir=tmpdir,
                    profile="scaffold",
                )
            written = json.loads((Path(tmpdir) / "validation_report.json").read_text(encoding="utf-8"))
            events = read_jsonl(Path(tmpdir) / "events.jsonl")

        self.assertTrue(response["ok"])
        self.assertEqual(response["operation"], "workbench_validate_run")
        self.assertEqual(response["status"], "passed")
        self.assertEqual(response["artifacts"]["validation_report"], str(Path(tmpdir) / "validation_report.json"))
        self.assertEqual(written["overall_status"], "passed")
        self.assertEqual(response["summary"]["project"], "ai_workbench_mcp")
        self.assertEqual(response["summary"]["profile"], "scaffold")
        self.assertTrue(response["summary"]["sign_off_ready"])
        self.assertEqual(response["summary"]["commands_passed"], 12)
        self.assertEqual(response["summary"]["commands_failed"], 0)
        command_names = [command["name"] for command in written["commands_run"]]
        self.assertIn("model_registry_override_support", command_names)
        self.assertIn("event_ledger_import_smoke", command_names)
        self.assertIn("golden_eval_help", command_names)
        self.assertIn("policy_pack_select_help", command_names)
        self.assertIn("codex_live_handoff_help", command_names)
        self.assertIn("codex_live_result_check_help", command_names)
        self.assertEqual(response["summary"]["checks_passed"], 3)
        self.assertEqual(response["summary"]["checks_needs_review"], 0)
        self.assertEqual(response["summary"]["checks_failed"], 0)
        self.assertEqual(response["artifacts"]["events"], str(Path(tmpdir) / "events.jsonl"))
        self.assertEqual(events[0]["operation"], "workbench_validate_run")
        self.assertEqual(events[0]["status"], "passed")

    def test_quality_gate_direct_call_writes_artifact_and_wraps_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            (run_dir / "model_output.md").write_text(
                "\n".join(
                    [
                        "# Model Output",
                        "",
                        "## Captured Response",
                        "",
                        "Summary:",
                        "Implemented a bounded change.",
                        "",
                        "Files touched:",
                        "- tools/example.py",
                        "",
                        "Validation run:",
                        "- pytest -> passed",
                        "",
                        "Risks / follow-ups:",
                        "- None.",
                    ]
                ),
                encoding="utf-8",
            )
            (run_dir / "validation_report.json").write_text(
                json.dumps({"overall_status": "passed", "confidence": 1.0}),
                encoding="utf-8",
            )
            real_subprocess_run = subprocess.run

            def guarded_subprocess_run(*args, **kwargs):
                caller = inspect.stack()[1]
                if Path(caller.filename).name == "core.py":
                    raise AssertionError("core subprocess.run not expected")
                return real_subprocess_run(*args, **kwargs)

            with (
                patch("ai_workbench_mcp.core.run_tool", side_effect=AssertionError("run_tool not expected")),
                patch("ai_workbench_mcp.core.subprocess.run", side_effect=guarded_subprocess_run),
            ):
                response = quality_gate(
                    project="ai_workbench_mcp",
                    run_dir=run_dir,
                    mode="auto",
                    risk="low",
                )
            written = json.loads((run_dir / "revision_decision.json").read_text(encoding="utf-8"))
            events = read_jsonl(run_dir / "events.jsonl")

        self.assertTrue(response["ok"])
        self.assertEqual(response["operation"], "workbench_quality_gate")
        self.assertEqual(response["status"], "accepted")
        self.assertEqual(response["artifacts"]["revision_decision"], str(run_dir / "revision_decision.json"))
        self.assertEqual(written["final_status"], "accepted")
        self.assertEqual(response["summary"]["loop_type"], "none")
        self.assertFalse(response["summary"]["required"])
        self.assertEqual(response["summary"]["accepted_pass"], 1)
        self.assertEqual(response["summary"]["blocking_findings"], 0)
        self.assertEqual(response["summary"]["non_blocking_findings"], 0)
        self.assertEqual(response["artifacts"]["events"], str(run_dir / "events.jsonl"))
        self.assertEqual(events[0]["operation"], "workbench_quality_gate")
        self.assertEqual(events[0]["status"], "accepted")

    def test_analyze_runs_direct_call_writes_artifacts_and_wraps_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            runs_dir = root / "runs"
            run_dir = runs_dir / "run1"
            run_dir.mkdir(parents=True)
            (run_dir / "run_log.jsonl").write_text(
                json.dumps(
                    {
                        "timestamp": "2026-05-12T10:00:00",
                        "model_tier": "local_coding",
                        "decision": "model_response_captured",
                        "prompt": "implement_request_change_request",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "model_selection.json").write_text(
                json.dumps(
                    {
                        "selected_tier": "local_coding",
                        "task_type": "implementation",
                        "risk": "medium",
                        "complexity_band": "moderate",
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "task_metadata.json").write_text(
                json.dumps(
                    {
                        "run_id": "run1",
                        "project": "ai_workbench_mcp",
                        "task_type": "implementation",
                        "prompt": "implement_request_change_request",
                        "recipe": "workbench-engineering-acceptance.yaml",
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "model_output.md").write_text(
                "\n".join(
                    [
                        "# Model Output",
                        "",
                        "## Execution Metadata",
                        "",
                        "- Response Source: `goose`",
                        "- Status: `response_captured`",
                        "",
                        "## Normalized Response",
                        "",
                        "Summary:",
                        "Captured sample response.",
                        "",
                        "Files touched:",
                        "- src/example.py",
                        "",
                        "Validation run:",
                        "- pytest -> passed",
                        "",
                        "Risks / follow-ups:",
                        "- None.",
                    ]
                ),
                encoding="utf-8",
            )
            (run_dir / "validation_report.json").write_text(
                json.dumps(
                    {
                        "overall_status": "passed",
                        "sign_off_ready": True,
                        "confidence": 0.9,
                        "profile": "run_signoff",
                        "missing_context_notes": {"needs_review": [], "info": []},
                    }
                ),
                encoding="utf-8",
            )
            (run_dir / "revision_decision.json").write_text(
                json.dumps({"final_status": "accepted", "loop_type": "none"}),
                encoding="utf-8",
            )
            out_dir = root / "reports"
            real_subprocess_run = subprocess.run

            def guarded_subprocess_run(*args, **kwargs):
                caller = inspect.stack()[1]
                if Path(caller.filename).name == "core.py":
                    raise AssertionError("core subprocess.run not expected")
                return real_subprocess_run(*args, **kwargs)

            with (
                patch("ai_workbench_mcp.core.run_tool", side_effect=AssertionError("run_tool not expected")),
                patch("ai_workbench_mcp.core.subprocess.run", side_effect=guarded_subprocess_run),
            ):
                response = analyze_runs(
                    runs_dir=runs_dir,
                    out_dir=out_dir,
                    evals_dir=root / "evals",
                )
            written = json.loads((out_dir / "run_metrics.json").read_text(encoding="utf-8"))
            events = read_jsonl(out_dir / "events.jsonl")

        self.assertTrue(response["ok"])
        self.assertEqual(response["operation"], "workbench_analyze_runs")
        self.assertEqual(response["status"], "completed")
        self.assertEqual(response["artifacts"]["run_metrics"], str(out_dir / "run_metrics.json"))
        self.assertEqual(response["artifacts"]["run_summary"], str(out_dir / "run_summary.md"))
        self.assertEqual(response["artifacts"]["dashboard"], str(out_dir / "run_dashboard.html"))
        self.assertEqual(written["runs_total"], 1)
        self.assertEqual(written["evidence_scope"], "all")
        self.assertEqual(written["excluded_runs_total"], 0)
        self.assertEqual(
            analytics_contract_projection(written),
            load_contract_fixture("analytics_single_accepted_run_projection.json"),
        )
        self.assertEqual(response["summary"]["runs_total"], 1)
        self.assertEqual(response["summary"]["evidence_scope"], "all")
        self.assertEqual(response["summary"]["runs_passed"], 1)
        self.assertEqual(response["summary"]["runs_failed"], 0)
        self.assertEqual(response["summary"]["runs_needs_review"], 0)
        self.assertEqual(response["summary"]["workflow_signoff_pass_rate"], 1.0)
        self.assertEqual(response["summary"]["average_confidence"], 0.9)
        self.assertEqual(response["artifacts"]["events"], str(out_dir / "events.jsonl"))
        self.assertEqual(events[0]["operation"], "workbench_analyze_runs")
        self.assertEqual(events[0]["status"], "completed")

    def test_analyze_runs_direct_call_accepts_complete_evidence_scope(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            runs_dir = root / "runs"
            run_dir = runs_dir / "tool-smoke"
            run_dir.mkdir(parents=True)
            (run_dir / "run_log.jsonl").write_text(
                json.dumps(
                    {
                        "timestamp": "2026-05-12T10:00:00",
                        "model_tier": "local_coding",
                        "decision": "model_selected",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            (run_dir / "model_selection.json").write_text(
                json.dumps(
                    {
                        "selected_tier": "local_coding",
                        "task_type": "implementation",
                        "risk": "low",
                        "complexity_band": "easy",
                    }
                ),
                encoding="utf-8",
            )
            out_dir = root / "reports"

            response = analyze_runs(
                runs_dir=runs_dir,
                out_dir=out_dir,
                evals_dir=root / "evals",
                evidence_scope="complete",
            )
            written = json.loads((out_dir / "run_metrics.json").read_text(encoding="utf-8"))

        self.assertTrue(response["ok"])
        self.assertEqual(written["evidence_scope"], "complete")
        self.assertEqual(written["runs_total"], 0)
        self.assertEqual(written["excluded_runs_total"], 1)
        self.assertEqual(
            written["excluded_runs_by_reason"],
            {"missing_validation_report": 1, "missing_revision_decision": 1},
        )
        self.assertEqual(response["summary"]["evidence_scope"], "complete")
        self.assertEqual(response["summary"]["excluded_runs_total"], 1)

    def test_run_analysis_file_response_records_dashboard_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            metrics = root / "run_metrics.json"
            summary = root / "run_summary.md"
            dashboard = root / "run_dashboard.html"
            metrics.write_text(json.dumps({"runs_total": 1, "runs_passed": 1}), encoding="utf-8")
            summary.write_text("# Summary\n", encoding="utf-8")
            dashboard.write_text("<!doctype html>\n", encoding="utf-8")

            response = run_analysis_file_response(metrics, summary, dashboard)

        self.assertTrue(response["ok"])
        self.assertEqual(response["artifacts"]["run_metrics"], str(metrics))
        self.assertEqual(response["artifacts"]["run_summary"], str(summary))
        self.assertEqual(response["artifacts"]["dashboard"], str(dashboard))


if __name__ == "__main__":
    unittest.main()
