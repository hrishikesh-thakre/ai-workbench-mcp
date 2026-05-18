import tempfile
import tomllib
import unittest
from pathlib import Path

from ai_workbench_mcp.tools.bootstrap_assets import (
    DEFAULT_GROUPS,
    bootstrap_assets,
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
        ]
        for relative_path in expected_files:
            with self.subTest(relative_path=relative_path):
                self.assertTrue(assets_root.joinpath(*relative_path.split("/")).is_file())

        policy_catalog_text = assets_root.joinpath("configs", "policy_packs.yaml").read_text(encoding="utf-8")
        self.assertIn("policy_packs:", policy_catalog_text)
        self.assertIn("docs_only:", policy_catalog_text)
        self.assertFalse(assets_root.joinpath("examples").is_dir())
        self.assertFalse(assets_root.joinpath("evals").is_dir())

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
            self.assertFalse((target / "examples").exists())
            self.assertFalse((target / "evals").exists())

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

    def test_packaging_metadata_includes_asset_bootstrap_surface(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

        self.assertEqual(
            pyproject["project"]["scripts"]["ai-workbench-bootstrap-assets"],
            "ai_workbench_mcp.tools.bootstrap_assets:main",
        )
        self.assertTrue(pyproject["tool"]["setuptools"]["include-package-data"])
        self.assertIn("recursive-include src/ai_workbench_mcp/assets/configs *.yaml", manifest)
        self.assertIn("recursive-include src/ai_workbench_mcp/assets/prompts *.md", manifest)
        self.assertIn("recursive-include src/ai_workbench_mcp/assets/recipes *.yaml", manifest)


if __name__ == "__main__":
    unittest.main()
