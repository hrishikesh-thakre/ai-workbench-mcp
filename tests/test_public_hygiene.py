import json
import re
import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
PYPROJECT = ROOT / "pyproject.toml"
SERVER_JSON = ROOT / "server.json"
GITIGNORE = ROOT / ".gitignore"
CI_WORKFLOW = ROOT / ".github" / "workflows" / "ci.yml"
MODEL_REGISTRY_EXAMPLE = ROOT / "configs" / "model_registry.example.yaml"
PYPI_GUIDE = ROOT / "docs" / "publishing" / "pypi.md"
TOPICS_GUIDE = ROOT / "docs" / "github" / "repository-topics.md"
CREATE_ISSUES_GUIDE = ROOT / "docs" / "github" / "create-launch-issues.md"
ACCEPTANCE_CONCEPT = ROOT / "docs" / "concepts" / "how-acceptance-works.md"
ISSUE_DRAFTS_DIR = ROOT / "docs" / "github" / "issue-drafts"
OPERATING_DOCS = [
    ROOT / "docs" / "ai" / "START_HERE.md",
    ROOT / "docs" / "ai" / "DECISIONS.md",
    ROOT / "docs" / "ai" / "PROJECT_MAP.md",
    ROOT / "docs" / "ai" / "ROADMAP_STATUS.md",
]
PUBLIC_ROOTS = [
    ROOT / "README.md",
    ROOT / ".github",
    ROOT / "configs",
    ROOT / "docs",
    ROOT / "evals",
    ROOT / "examples",
    ROOT / "prompts",
    ROOT / "recipes",
    ROOT / "src",
    ROOT / "tools",
]
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}
EXPECTED_MCP_SERVER_NAME = "io.github.hrishikesh-thakre/ai-workbench-mcp"
EXPECTED_PACKAGE_NAME = "ai-workbench-mcp"
EXPECTED_REPOSITORY_URL = "https://github.com/hrishikesh-thakre/ai-workbench-mcp"


def public_files() -> list[Path]:
    files: list[Path] = []
    for root in PUBLIC_ROOTS:
        if root.is_file():
            files.append(root)
            continue
        files.extend(path for path in root.rglob("*") if path.is_file() and path.suffix in TEXT_SUFFIXES)
    return sorted(set(files))


