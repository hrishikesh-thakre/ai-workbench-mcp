import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TINY_EXAMPLE = ROOT / "examples" / "tiny-python-fix"
SAMPLE_RUN = ROOT / "examples" / "sample-runs" / "accepted-tiny-python-fix"
CODEX_SAMPLE_RUN = ROOT / "examples" / "sample-runs" / "accepted-codex-tiny-python-fix"
DOCS_ONLY_SAMPLE_RUN = ROOT / "examples" / "sample-runs" / "accepted-docs-only-smoke"
NEEDS_REVIEW_SAMPLE_RUN = ROOT / "examples" / "sample-runs" / "needs-review-test-fix"
FOCUSED_WORKFLOWS = ROOT / "examples" / "focused-workflows" / "README.md"
SAMPLE_RUNS_README = ROOT / "examples" / "sample-runs" / "README.md"
ANALYTICS_GUIDE = ROOT / "docs" / "analytics" / "acceptance-analytics.md"
EVIDENCE_DASHBOARD_GUIDE = ROOT / "docs" / "analytics" / "evidence-dashboard.md"
EVENT_LEDGER_GUIDE = ROOT / "docs" / "analytics" / "event-ledger.md"
MODEL_REGISTRY_GUIDE = ROOT / "docs" / "configuration" / "model-registry.md"
DOGFOODING_GUIDE = ROOT / "docs" / "dogfooding" / "phase5-dogfooding.md"
GOLDEN_CASE_GUIDE = ROOT / "docs" / "evals" / "golden-case-harness.md"
PR_GATE_GUIDE = ROOT / "docs" / "github" / "pr-gate.md"
LAUNCH_ISSUES = ROOT / "docs" / "github" / "launch-issues.md"
PYPI_GUIDE = ROOT / "docs" / "publishing" / "pypi.md"
TOPICS_GUIDE = ROOT / "docs" / "github" / "repository-topics.md"
CREATE_ISSUES_GUIDE = ROOT / "docs" / "github" / "create-launch-issues.md"
WALKTHROUGH_GUIDE = ROOT / "docs" / "walkthroughs" / "goose-acceptance-demo.md"
CODEX_WALKTHROUGH_GUIDE = ROOT / "docs" / "walkthroughs" / "codex-acceptance-demo.md"
PROOF_PACK = ROOT / "docs" / "proof" / "proof-pack-v0.2.md"
GEMINI_FIXTURE_PROOF = ROOT / "docs" / "proof" / "gemini-fixture-accepted-run.md"
CODEX_SETUP = ROOT / "docs" / "codex" / "setup.md"
CODEX_WORKFLOW = ROOT / "docs" / "codex" / "acceptance-workflow.md"
CODEX_HANDOFF = ROOT / "docs" / "codex" / "live-test-handoff.md"
CODEX_AGENTS = ROOT / "docs" / "codex" / "agents-snippet.md"
CODEX_CLOUD = ROOT / "docs" / "codex" / "cloud-limitations.md"
CODEX_TOOL_SMOKE = ROOT / "examples" / "codex-tool-smoke" / "README.md"
CODEX_ACCEPTANCE_SMOKE = ROOT / "examples" / "codex-acceptance-smoke" / "README.md"
README = ROOT / "README.md"
ACCEPTANCE_CONCEPT = ROOT / "docs" / "concepts" / "how-acceptance-works.md"
START_HERE = ROOT / "docs" / "ai" / "START_HERE.md"
PROJECT_MAP = ROOT / "docs" / "ai" / "PROJECT_MAP.md"
ROADMAP_STATUS = ROOT / "docs" / "ai" / "ROADMAP_STATUS.md"
V02_RELEASE = ROOT / "docs" / "releases" / "v0.2.0-alpha.md"

REQUIRED_SAMPLE_ARTIFACTS = [
    "task_metadata.json",
    "final_prompt.md",
    "model_selection.json",
    "model_output.md",
    "validation_report.json",
    "revision_decision.json",
    "run_log.jsonl",
]


