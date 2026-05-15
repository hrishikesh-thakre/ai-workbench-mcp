import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

from ai_workbench_mcp.tools.config_loader import load_simple_yaml

RECIPES_DIR = ROOT / "recipes"
RECIPE_PATH = ROOT / "recipes" / "workbench-engineering-acceptance.yaml"
TOOL_SMOKE_RECIPE_PATH = ROOT / "recipes" / "workbench-mcp-tool-smoke.yaml"
DOCS_ONLY_RECIPE_PATH = ROOT / "recipes" / "workbench-docs-only-acceptance.yaml"
PYTHON_PACKAGE_RECIPE_PATH = ROOT / "recipes" / "workbench-python-package-maintenance.yaml"
TEST_FIX_RECIPE_PATH = ROOT / "recipes" / "workbench-test-fix-acceptance.yaml"
VALIDATION_PROFILES_PATH = ROOT / "configs" / "validation_profiles.yaml"
FULL_ACCEPTANCE_TOOLS = [
    "workbench_open_run",
    "workbench_select_model",
    "workbench_record_execution",
    "workbench_validate_run",
    "workbench_quality_gate",
    "workbench_analyze_runs",
]


def recipe_files() -> list[Path]:
    return sorted(path for path in RECIPES_DIR.glob("workbench-*.yaml") if path.is_file())


def validation_profiles() -> dict[str, object]:
    raw_data = load_simple_yaml(VALIDATION_PROFILES_PATH)
    profiles = raw_data.get("profiles", {})
    if not isinstance(profiles, dict):
        raise AssertionError("configs/validation_profiles.yaml must define a profiles mapping")
    return profiles


def recipe_parameter_default(text: str, key: str) -> str | None:
    marker = f"  - key: {key}\n"
    start = text.find(marker)
    if start == -1:
        return None
    block_start = start + len(marker)
    next_parameter = text.find("\n  - key:", block_start)
    extensions = text.find("\nextensions:", block_start)
    block_end_candidates = [index for index in (next_parameter, extensions) if index != -1]
    block_end = min(block_end_candidates) if block_end_candidates else len(text)
    block = text[block_start:block_end]
    match = re.search(r'(?m)^\s{4}default:\s+"?([^"\n]+)"?\s*$', block)
    return match.group(1) if match else None


class WorkbenchRecipeTests(unittest.TestCase):
    def test_recipe_declares_workbench_mcp_extension_and_tools(self) -> None:
        text = RECIPE_PATH.read_text(encoding="utf-8")

        self.assertIn('title: "Workbench Engineering Acceptance"', text)
        self.assertIn("cmd: \"ai-workbench-mcp\"", text)
        self.assertIn('name: "AI Workbench MCP"', text)
        self.assertIn('type: stdio', text)
        self.assertIn('timeout: 300', text)
        self.assertIn('- "workbench_open_run"', text)
        self.assertIn('- "workbench_select_model"', text)
        self.assertIn('- "workbench_record_execution"', text)
        self.assertIn('- "workbench_validate_run"', text)
        self.assertIn('- "workbench_quality_gate"', text)
        self.assertIn('- "workbench_analyze_runs"', text)

    def test_recipe_parameters_cover_acceptance_workflow_inputs(self) -> None:
        text = RECIPE_PATH.read_text(encoding="utf-8")

        for key in (
            "project",
            "run_dir",
            "task",
            "task_type",
            "risk",
            "validation_strength",
            "validation_profile",
            "routing_feedback_path",
            "prompt",
            "complexity_score",
        ):
            self.assertIn(f"key: {key}", text)

    def test_recipe_instructions_call_tools_in_acceptance_order(self) -> None:
        text = RECIPE_PATH.read_text(encoding="utf-8")
        positions = [text.index(tool) for tool in FULL_ACCEPTANCE_TOOLS]

        self.assertEqual(positions, sorted(positions))
        self.assertIn("Do not claim the run is accepted", text)
        self.assertIn("deterministic validation and the quality gate", text)
        self.assertIn("Call workbench_record_execution exactly once", text)
        self.assertIn("do not call workbench_record_execution again", text)
        self.assertIn('status="response_captured"', text)

    def test_tool_smoke_recipe_is_bounded_to_open_and_select(self) -> None:
        text = TOOL_SMOKE_RECIPE_PATH.read_text(encoding="utf-8")

        self.assertIn('title: "Workbench MCP Tool Smoke"', text)
        self.assertIn("cmd: \"ai-workbench-mcp\"", text)
        self.assertIn('- "workbench_open_run"', text)
        self.assertIn('- "workbench_select_model"', text)
        self.assertIn("Call exactly these two tools", text)
        self.assertIn("Do not edit tracked files", text)
        self.assertNotIn('- "workbench_record_execution"', text)
        self.assertNotIn('- "workbench_validate_run"', text)
        self.assertNotIn('- "workbench_quality_gate"', text)
        self.assertNotIn('- "workbench_analyze_runs"', text)