class PublicHygieneTests(unittest.TestCase):
    def test_public_files_do_not_contain_private_paths_or_secret_values(self) -> None:
        forbidden_patterns = [
            r"(?<![A-Za-z])[A-Za-z]:\\",
            r"(?<![A-Za-z])[A-Za-z]:/(?!/)",
            r"\bC:/Users\b",
            r"\bD:/ai-workbench\b",
            r"\bD:\\ai-workbench\b",
            r"\bapi[_-]?key\s*[:=]\s*['\"][^'\"]+",
            r"\btoken\s*=\s*['\"][^'\"]+",
            r"\bsk-[A-Za-z0-9_-]{20,}",
            r"BEGIN (?:RSA |OPENSSH |PRIVATE )?KEY",
        ]

        findings: list[str] = []
        for path in public_files():
            text = path.read_text(encoding="utf-8", errors="replace")
            for pattern in forbidden_patterns:
                if re.search(pattern, text, flags=re.IGNORECASE):
                    findings.append(f"{path.relative_to(ROOT)} matched {pattern}")

        self.assertEqual(findings, [])

    def test_release_notes_do_not_point_to_concrete_local_run_ledgers(self) -> None:
        release_files = sorted((ROOT / "docs" / "releases").glob("*.md"))
        concrete_run_reference = re.compile(r"Run evidence:\s*`runs/[A-Za-z0-9_.-]+/?`")
        findings: list[str] = []

        for path in release_files:
            text = path.read_text(encoding="utf-8")
            for match in concrete_run_reference.finditer(text):
                findings.append(f"{path.relative_to(ROOT)} references {match.group(0)}")

        self.assertEqual(findings, [])

    def test_only_sanitized_sample_runs_are_under_examples(self) -> None:
        sample_runs_dir = ROOT / "examples" / "sample-runs"
        sample_names = sorted(path.name for path in sample_runs_dir.iterdir() if path.is_dir())

        self.assertEqual(
            sample_names,
            [
                "accepted-codex-tiny-python-fix",
                "accepted-docs-only-smoke",
                "accepted-tiny-python-fix",
                "needs-review-test-fix",
            ],
        )

    def test_operating_docs_are_aligned_to_v02_release_candidate_state(self) -> None:
        for path in OPERATING_DOCS:
            with self.subTest(path=path.relative_to(ROOT)):
                text = path.read_text(encoding="utf-8")
                self.assertIn("Status: v0.2 alpha release candidate", text)
                self.assertNotIn("Status: v0.1 alpha baseline", text)

        roadmap = (ROOT / "docs" / "ai" / "ROADMAP_STATUS.md").read_text(encoding="utf-8")
        self.assertIn("Phase 4: v0.2 Recipe And Policy Packs (Release Candidate)", roadmap)
        self.assertIn("Phase 5: Acceptance Analytics (Hardening)", roadmap)
        self.assertIn("routing feedback candidates", roadmap)
        self.assertNotIn("passed 78 tests and 2 subtests", roadmap)
        self.assertNotIn("Phase 4: v0.2 Recipe And Policy Packs (Next)", roadmap)
        self.assertNotIn("Continue v0.2 hardening by adding sanitized sample evidence", roadmap)

    def test_package_version_matches_v02_alpha_release_docs(self) -> None:
        pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        release_note = (ROOT / "docs" / "releases" / "v0.2.0-alpha.md").read_text(encoding="utf-8")

        self.assertEqual(pyproject["build-system"]["build-backend"], "setuptools.build_meta")
        self.assertIn("setuptools>=68", pyproject["build-system"]["requires"])
        self.assertEqual(pyproject["project"]["version"], "0.2.0a0")
        self.assertEqual(pyproject["project"]["license"], "Apache-2.0")
        self.assertEqual(pyproject["project"]["optional-dependencies"]["publish"], ["build", "twine"])
        self.assertEqual(pyproject["tool"]["setuptools"]["packages"]["find"]["where"], ["src"])
        self.assertEqual(pyproject["tool"]["setuptools"]["package-data"]["ai_workbench_mcp"], ["py.typed"])
        self.assertIn("Python package version: `0.2.0a0`", release_note)
        self.assertEqual(
            pyproject["project"]["urls"],
            {
                "Homepage": "https://github.com/hrishikesh-thakre/ai-workbench-mcp",
                "Repository": "https://github.com/hrishikesh-thakre/ai-workbench-mcp",
                "Issues": "https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues",
                "Documentation": "https://github.com/hrishikesh-thakre/ai-workbench-mcp#readme",
            },
        )

    def test_mcp_registry_server_json_is_structurally_prepared(self) -> None:
        self.assertTrue(SERVER_JSON.is_file())
        metadata = json.loads(SERVER_JSON.read_text(encoding="utf-8"))

        for field in ("name", "title", "description", "version", "repository", "packages"):
            self.assertIn(field, metadata)

        self.assertEqual(metadata["name"], EXPECTED_MCP_SERVER_NAME)
        self.assertEqual(metadata["title"], "AI Workbench MCP")
        self.assertIn("Workbench-owned acceptance evidence", metadata["description"])
        self.assertEqual(
            metadata["repository"],
            {
                "url": EXPECTED_REPOSITORY_URL,
                "source": "github",
            },
        )

        packages = metadata["packages"]
        self.assertIsInstance(packages, list)
        self.assertEqual(len(packages), 1)

        package = packages[0]
        for field in ("registryType", "identifier", "version", "transport"):
            self.assertIn(field, package)
        self.assertEqual(package["registryType"], "pypi")
        self.assertEqual(package["identifier"], EXPECTED_PACKAGE_NAME)
        self.assertEqual(package["transport"], {"type": "stdio"})

    def test_mcp_registry_versions_and_readme_marker_are_consistent(self) -> None:
        metadata = json.loads(SERVER_JSON.read_text(encoding="utf-8"))
        pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
        readme_text = README.read_text(encoding="utf-8")
        project_version = pyproject["project"]["version"]
        expected_marker = f"<!-- mcp-name: {metadata['name']} -->"

        self.assertEqual(metadata["version"], project_version)
        self.assertEqual(metadata["packages"][0]["version"], project_version)
        self.assertEqual(metadata["name"], EXPECTED_MCP_SERVER_NAME)
        self.assertIn(expected_marker, readme_text)
        self.assertEqual(readme_text.count("mcp-name:"), 1)

    def test_model_registry_local_override_is_ignored_and_documented(self) -> None:
        gitignore_text = GITIGNORE.read_text(encoding="utf-8")
        example_text = MODEL_REGISTRY_EXAMPLE.read_text(encoding="utf-8")

        self.assertIn("configs/model_registry.local.yaml", gitignore_text)
        self.assertTrue(MODEL_REGISTRY_EXAMPLE.is_file())
        for tier in ("local_coding", "cheap_cloud", "mid_cloud", "frontier"):
            self.assertIn(f"  {tier}:", example_text)
        self.assertIn("deterministic_tool", example_text)
        self.assertIn("human_review", example_text)

    def test_ci_workflow_is_repo_self_validation_gate(self) -> None:
        self.assertTrue(CI_WORKFLOW.is_file())
        workflow = CI_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("permissions:", workflow)
        self.assertIn("contents: read", workflow)
        self.assertIn("timeout-minutes: 15", workflow)
        self.assertIn("ubuntu-latest", workflow)
        self.assertIn('python-version: "3.11"', workflow)
        self.assertIn('python -m pip install -e ".[dev,publish]"', workflow)
        self.assertIn("python -m pytest -q -p no:cacheprovider", workflow)
        self.assertIn(
            "python tools/validate_run.py --project ai_workbench_mcp --profile scaffold --out-dir runs/ci_scaffold",
            workflow,
        )
        self.assertIn("python -m build", workflow)
        self.assertIn("python -m twine check dist/*", workflow)
        self.assertIn("python -m pip install --force-reinstall", workflow)
        self.assertIn("from ai_workbench_mcp import server", workflow)
        self.assertIn("git diff --check", workflow)
        self.assertIn("pull_request:", workflow)
        self.assertIn("push:", workflow)

    def test_publishing_and_launch_docs_record_completed_external_setup(self) -> None:
        gitignore_text = GITIGNORE.read_text(encoding="utf-8")
        pypi_text = PYPI_GUIDE.read_text(encoding="utf-8")
        topics_text = TOPICS_GUIDE.read_text(encoding="utf-8")
        create_issues_text = CREATE_ISSUES_GUIDE.read_text(encoding="utf-8")
        launch_issues_text = (ROOT / "docs" / "github" / "launch-issues.md").read_text(encoding="utf-8")

        self.assertIn("dist/", gitignore_text)
        self.assertIn("has not been published to PyPI yet", pypi_text)
        self.assertIn("code/server only", pypi_text)
        self.assertIn("checked-out repository", pypi_text)
        self.assertIn("python -m build", pypi_text)
        self.assertIn("python -m twine check dist/*", pypi_text)
        self.assertIn("python -m pip install --force-reinstall", pypi_text)
        self.assertIn("Fresh virtual environment smoke", pypi_text)
        self.assertIn("assert shutil.which('ai-workbench-mcp')", pypi_text)
        self.assertIn("Do not run `ai-workbench-mcp` directly as a smoke command.", pypi_text)
        self.assertIn("external_launch_execution_prep.md", pypi_text)
        self.assertIn("python -m pip install -e \".[dev,publish]\"", pypi_text)
        self.assertIn("server.json.version", pypi_text)
        self.assertIn("server.json.packages[0].version", pypi_text)
        self.assertIn("mcp-publisher login", pypi_text)
        self.assertIn("mcp-publisher publish", pypi_text)
        self.assertIn("explicit approval", pypi_text)
        self.assertIn("Do not upload to TestPyPI or PyPI as part of registry metadata prep.", pypi_text)
        self.assertIn("TestPyPI", pypi_text)
        self.assertIn("Only run this after", pypi_text)

        for topic in (
            "goose",
            "mcp",
            "model-context-protocol",
            "ai-agents",
            "agentic-ai",
            "coding-agents",
            "developer-tools",
            "validation",
            "evals",
            "quality-gates",
            "audit-trail",
        ):
            self.assertIn(topic, topics_text)
        self.assertIn("hrishikesh-thakre/ai-workbench-mcp", topics_text)
        self.assertIn("The public GitHub repository has the recommended topics applied.", topics_text)
        self.assertIn("Topics applied: 11", topics_text)
        self.assertIn("recovery/reference guidance only", topics_text)
        self.assertIn("Do not rerun unless recreating the topic setup after checking", topics_text)
        self.assertIn("gh repo edit", topics_text)

        expected_issues = {
            1: (
                "dogfooding: collect 20-50 Goose acceptance runs",
                "dogfooding-collect-goose-runs.md",
            ),
            2: (
                "analytics: promote routing feedback candidates into policy experiments",
                "analytics-routing-feedback-policy-experiments.md",
            ),
            3: (
                "cost evidence: capture provider token and cost metadata",
                "cost-evidence-provider-metadata.md",
            ),
            4: (
                "policy packs: design first-class validation policy metadata",
                "policy-packs-validation-metadata.md",
            ),
            5: (
                "ci: prototype PR acceptance gate",
                "ci-pr-acceptance-gate.md",
            ),
            6: (
                "docs: record a five-minute Goose acceptance demo",
                "docs-five-minute-goose-demo.md",
            ),
        }
        expected_drafts = sorted(draft for _title, draft in expected_issues.values())
        self.assertEqual(sorted(path.name for path in ISSUE_DRAFTS_DIR.glob("*.md")), expected_drafts)
        for issue_number, (issue_title, draft_name) in expected_issues.items():
            issue_link = f"https://github.com/hrishikesh-thakre/ai-workbench-mcp/issues/{issue_number}"
            self.assertIn(f"`#{issue_number}` {issue_title}", create_issues_text)
            self.assertIn(issue_link, create_issues_text)
            self.assertIn(f"`#{issue_number}` {issue_title}", launch_issues_text)
            self.assertIn(issue_link, launch_issues_text)
            self.assertIn(f"docs/github/issue-drafts/{draft_name}", create_issues_text)
        self.assertIn("Do not rerun the creation commands unless recreating after duplicate checks.", create_issues_text)
        self.assertIn("Do not rerun them unless recreating the launch backlog", create_issues_text)
        self.assertIn("gh issue list", create_issues_text)
        self.assertIn("gh issue create", create_issues_text)

    def test_acceptance_concept_guide_locks_mcp_workbench_boundary(self) -> None:
        self.assertTrue(ACCEPTANCE_CONCEPT.is_file())
        text = ACCEPTANCE_CONCEPT.read_text(encoding="utf-8")

        for phrase in (
            "MCP is the connection protocol.",
            "AI Workbench MCP is the tool server.",
            "Acceptance is decided by the selected validation profile and quality gate.",
            "The agent performs. Workbench accepts. MCP connects them.",
        ):
            self.assertIn(phrase, text)

        self.assertIn("MCP connects those pieces. It does not prove correctness", text)
        self.assertIn("A prompt definition-of-done is an instruction to the agent.", text)
        self.assertIn("The acceptance gate runs after the agent acts.", text)
        self.assertIn("claimed changed files must have matching worktree diff evidence", text)
        self.assertIn("AI Workbench MCP does not prove software correctness.", text)
        self.assertIn("It does not replace CI, code review, security review, or human judgment", text)


if __name__ == "__main__":
    unittest.main()