class PublicExamplesTests(unittest.TestCase):
    def test_tiny_python_fix_has_runnable_failing_validation_command(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                str(TINY_EXAMPLE),
                "-p",
                "test_*.py",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 1)
        self.assertIn("FAILED", result.stderr)

    def test_sample_run_contains_required_sanitized_artifacts(self) -> None:
        for sample_run in (SAMPLE_RUN, CODEX_SAMPLE_RUN, DOCS_ONLY_SAMPLE_RUN, NEEDS_REVIEW_SAMPLE_RUN):
            with self.subTest(sample_run=sample_run.name):
                for artifact in REQUIRED_SAMPLE_ARTIFACTS:
                    self.assertTrue((sample_run / artifact).exists(), artifact)

                selection = json.loads((sample_run / "model_selection.json").read_text(encoding="utf-8"))

                self.assertEqual(selection["status"], "selected")

                combined = "\n".join(path.read_text(encoding="utf-8") for path in sample_run.iterdir() if path.is_file())
                self.assertNotIn("D:\\", combined)
                self.assertNotIn("C:\\Users", combined)
                self.assertNotIn("api_key", combined.lower())
                self.assertNotIn("token=", combined.lower())

    def test_accepted_sample_runs_are_accepted(self) -> None:
        for sample_run in (SAMPLE_RUN, CODEX_SAMPLE_RUN, DOCS_ONLY_SAMPLE_RUN):
            with self.subTest(sample_run=sample_run.name):
                report = json.loads((sample_run / "validation_report.json").read_text(encoding="utf-8"))
                decision = json.loads((sample_run / "revision_decision.json").read_text(encoding="utf-8"))

                self.assertEqual(report["overall_status"], "passed")
                self.assertTrue(report["sign_off_ready"])
                self.assertEqual(decision["final_status"], "accepted")

    def test_docs_only_sample_run_uses_focused_prompt_profile_and_policy(self) -> None:
        metadata = json.loads((DOCS_ONLY_SAMPLE_RUN / "task_metadata.json").read_text(encoding="utf-8"))
        report = json.loads((DOCS_ONLY_SAMPLE_RUN / "validation_report.json").read_text(encoding="utf-8"))
        decision = json.loads((DOCS_ONLY_SAMPLE_RUN / "revision_decision.json").read_text(encoding="utf-8"))
        run_log_entries = [
            json.loads(line)
            for line in (DOCS_ONLY_SAMPLE_RUN / "run_log.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        self.assertEqual(metadata["prompt"], "documentation_accuracy_audit")
        self.assertEqual(metadata["recipe"], "workbench-docs-only-acceptance.yaml")
        self.assertEqual(report["profile"], "docs_only")
        self.assertEqual(report["confidence"], 1.0)
        self.assertEqual(decision["final_status"], "accepted")
        self.assertEqual(
            sum(1 for entry in run_log_entries if entry.get("decision") == "model_response_captured"),
            1,
        )
        self.assertTrue(
            any(
                check["name"] == "changed_file_policy" and check["status"] == "passed"
                for check in report["artifact_checks"]
            )
        )

    def test_codex_sample_run_uses_codex_host_metadata_and_accepted_gate(self) -> None:
        metadata = json.loads((CODEX_SAMPLE_RUN / "task_metadata.json").read_text(encoding="utf-8"))
        final_prompt = (CODEX_SAMPLE_RUN / "final_prompt.md").read_text(encoding="utf-8")
        model_output = (CODEX_SAMPLE_RUN / "model_output.md").read_text(encoding="utf-8")
        selection = json.loads((CODEX_SAMPLE_RUN / "model_selection.json").read_text(encoding="utf-8"))
        report = json.loads((CODEX_SAMPLE_RUN / "validation_report.json").read_text(encoding="utf-8"))
        decision = json.loads((CODEX_SAMPLE_RUN / "revision_decision.json").read_text(encoding="utf-8"))

        self.assertEqual(metadata["execution_host"], "codex")
        self.assertEqual(metadata["recipe"], "workbench-engineering-acceptance.yaml")
        self.assertIn("- Execution Host: `codex`", final_prompt)
        self.assertIn("- Mode: `codex`", final_prompt)
        self.assertIn("- Execution Host: `codex`", model_output)
        self.assertIn("- Response Source: `codex`", model_output)
        self.assertEqual(selection["validation_profile"], "tiny_python_fix")
        self.assertEqual(report["profile"], "tiny_python_fix")
        self.assertEqual(report["overall_status"], "passed")
        self.assertTrue(report["sign_off_ready"])
        self.assertEqual(decision["final_status"], "accepted")

    def test_needs_review_sample_run_uses_test_fix_profile_and_revision_required_gate(self) -> None:
        metadata = json.loads((NEEDS_REVIEW_SAMPLE_RUN / "task_metadata.json").read_text(encoding="utf-8"))
        selection = json.loads((NEEDS_REVIEW_SAMPLE_RUN / "model_selection.json").read_text(encoding="utf-8"))
        report = json.loads((NEEDS_REVIEW_SAMPLE_RUN / "validation_report.json").read_text(encoding="utf-8"))
        decision = json.loads((NEEDS_REVIEW_SAMPLE_RUN / "revision_decision.json").read_text(encoding="utf-8"))

        self.assertEqual(metadata["prompt"], "bug_root_cause_investigation")
        self.assertEqual(metadata["recipe"], "workbench-test-fix-acceptance.yaml")
        self.assertEqual(selection["selected_tier"], "frontier")
        self.assertEqual(report["profile"], "test_fix")
        self.assertEqual(report["overall_status"], "failed")
        self.assertFalse(report["sign_off_ready"])
        self.assertEqual(decision["final_status"], "revision_required")
        self.assertTrue(decision["blocking_findings"])
        self.assertTrue(
            any(
                command["name"] == "full_test_suite" and command["status"] == "failed"
                for command in report["commands_run"]
            )
        )

    def test_readme_product_page_references_quickstart_tools_recipe_and_sample_run(self) -> None:
        text = README.read_text(encoding="utf-8")

        self.assertIn("Acceptance gates for AI coding-agent runs.", text)
        self.assertIn("Works with Goose today. Designed as a host-agnostic acceptance layer", text)
        self.assertIn("## Before", text)
        self.assertIn('The agent says: "Done."', text)
        self.assertIn("## After", text)
        self.assertIn("AI Workbench shows:", text)
        self.assertLess(text.index("runs/example/"), text.index("## 5-Minute Quickstart"))
        self.assertIn("task_metadata.json", text)
        self.assertIn("validation_report.json", text)
        self.assertIn("revision_decision.json", text)
        self.assertIn("evidence-backed accepted runs", text)
        self.assertIn("## 5-Minute Quickstart", text)
        self.assertIn("## What MCP Does And Does Not Do", text)
        self.assertIn("## Prompt DoD vs Acceptance Gate", text)
        self.assertIn("## What Decides Acceptance", text)
        self.assertIn("MCP is the connection protocol.", text)
        self.assertIn("AI Workbench MCP is the tool server.", text)
        self.assertIn("Acceptance is decided by the selected validation profile and quality gate.", text)
        self.assertIn("The agent performs. Workbench accepts. MCP connects them.", text)
        self.assertIn("docs/concepts/how-acceptance-works.md", text)
        self.assertIn("## Six MCP Tools", text)
        self.assertIn("## Workflow", text)
        self.assertIn("workbench_open_run", text)
        self.assertIn("workbench_select_model", text)
        self.assertIn("workbench_record_execution", text)
        self.assertIn("workbench_validate_run", text)
        self.assertIn("workbench_quality_gate", text)
        self.assertIn("workbench_analyze_runs", text)
        self.assertIn("recipes/workbench-engineering-acceptance.yaml", text)
        self.assertIn("recipes/workbench-mcp-tool-smoke.yaml", text)
        self.assertIn("examples/goose-tool-smoke", text)
        self.assertIn("docs/codex/setup.md", text)
        self.assertIn("docs/codex/acceptance-workflow.md", text)
        self.assertIn("docs/codex/agents-snippet.md", text)
        self.assertIn("docs/codex/cloud-limitations.md", text)
        self.assertIn("docs/codex/live-test-handoff.md", text)
        self.assertIn("checks the resulting Codex evidence folders", text)
        self.assertIn("docs/walkthroughs/codex-acceptance-demo.md", text)
        self.assertIn("examples/codex-tool-smoke", text)
        self.assertIn("examples/codex-acceptance-smoke", text)
        self.assertIn('execution_host="codex"', text)
        self.assertIn('response_source="codex"', text)
        self.assertIn("examples/focused-workflows", text)
        self.assertIn("examples/sample-runs/accepted-tiny-python-fix", text)
        self.assertIn("examples/sample-runs/accepted-codex-tiny-python-fix", text)
        self.assertIn("examples/sample-runs/accepted-docs-only-smoke", text)
        self.assertIn("examples/sample-runs/needs-review-test-fix", text)
        self.assertIn("docs/proof/gemini-fixture-accepted-run.md", text)
        self.assertIn("docs/analytics/acceptance-analytics.md", text)
        self.assertIn("docs/analytics/event-ledger.md", text)
        self.assertIn("docs/configuration/model-registry.md", text)
        self.assertIn("docs/dogfooding/phase5-dogfooding.md", text)
        self.assertIn("docs/github/pr-gate.md", text)
        self.assertIn("docs/github/launch-issues.md", text)
        self.assertIn("recipes/workbench-docs-only-acceptance.yaml", text)
        self.assertIn("recipes/workbench-python-package-maintenance.yaml", text)
        self.assertIn("recipes/workbench-test-fix-acceptance.yaml", text)
        self.assertIn("low_risk_coding", text)

    def test_goose_tool_smoke_documents_slow_local_model_path(self) -> None:
        text = (ROOT / "examples" / "goose-tool-smoke" / "README.md").read_text(encoding="utf-8")

        self.assertIn("workbench_open_run", text)
        self.assertIn("workbench_select_model", text)
        self.assertIn("workbench-mcp-tool-smoke.yaml", text)
        self.assertIn("--max-turns 4", text)
        self.assertIn("slow", text.lower())

    def test_focused_workflows_document_v02_recipe_commands(self) -> None:
        text = FOCUSED_WORKFLOWS.read_text(encoding="utf-8")

        self.assertIn("Focused v0.2 Workflows", text)
        self.assertIn("workbench-docs-only-acceptance.yaml", text)
        self.assertIn("workbench-python-package-maintenance.yaml", text)
        self.assertIn("workbench-test-fix-acceptance.yaml", text)
        self.assertIn("workbench-engineering-acceptance.yaml", text)
        self.assertIn("docs_only", text)
        self.assertIn("python_package_maintenance", text)
        self.assertIn("test_fix", text)
        self.assertIn("low_risk_coding", text)
        self.assertIn("Do not commit `runs/`", text)

    def test_sample_runs_readme_and_analytics_guide_document_phase5_reports(self) -> None:
        sample_text = SAMPLE_RUNS_README.read_text(encoding="utf-8")
        guide_text = ANALYTICS_GUIDE.read_text(encoding="utf-8")
        dashboard_guide_text = EVIDENCE_DASHBOARD_GUIDE.read_text(encoding="utf-8")
        event_guide_text = EVENT_LEDGER_GUIDE.read_text(encoding="utf-8")
        model_registry_text = MODEL_REGISTRY_GUIDE.read_text(encoding="utf-8")
        dogfooding_text = DOGFOODING_GUIDE.read_text(encoding="utf-8")
        golden_case_text = GOLDEN_CASE_GUIDE.read_text(encoding="utf-8")
        pr_gate_text = PR_GATE_GUIDE.read_text(encoding="utf-8")
        launch_text = LAUNCH_ISSUES.read_text(encoding="utf-8")
        pypi_text = PYPI_GUIDE.read_text(encoding="utf-8")
        topics_text = TOPICS_GUIDE.read_text(encoding="utf-8")
        create_issues_text = CREATE_ISSUES_GUIDE.read_text(encoding="utf-8")
        walkthrough_text = WALKTHROUGH_GUIDE.read_text(encoding="utf-8")
        codex_walkthrough_text = CODEX_WALKTHROUGH_GUIDE.read_text(encoding="utf-8")
        readme_text = README.read_text(encoding="utf-8")
        concept_text = ACCEPTANCE_CONCEPT.read_text(encoding="utf-8")
        start_here_text = START_HERE.read_text(encoding="utf-8")
        project_map_text = PROJECT_MAP.read_text(encoding="utf-8")
        roadmap_text = ROADMAP_STATUS.read_text(encoding="utf-8")
        proof_pack_text = PROOF_PACK.read_text(encoding="utf-8")
        gemini_proof_text = GEMINI_FIXTURE_PROOF.read_text(encoding="utf-8")

        self.assertIn("needs-review-test-fix", sample_text)
        self.assertIn("accepted-codex-tiny-python-fix", sample_text)
        self.assertIn("docs/analytics/acceptance-analytics.md", sample_text)
        self.assertIn("docs/analytics/acceptance-analytics.md", readme_text)
        self.assertIn("docs/analytics/acceptance-analytics.md", start_here_text)
        self.assertIn("docs/analytics/evidence-dashboard.md", sample_text)
        self.assertIn("docs/analytics/evidence-dashboard.md", readme_text)
        self.assertIn("docs/analytics/evidence-dashboard.md", start_here_text)
        self.assertIn("docs/analytics/evidence-dashboard.md", project_map_text)
        self.assertIn("docs/analytics/event-ledger.md", readme_text)
        self.assertIn("docs/analytics/event-ledger.md", start_here_text)
        self.assertIn("docs/analytics/event-ledger.md", project_map_text)
        self.assertIn("docs/evals/golden-case-harness.md", sample_text)
        self.assertIn("docs/evals/golden-case-harness.md", readme_text)
        self.assertIn("docs/evals/golden-case-harness.md", start_here_text)
        self.assertIn("docs/evals/golden-case-harness.md", project_map_text)
        self.assertIn("docs/configuration/model-registry.md", readme_text)
        self.assertIn("docs/configuration/model-registry.md", start_here_text)
        self.assertIn("docs/github/pr-gate.md", readme_text)
        self.assertIn("docs/github/pr-gate.md", start_here_text)
        self.assertIn("docs/dogfooding/phase5-dogfooding.md", sample_text)
        self.assertIn("docs/dogfooding/phase5-dogfooding.md", readme_text)
        self.assertIn("docs/dogfooding/phase5-dogfooding.md", start_here_text)
        self.assertIn("docs/github/launch-issues.md", readme_text)
        self.assertIn("docs/github/launch-issues.md", start_here_text)
        self.assertIn("docs/publishing/pypi.md", readme_text)
        self.assertIn("docs/publishing/pypi.md", start_here_text)
        self.assertIn("docs/publishing/pypi.md", project_map_text)
        self.assertIn("docs/concepts/how-acceptance-works.md", readme_text)
        self.assertIn("docs/concepts/how-acceptance-works.md", start_here_text)
        self.assertIn("docs/concepts/how-acceptance-works.md", project_map_text)
        self.assertIn("docs/concepts/how-acceptance-works.md", roadmap_text)
        for required_phrase in (
            "MCP is the connection protocol.",
            "AI Workbench MCP is the tool server.",
            "Acceptance is decided by the selected validation profile and quality gate.",
            "The agent performs. Workbench accepts. MCP connects them.",
        ):
            self.assertIn(required_phrase, readme_text)
            self.assertIn(required_phrase, concept_text)
            self.assertIn(required_phrase, walkthrough_text)
        self.assertIn("Prompt DoD vs Acceptance Gate", concept_text)
        self.assertIn("does not prove software correctness", concept_text)
        self.assertIn("does not replace CI, code review, security review, or human judgment", concept_text)
        self.assertIn("docs/github/repository-topics.md", readme_text)
        self.assertIn("docs/github/create-launch-issues.md", readme_text)
        self.assertIn("docs/walkthroughs/goose-acceptance-demo.md", readme_text)
        self.assertIn("docs/walkthroughs/goose-acceptance-demo.md", start_here_text)
        self.assertIn("docs/walkthroughs/goose-acceptance-demo.md", project_map_text)
        self.assertIn("recording-ready 3-5 minute public demo runbook", readme_text)
        self.assertIn("recording-ready public demo runbook", start_here_text)
        self.assertIn("Recording-ready public Goose acceptance demo walkthrough", project_map_text)
        self.assertIn("recording-ready demo walkthrough", roadmap_text)
        for stale_phrase in (
            "public demo script skeleton",
            "demo walkthrough skeleton",
            "skeleton for a 3-5 minute public demo",
        ):
            self.assertNotIn(stale_phrase, readme_text)
            self.assertNotIn(stale_phrase, start_here_text)
            self.assertNotIn(stale_phrase, project_map_text)
            self.assertNotIn(stale_phrase, roadmap_text)
            self.assertNotIn(stale_phrase, walkthrough_text)
        self.assertIn("docs/walkthroughs/codex-acceptance-demo.md", readme_text)
        self.assertIn("docs/walkthroughs/codex-acceptance-demo.md", start_here_text)
        self.assertIn("docs/walkthroughs/codex-acceptance-demo.md", project_map_text)
        self.assertIn("docs/proof/gemini-fixture-accepted-run.md", readme_text)
        self.assertIn("docs/proof/gemini-fixture-accepted-run.md", proof_pack_text)
        self.assertIn("gemini_oauth / gemini-3-flash-preview", gemini_proof_text)
        self.assertIn("fixture_repair_proof", gemini_proof_text)
        self.assertIn("changed_file_policy = passed", gemini_proof_text)
        self.assertIn("full_test_suite command = absent", gemini_proof_text)
        self.assertIn("Isolated analytics", gemini_proof_text)
        self.assertIn("Do not change routing policy from this proof alone", gemini_proof_text)
        self.assertIn("--runs-dir examples/sample-runs", guide_text)
        self.assertIn("run_metrics.json", guide_text)
        self.assertIn("run_summary.md", guide_text)
        self.assertIn("run_dashboard.html", guide_text)
        self.assertIn("routing_feedback_candidates", guide_text)
        self.assertIn("Advisory Routing Feedback", guide_text)
        self.assertIn("source_invalid", guide_text)
        self.assertIn("does not mutate `selected_tier`", guide_text)
        self.assertIn("Cost tracking is optional provider metadata", guide_text)
        self.assertIn("run_dashboard.html", dashboard_guide_text)
        self.assertIn("does not embed raw model output", dashboard_guide_text)
        self.assertIn("relative path", dashboard_guide_text)
        self.assertIn("tools/golden_eval.py", golden_case_text)
        self.assertIn("Valid scoring failures", golden_case_text)
        self.assertIn("does not call providers", golden_case_text)
        self.assertIn("events.jsonl", event_guide_text)
        self.assertIn("best-effort and non-fatal", event_guide_text)
        self.assertIn("should stay local", event_guide_text)
        self.assertIn("not required sign-off artifacts", event_guide_text)
        self.assertIn("configs/model_registry.local.yaml", model_registry_text)
        self.assertIn("dictionaries merge recursively", model_registry_text)
        self.assertIn("selector reference", model_registry_text.lower())
        self.assertIn("does not record provider credentials", model_registry_text)
        self.assertIn("CI gate prototype", pr_gate_text)
        self.assertIn("repo self-validation gate", pr_gate_text)
        self.assertIn("Semantic PR acceptance comes later", pr_gate_text)
        self.assertIn("does not run live Goose", pr_gate_text)
        self.assertIn("git diff --check", pr_gate_text)
        self.assertIn("20-50 real Goose acceptance runs", dogfooding_text)
        self.assertIn("runs/dogfood-batchN", dogfooding_text)
        self.assertIn("dogfood-YYYYMMDD-<short-task-slug>", dogfooding_text)
        self.assertIn("docs/dogfooding/phase5-batch1-report.md", dogfooding_text)
        self.assertIn("docs/dogfooding/phase5-batch2-stage-a-report.md", dogfooding_text)
        self.assertIn("docs/dogfooding/phase5-batch2-stage-b-report.md", dogfooding_text)
        self.assertIn("focused profiles block no-op or underreported changed-file claims", dogfooding_text)
        self.assertIn("Do not analyze the whole `runs/` directory", dogfooding_text)
        self.assertIn("routing_feedback_candidates", dogfooding_text)
        self.assertIn("does not change the selected tier", dogfooding_text)
        self.assertIn("command_failed:full_test_suite", dogfooding_text)
        self.assertIn("Dogfood Batch 2", roadmap_text)
        self.assertIn("exact-diff validation blocks no-op and underreported changed-file claims", roadmap_text)
        self.assertIn("docs/dogfooding/phase5-batch2-stage-b-report.md", roadmap_text)
        self.assertIn("provider-backed or stronger-model Goose runs", roadmap_text)
        self.assertIn("dogfooding: collect 20-50 Goose acceptance runs", launch_text)
        self.assertIn("analytics: promote routing feedback candidates", launch_text)
        self.assertIn("cost evidence: capture provider token and cost metadata", launch_text)
        self.assertIn("ci: prototype PR acceptance gate", launch_text)
        self.assertNotIn("before the v0.1 alpha announcement", launch_text)
        self.assertIn("published to PyPI as `ai-workbench-mcp==0.2.0a0`", pypi_text)
        self.assertIn("code/server only", pypi_text)
        self.assertIn("python -m twine check dist/*", pypi_text)
        self.assertIn("TestPyPI dry run completed for `ai-workbench-mcp==0.2.0a0`", pypi_text)
        self.assertIn("https://test.pypi.org/project/ai-workbench-mcp/0.2.0a0/", pypi_text)
        self.assertIn("PyPI release completed for `ai-workbench-mcp==0.2.0a0`", pypi_text)
        self.assertIn("https://pypi.org/project/ai-workbench-mcp/0.2.0a0/", pypi_text)
        self.assertIn('"ai-workbench-mcp==0.2.0a0"', pypi_text)
        self.assertIn("python -m pip install ai-workbench-mcp==0.2.0a0", pypi_text)
        self.assertIn("MCP Registry publication completed for `io.github.hrishikesh-thakre/ai-workbench-mcp`", pypi_text)
        self.assertIn("https://registry.modelcontextprotocol.io/v0.1/servers?search=io.github.hrishikesh-thakre%2Fai-workbench-mcp", pypi_text)
        self.assertNotIn("MCP Registry submission remains pending.", pypi_text)
        self.assertNotIn("has not been published to PyPI yet", pypi_text)
        self.assertNotIn("Real PyPI remains pending.", pypi_text)
        self.assertIn("model-context-protocol", topics_text)
        self.assertIn("The public GitHub repository has the recommended topics applied.", topics_text)
        self.assertIn("Topics applied: 11", topics_text)
        self.assertIn("Do not rerun unless recreating the topic setup after checking", topics_text)
        self.assertIn("gh repo edit", topics_text)
        for issue_number, issue_title in (
            (1, "dogfooding: collect 20-50 Goose acceptance runs"),
            (2, "analytics: promote routing feedback candidates into policy experiments"),
            (3, "cost evidence: capture provider token and cost metadata"),
            (4, "policy packs: design first-class validation policy metadata"),
            (5, "ci: prototype PR acceptance gate"),
            (6, "docs: record a five-minute Goose acceptance demo"),
        ):
            issue_link = f"https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/{issue_number}"
            self.assertIn(f"`#{issue_number}` {issue_title}", launch_text)
            self.assertIn(f"`#{issue_number}` {issue_title}", create_issues_text)
            self.assertIn(issue_link, launch_text)
            self.assertIn(issue_link, create_issues_text)
        self.assertIn("Do not rerun the creation commands unless recreating after duplicate checks.", create_issues_text)
        self.assertIn("gh issue list", create_issues_text)
        self.assertIn("gh issue create", create_issues_text)
        self.assertIn("GitHub launch setup", roadmap_text)
        self.assertIn("launch issues `#1`-`#6` are open with public links", roadmap_text)
        self.assertIn("Goose Acceptance Demo Walkthrough", walkthrough_text)
        self.assertIn("recording-ready runbook", walkthrough_text)
        self.assertIn("sample-only path", walkthrough_text)
        self.assertIn("optional live Goose path", walkthrough_text)
        self.assertIn(
            "Do not show private run folders, provider credentials, raw provider logs, local absolute paths, or unreviewed `runs/` evidence.",
            walkthrough_text,
        )
        self.assertIn("goose configure", walkthrough_text)
        self.assertIn("validation_report.json", walkthrough_text)
        self.assertIn("revision_decision.json", walkthrough_text)
        self.assertIn("accepted-tiny-python-fix", walkthrough_text)
        self.assertIn("accepted-docs-only-smoke", walkthrough_text)
        self.assertIn("needs-review-test-fix", walkthrough_text)
        self.assertIn("The prompt can describe done, but the prompt does not enforce done.", walkthrough_text)
        self.assertIn('final_status="revision_required"', walkthrough_text)
        self.assertIn("review-required", walkthrough_text)
        self.assertIn("run_dashboard.html", walkthrough_text)
        self.assertIn("does not embed raw provider logs", walkthrough_text)
        self.assertIn("tools/golden_eval.py", walkthrough_text)
        self.assertIn("AI Workbench MCP does not prove software correctness.", walkthrough_text)
        self.assertIn("It does not replace CI, code review, security review, or human judgment.", walkthrough_text)
        self.assertIn("MCP does not decide acceptance; Workbench validation profiles and quality gates do.", walkthrough_text)
        self.assertIn("Do not commit `runs/demo-tiny-python-fix/`", walkthrough_text)
        self.assertIn("Codex Acceptance Demo Walkthrough", codex_walkthrough_text)
        self.assertIn("Do not run `ai-workbench-mcp` directly", codex_walkthrough_text)
        self.assertIn("ask Codex to launch another Codex session", codex_walkthrough_text)
        self.assertIn("runs/codex-local-demo/tool-smoke", codex_walkthrough_text)
        self.assertIn("runs/codex-local-demo/tiny-python-fix", codex_walkthrough_text)
        self.assertIn("--runs-dir runs/codex-local-demo", codex_walkthrough_text)
        self.assertIn("execution_host_counts", codex_walkthrough_text)
        self.assertIn("docs/codex/setup.md", readme_text)
        self.assertIn("docs/codex/setup.md", start_here_text)
        self.assertIn("docs/codex/live-test-handoff.md", readme_text)
        self.assertIn("docs/codex/live-test-handoff.md", start_here_text)
        self.assertIn("docs/codex/", project_map_text)
        self.assertIn("examples/sample-runs/accepted-codex-tiny-python-fix", CODEX_WORKFLOW.read_text(encoding="utf-8"))

    def test_codex_docs_and_examples_document_local_ide_lifecycle(self) -> None:
        docs_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (CODEX_SETUP, CODEX_WORKFLOW, CODEX_HANDOFF, CODEX_AGENTS, CODEX_CLOUD, CODEX_WALKTHROUGH_GUIDE)
        )
        examples_text = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (CODEX_TOOL_SMOKE, CODEX_ACCEPTANCE_SMOKE)
        )

        self.assertIn("ai-workbench-mcp", docs_text)
        self.assertIn("one shared MCP server", docs_text)
        self.assertIn('execution_host="codex"', docs_text)
        self.assertIn('response_source="codex"', docs_text)
        self.assertIn("Codex cloud", docs_text)
        self.assertIn("exported, committed, uploaded, or summarized", docs_text)
        self.assertIn("foreground stdio-server loops", docs_text)
        self.assertIn("docs/walkthroughs/codex-acceptance-demo.md", docs_text)
        self.assertIn("READY: Start Codex now", docs_text)
        self.assertIn("exact result-check command", docs_text)
        self.assertIn("Analyze only the isolated live-test parent", docs_text)
        self.assertIn("tools/codex_live_test_handoff.py", docs_text)
        self.assertIn("tools/check_codex_live_result.py", docs_text)
        self.assertIn("workbench_open_run", examples_text)
        self.assertIn("workbench_select_model", examples_text)
        self.assertIn("workbench_record_execution", examples_text)
        self.assertIn("workbench_validate_run", examples_text)
        self.assertIn("workbench_quality_gate", examples_text)
        self.assertIn("workbench_analyze_runs", examples_text)
        self.assertIn('response_source="codex"', examples_text)
        self.assertIn("fixture_repair_proof", docs_text)
        self.assertIn("fixture_repair_proof", examples_text)
        self.assertIn("task_test_command", docs_text)
        self.assertIn("task_test_command", examples_text)
        self.assertIn("changed_file_policy", docs_text)
        self.assertIn("changed_file_policy", examples_text)
        self.assertIn("full_test_suite", docs_text)
        self.assertIn("full_test_suite", examples_text)
        self.assertIn(
            'task="Fix examples/tiny-python-fix/calculator.py so python -m unittest discover -s examples/tiny-python-fix -p test_*.py passes."',
            docs_text,
        )
        self.assertIn(
            'task="Fix examples/tiny-python-fix/calculator.py so python -m unittest discover -s examples/tiny-python-fix -p test_*.py passes."',
            examples_text,
        )
        self.assertIn('response_text="Summary:', docs_text)
        self.assertIn('response_text="Summary:', examples_text)
        self.assertIn('out_dir="runs/codex-local-demo/tiny-python-fix"', docs_text)
        self.assertIn('out_dir="runs/codex-smoke/tiny-python-fix"', examples_text)
        self.assertIn('run_dir="runs/codex-local-demo/tiny-python-fix"', docs_text)
        self.assertIn('run_dir="runs/codex-smoke/tiny-python-fix"', examples_text)

    def test_v02_release_notes_document_focused_profiles_and_verification(self) -> None:
        text = V02_RELEASE.read_text(encoding="utf-8")

        self.assertIn("v0.2.0-alpha", text)
        self.assertIn("workbench_open_run", text)
        self.assertIn("workbench_analyze_runs", text)
        self.assertIn("workbench-docs-only-acceptance.yaml", text)
        self.assertIn("workbench-python-package-maintenance.yaml", text)
        self.assertIn("workbench-test-fix-acceptance.yaml", text)
        self.assertIn("docs_only", text)
        self.assertIn("python_package_maintenance", text)
        self.assertIn("test_fix", text)
        self.assertIn("low_risk_coding", text)
        self.assertIn("Goose focused docs-only six-tool smoke", text)
        self.assertIn("examples/sample-runs/accepted-docs-only-smoke", text)
        self.assertIn("quality gate accepted", text)
        self.assertIn("python -m pytest -q -p no:cacheprovider", text)
        self.assertIn("--profile scaffold", text)
        self.assertIn("Full sign-off profiles", text)
        self.assertIn("--changed-files README.md docs/ai/ROADMAP_STATUS.md", text)


if __name__ == "__main__":
    unittest.main()