class WorkbenchRecipeDiscoveryTests(unittest.TestCase):
    def test_workbench_recipes_are_folder_discoverable(self) -> None:
        files = recipe_files()
        names = {path.name for path in files}

        self.assertIn("workbench-engineering-acceptance.yaml", names)
        self.assertIn("workbench-mcp-tool-smoke.yaml", names)
        self.assertIn("workbench-docs-only-acceptance.yaml", names)
        self.assertIn("workbench-python-package-maintenance.yaml", names)
        self.assertIn("workbench-test-fix-acceptance.yaml", names)

        for recipe_path in files:
            text = recipe_path.read_text(encoding="utf-8")
            with self.subTest(recipe=recipe_path.name):
                self.assertRegex(text, r'(?m)^version: "1\.0\.0"$')
                self.assertRegex(text, r'(?m)^title: ".+"$')
                self.assertIn("parameters:", text)
                self.assertIn("extensions:", text)
                self.assertIn("instructions: |", text)
                self.assertIn('cmd: "ai-workbench-mcp"', text)
                self.assertIn('name: "AI Workbench MCP"', text)
                self.assertIn("available_tools:", text)
                self.assertIn(f'recipe="{recipe_path.name}"', text)

    def test_validation_recipes_reference_discoverable_policy_profiles(self) -> None:
        profiles = validation_profiles()

        for recipe_path in recipe_files():
            text = recipe_path.read_text(encoding="utf-8")
            if "workbench_validate_run" not in text:
                continue

            with self.subTest(recipe=recipe_path.name):
                default_profile = recipe_parameter_default(text, "validation_profile")
                self.assertIsNotNone(default_profile)
                self.assertIn(default_profile, profiles)
                self.assertIn('profile="{{ validation_profile }}"', text)
                self.assertIn('validation_profile="{{ validation_profile }}"', text)
                self.assertIn('routing_feedback_path="{{ routing_feedback_path }}"', text)

    def test_validation_policy_profiles_are_discoverable(self) -> None:
        profiles = validation_profiles()

        self.assertIn("scaffold", profiles)
        self.assertIn("run_signoff", profiles)
        self.assertIn("docs_only", profiles)
        self.assertIn("python_package_maintenance", profiles)
        self.assertIn("test_fix", profiles)
        self.assertIn("low_risk_coding", profiles)

        for profile_name, profile_data in profiles.items():
            with self.subTest(profile=profile_name):
                self.assertIsInstance(profile_data, dict)
                description = profile_data.get("description")
                self.assertIsInstance(description, str)
                self.assertTrue(description.strip())

                commands = profile_data.get("commands")
                self.assertIsInstance(commands, list)
                self.assertGreater(len(commands), 0)

                command_names: set[str] = set()
                for command in commands:
                    self.assertIsInstance(command, dict)
                    name = command.get("name")
                    self.assertIsInstance(name, str)
                    self.assertTrue(name.strip())
                    self.assertNotIn(name, command_names)
                    command_names.add(name)

                    self.assertIsInstance(command.get("command"), str)
                    self.assertTrue(str(command.get("command")).strip())
                    self.assertIsInstance(command.get("cwd"), str)
                    self.assertIsInstance(command.get("required"), bool)
                    self.assertIsInstance(command.get("weight"), (int, float))
                    self.assertNotIsInstance(command.get("weight"), bool)

    def test_v02_acceptance_profiles_require_evidence_artifacts(self) -> None:
        profiles = validation_profiles()
        profile_names = {
            "docs_only",
            "python_package_maintenance",
            "test_fix",
            "low_risk_coding",
        }

        for profile_name in profile_names:
            profile_data = profiles[profile_name]
            with self.subTest(profile=profile_name):
                self.assertEqual(
                    profile_data.get("required_artifacts"),
                    ["model_selection.json", "model_output.md", "run_log.jsonl"],
                )
                self.assertEqual(
                    profile_data.get("non_empty_artifacts"),
                    ["model_selection.json", "model_output.md", "run_log.jsonl"],
                )
                self.assertEqual(profile_data.get("review_checks"), ["model_output_status"])

    def test_low_risk_coding_profile_has_bounded_validation_commands(self) -> None:
        profile_data = validation_profiles()["low_risk_coding"]
        commands = profile_data.get("commands", [])
        command_names = [command.get("name") for command in commands if isinstance(command, dict)]

        self.assertEqual(
            command_names,
            ["pytest_collection", "full_test_suite", "workbench_tool_help_smoke"],
        )

    def test_docs_only_profile_declares_changed_file_policy(self) -> None:
        profile_data = validation_profiles()["docs_only"]
        policy = profile_data.get("changed_file_policy")

        self.assertIsInstance(policy, dict)
        self.assertTrue(policy.get("require_actual_diff"))
        self.assertTrue(policy.get("require_non_empty"))
        self.assertIn("*.md", policy.get("allowed_patterns", []))
        self.assertIn("docs/**/*.md", policy.get("allowed_patterns", []))
        self.assertIn("examples/**/*.md", policy.get("allowed_patterns", []))
        self.assertIn("src/**", policy.get("forbidden_patterns", []))
        self.assertIn("tools/**", policy.get("forbidden_patterns", []))
        self.assertIn("tests/**", policy.get("forbidden_patterns", []))
        self.assertIn("configs/**", policy.get("forbidden_patterns", []))

    def test_focused_change_profiles_require_exact_non_empty_diff_evidence(self) -> None:
        profiles = validation_profiles()

        for profile_name in ("docs_only", "low_risk_coding", "python_package_maintenance", "test_fix"):
            with self.subTest(profile=profile_name):
                profile_data = profiles[profile_name]
                policy = profile_data.get("changed_file_policy")

                self.assertIsInstance(policy, dict)
                self.assertTrue(policy.get("require_actual_diff"))
                self.assertTrue(policy.get("require_non_empty"))

    def test_focused_recipes_require_exact_changed_files_for_record_and_validate(self) -> None:
        focused_recipes = (
            DOCS_ONLY_RECIPE_PATH,
            RECIPE_PATH,
            PYTHON_PACKAGE_RECIPE_PATH,
            TEST_FIX_RECIPE_PATH,
        )

        for recipe_path in focused_recipes:
            with self.subTest(recipe=recipe_path.name):
                text = recipe_path.read_text(encoding="utf-8")

                self.assertIn("exact changed files list", text)
                self.assertIn("files_touched set to the exact changed files list", text)
                self.assertIn("changed_files set to the same exact changed files list", text)

    def test_full_acceptance_recipes_keep_six_tool_order(self) -> None:
        for recipe_path in recipe_files():
            text = recipe_path.read_text(encoding="utf-8")
            if "workbench_record_execution" not in text:
                continue

            with self.subTest(recipe=recipe_path.name):
                positions = [text.index(tool) for tool in FULL_ACCEPTANCE_TOOLS]
                self.assertEqual(positions, sorted(positions))
                self.assertIn("Do not claim the run is accepted", text)
                self.assertIn("Call workbench_record_execution exactly once", text)
                self.assertIn('status="response_captured"', text)
                self.assertIn('routing_feedback_path="{{ routing_feedback_path }}"', text)

    def test_docs_only_recipe_matches_docs_only_policy_profile(self) -> None:
        text = DOCS_ONLY_RECIPE_PATH.read_text(encoding="utf-8")
        positions = [text.index(tool) for tool in FULL_ACCEPTANCE_TOOLS]

        self.assertIn('title: "Workbench Docs-Only Acceptance"', text)
        self.assertEqual(recipe_parameter_default(text, "validation_profile"), "docs_only")
        self.assertEqual(recipe_parameter_default(text, "prompt"), "documentation_accuracy_audit")
        self.assertIn("Documentation-only", text)
        self.assertIn("Do not modify source code", text)
        self.assertIn("Call workbench_record_execution exactly once", text)
        self.assertIn("matching worktree diff evidence", text)
        self.assertEqual(positions, sorted(positions))

    def test_python_package_recipe_matches_package_policy_profile(self) -> None:
        text = PYTHON_PACKAGE_RECIPE_PATH.read_text(encoding="utf-8")
        positions = [text.index(tool) for tool in FULL_ACCEPTANCE_TOOLS]

        self.assertIn('title: "Workbench Python Package Maintenance"', text)
        self.assertEqual(recipe_parameter_default(text, "validation_profile"), "python_package_maintenance")
        self.assertIn("Python package maintenance", text)
        self.assertIn("Preserve Goose as the execution surface", text)
        self.assertIn("package maintenance concerns", text)
        self.assertIn("Call workbench_record_execution exactly once", text)
        self.assertEqual(positions, sorted(positions))

    def test_test_fix_recipe_matches_test_fix_policy_profile(self) -> None:
        text = TEST_FIX_RECIPE_PATH.read_text(encoding="utf-8")
        positions = [text.index(tool) for tool in FULL_ACCEPTANCE_TOOLS]
        profile_data = validation_profiles()["test_fix"]

        self.assertIn('title: "Workbench Test-Fix Acceptance"', text)
        self.assertEqual(recipe_parameter_default(text, "validation_profile"), "test_fix")
        self.assertEqual(recipe_parameter_default(text, "prompt"), "bug_root_cause_investigation")
        self.assertIn("task_test_command", profile_data)
        self.assertTrue(profile_data["task_test_command"]["required"])
        self.assertIn("python -m pytest", profile_data["task_test_command"]["allowed_prefixes"])
        self.assertIn("python -m unittest", profile_data["task_test_command"]["allowed_prefixes"])
        self.assertIn("Test-fix", text)
        self.assertIn('task_type="test"', text)
        self.assertIn("Do not weaken, delete, skip, xfail, or broadly rewrite tests", text)
        self.assertIn("Include the exact test command and result", text)
        self.assertIn("task_test_command", text)
        self.assertIn("Call workbench_record_execution exactly once", text)
        self.assertEqual(positions, sorted(positions))


if __name__ == "__main__":
    unittest.main()
