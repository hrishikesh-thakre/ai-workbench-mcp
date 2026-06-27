import contextlib
import io
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock

from ai_workbench_mcp.tools.bootstrap_assets import (
    BOOTSTRAP_GROUPS,
    DEFAULT_GROUPS,
    bootstrap_main,
    bootstrap_assets,
    bootstrap_repository,
    package_assets_root,
)
ROOT = Path(__file__).resolve().parents[1]
ASSET_GROUP_SUFFIXES = {
    "configs": {".yaml"},
    "prompts": {".md"},
    "recipes": {".yaml"},
}


def source_files_for_group(group: str) -> dict[str, Path]:
    source_root = ROOT / group
    suffixes = ASSET_GROUP_SUFFIXES[group]
    files: dict[str, Path] = {}
    for path in source_root.rglob("*"):
        if not path.is_file() or path.suffix not in suffixes:
            continue
        relative_path = path.relative_to(source_root).as_posix()
        if group == "configs" and relative_path.endswith(".local.yaml"):
            continue
        files[relative_path] = path
    return files


def asset_files_for_group(group: str) -> dict[str, Path]:
    asset_root = Path(str(package_assets_root())) / group
    suffixes = ASSET_GROUP_SUFFIXES[group]
    return {
        path.relative_to(asset_root).as_posix(): path
        for path in asset_root.rglob("*")
        if path.is_file() and path.suffix in suffixes
    }


def result_action(summary: dict[str, object], path: str) -> str:
    files = summary["files"]
    if not isinstance(files, list):
        raise AssertionError("bootstrap summary files must be a list")
    for item in files:
        if isinstance(item, dict) and item.get("path") == path:
            return str(item.get("action"))
    raise AssertionError(f"bootstrap summary did not include {path}")


class PackageAssetTests(unittest.TestCase):
    def test_packaged_assets_include_pr_acceptance_defaults(self) -> None:
        assets_root = package_assets_root()

        expected_files = [
            "configs/policy_packs.yaml",
            "configs/validation_profiles.yaml",
            "configs/projects.yaml",
            "configs/quality_loop.yaml",
            "configs/model_registry.yaml",
            "prompts/approved/documentation_accuracy_audit.md",
            "prompts/approved/bug_root_cause_investigation.md",
            "recipes/workbench-engineering-acceptance.yaml",
            "recipes/workbench-docs-only-acceptance.yaml",
            "recipes/workbench-test-fix-acceptance.yaml",
            "github/workflows/ai-workbench-pr-gate.yml",
            "docs/ai-workbench-pr-gate.md",
        ]
        for relative_path in expected_files:
            with self.subTest(relative_path=relative_path):
                self.assertTrue(assets_root.joinpath(*relative_path.split("/")).is_file())

        policy_catalog_text = assets_root.joinpath("configs", "policy_packs.yaml").read_text(encoding="utf-8")
        self.assertIn("policy_packs:", policy_catalog_text)
        self.assertIn("docs_only:", policy_catalog_text)
        workflow_text = assets_root.joinpath("github", "workflows", "ai-workbench-pr-gate.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("AI Workbench PR Gate", workflow_text)
        self.assertIn("ai-workbench-mcp==0.8.0a0", workflow_text)
        setup_doc_text = assets_root.joinpath("docs", "ai-workbench-pr-gate.md").read_text(encoding="utf-8")
        self.assertIn("validation_report.json", setup_doc_text)
        self.assertIn("revision_decision.json", setup_doc_text)
        self.assertFalse(assets_root.joinpath("examples").is_dir())
        self.assertFalse(assets_root.joinpath("evals").is_dir())

    def test_packaged_pr_gate_workflow_matches_source_template(self) -> None:
        source_workflow = ROOT / ".github" / "workflows" / "ai-workbench-pr-gate.yml"
        packaged_workflow = Path(str(package_assets_root())).joinpath(
            "github",
            "workflows",
            "ai-workbench-pr-gate.yml",
        )

        self.assertEqual(packaged_workflow.read_bytes(), source_workflow.read_bytes())

    def test_packaged_validation_profiles_do_not_reference_repo_local_tool_paths(self) -> None:
        validation_profile_text = Path(str(package_assets_root())).joinpath(
            "configs",
            "validation_profiles.yaml",
        ).read_text(encoding="utf-8")

        self.assertNotIn("python tools/", validation_profile_text)
        self.assertIn("python -m ai_workbench_mcp.cli validate --help", validation_profile_text)
        self.assertIn("python -m ai_workbench_mcp.cli pr-gate --help", validation_profile_text)
        self.assertIn("python -m ai_workbench_mcp.tools.golden_eval --help", validation_profile_text)

    def test_packaged_bootstrap_doc_explains_local_recovery_smoke(self) -> None:
        setup_doc_text = Path(str(package_assets_root())).joinpath(
            "docs",
            "ai-workbench-pr-gate.md",
        ).read_text(encoding="utf-8")

        for phrase in (
            "ai-workbench pr-gate",
            "--fallback-run-dir",
            "pr_decision.json",
            "pr_comment.md",
            "Missing evidence and scaffold evidence are not semantic",
            "acceptance.",
            "Do not commit `runs/`.",
        ):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, setup_doc_text)

    def test_packaged_assets_match_source_defaults(self) -> None:
        for group in DEFAULT_GROUPS:
            with self.subTest(group=group):
                source_files = source_files_for_group(group)
                packaged_files = asset_files_for_group(group)

                self.assertEqual(set(packaged_files), set(source_files))
                for relative_path, source_path in source_files.items():
                    with self.subTest(group=group, relative_path=relative_path):
                        self.assertEqual(
                            packaged_files[relative_path].read_bytes(),
                            source_path.read_bytes(),
                        )

    def test_bootstrap_copies_default_assets_to_repo_style_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)

            summary = bootstrap_assets(target)
            second_summary = bootstrap_assets(target)

            self.assertEqual(summary["groups"], list(DEFAULT_GROUPS))
            self.assertEqual(summary["counts"]["skipped"], 0)
            self.assertGreater(summary["counts"]["copied"], 0)
            self.assertEqual(second_summary["counts"]["skipped"], 0)
            self.assertEqual(second_summary["counts"]["copied"], 0)
            self.assertGreater(second_summary["counts"]["unchanged"], 0)

            self.assertTrue((target / "configs" / "policy_packs.yaml").is_file())
            self.assertTrue((target / "configs" / "validation_profiles.yaml").is_file())
            self.assertTrue((target / "prompts" / "approved" / "documentation_accuracy_audit.md").is_file())
            self.assertTrue((target / "recipes" / "workbench-engineering-acceptance.yaml").is_file())
            self.assertFalse((target / ".github").exists())
            self.assertFalse((target / "docs").exists())
            self.assertFalse((target / "examples").exists())
            self.assertFalse((target / "evals").exists())

    def test_bootstrap_repository_copies_adoption_assets_and_gitignore(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)

            summary = bootstrap_repository(target)
            second_summary = bootstrap_repository(target)

            self.assertEqual(summary["groups"], list(BOOTSTRAP_GROUPS))
            self.assertEqual(summary["counts"]["skipped"], 0)
            self.assertGreater(summary["counts"]["copied"], 0)
            self.assertEqual(summary["gitignore"], {"path": ".gitignore", "action": "created"})
            self.assertEqual(second_summary["counts"]["skipped"], 0)
            self.assertEqual(second_summary["counts"]["copied"], 0)
            self.assertGreater(second_summary["counts"]["unchanged"], 0)
            self.assertEqual(second_summary["gitignore"], {"path": ".gitignore", "action": "unchanged"})

            workflow_path = target / ".github" / "workflows" / "ai-workbench-pr-gate.yml"
            setup_doc_path = target / "docs" / "ai-workbench-pr-gate.md"
            gitignore_path = target / ".gitignore"

            self.assertEqual(
                result_action(summary, ".github/workflows/ai-workbench-pr-gate.yml"),
                "copied",
            )
            self.assertEqual(result_action(summary, "docs/ai-workbench-pr-gate.md"), "copied")
            self.assertTrue(workflow_path.is_file())
            self.assertTrue(setup_doc_path.is_file())
            self.assertIn("AI Workbench PR Gate", workflow_path.read_text(encoding="utf-8"))
            self.assertIn("validation_report.json", setup_doc_path.read_text(encoding="utf-8"))
            self.assertEqual(gitignore_path.read_text(encoding="utf-8"), "runs/\n")

    def test_bootstrap_command_supports_dry_run_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            gitignore_path = target / ".gitignore"
            gitignore_path.write_text("# local ignores\n", encoding="utf-8")
            stdout = io.StringIO()

            with mock.patch.object(
                sys,
                "argv",
                ["ai-workbench", "--target", str(target), "--dry-run", "--json"],
            ):
                with contextlib.redirect_stdout(stdout):
                    exit_code = bootstrap_main()

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertTrue(payload["dry_run"])
            self.assertEqual(payload["groups"], list(BOOTSTRAP_GROUPS))
            self.assertEqual(payload["gitignore"], {"path": ".gitignore", "action": "appended"})
            self.assertEqual(gitignore_path.read_text(encoding="utf-8"), "# local ignores\n")
            self.assertFalse((target / ".github").exists())
            self.assertFalse((target / "docs").exists())

    def test_bootstrap_refuses_overwrite_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir)
            policy_pack_path = target / "configs" / "policy_packs.yaml"
            policy_pack_path.parent.mkdir(parents=True)
            policy_pack_path.write_text("local override\n", encoding="utf-8")

            summary = bootstrap_assets(target, groups=("configs",))

            self.assertEqual(result_action(summary, "configs/policy_packs.yaml"), "skipped")
            self.assertEqual(summary["counts"]["skipped"], 1)
            self.assertEqual(policy_pack_path.read_text(encoding="utf-8"), "local override\n")

            forced_summary = bootstrap_assets(target, groups=("configs",), force=True)

            self.assertEqual(result_action(forced_summary, "configs/policy_packs.yaml"), "overwritten")
            self.assertIn("policy_packs:", policy_pack_path.read_text(encoding="utf-8"))

    def test_packaging_metadata_includes_unified_cli_and_assets(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

        self.assertEqual(pyproject["project"]["scripts"], {"ai-workbench": "ai_workbench_mcp.cli:main"})
        self.assertTrue(pyproject["tool"]["setuptools"]["include-package-data"])
        self.assertIn("recursive-include src/ai_workbench_mcp/assets/configs *.yaml", manifest)
        self.assertIn("recursive-include src/ai_workbench_mcp/assets/prompts *.md", manifest)
        self.assertIn("recursive-include src/ai_workbench_mcp/assets/recipes *.yaml", manifest)
        self.assertIn("recursive-include src/ai_workbench_mcp/assets/github *.yml", manifest)
        self.assertIn("recursive-include src/ai_workbench_mcp/assets/docs *.md", manifest)


if __name__ == "__main__":
    unittest.main()
