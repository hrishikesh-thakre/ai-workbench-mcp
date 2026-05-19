import json
import tempfile
import unittest
from pathlib import Path

from ai_workbench_mcp.tools.validate_run import resolve_validation_profile_name


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")


class ValidationProfileResolutionTests(unittest.TestCase):
    def test_explicit_profile_takes_priority_over_artifact_sources(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            write_json(run_dir / "task_metadata.json", {"validation_profile": "docs_only"})
            write_json(
                run_dir / "policy_pack_selection.json",
                {
                    "status": "selected",
                    "ok": True,
                    "recommended_validation_profile": "test_fix",
                    "profile_selection_mode": "auto_advisory",
                },
            )
            write_json(run_dir / "model_selection.json", {"validation_profile": "missing_profile"})

            profile, source = resolve_validation_profile_name("scaffold", run_dir, "scaffold")

        self.assertEqual(profile, "scaffold")
        self.assertEqual(source, "cli_profile")

    def test_task_metadata_profile_is_selected_before_policy_pack_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            write_json(run_dir / "task_metadata.json", {"validation_profile": "docs_only"})
            write_json(
                run_dir / "policy_pack_selection.json",
                {"recommended_validation_profile": "docs_only", "profile_selection_mode": "auto_advisory"},
            )

            profile, source = resolve_validation_profile_name(None, run_dir, "scaffold")

        self.assertEqual(profile, "docs_only")
        self.assertEqual(source, "task_metadata")

    def test_policy_pack_selection_profile_is_selected_before_model_selection(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            write_json(
                run_dir / "policy_pack_selection.json",
                {
                    "status": "selected",
                    "ok": True,
                    "recommended_validation_profile": "test_fix",
                    "profile_selection_mode": "auto_advisory",
                },
            )
            write_json(run_dir / "model_selection.json", {"validation_profile": "test_fix"})

            profile, source = resolve_validation_profile_name(None, run_dir, "scaffold")

        self.assertEqual(profile, "test_fix")
        self.assertEqual(source, "policy_pack_selection")

    def test_policy_pack_selection_can_resolve_catalog_policy_pack_to_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            write_json(
                run_dir / "policy_pack_selection.json",
                {
                    "status": "selected",
                    "ok": True,
                    "recommended_policy_pack": "api_contract_change",
                    "profile_selection_mode": "auto_advisory",
                },
            )

            profile, source = resolve_validation_profile_name(None, run_dir, "scaffold")

        self.assertEqual(profile, "api_contract_change")
        self.assertEqual(source, "policy_pack_selection")

    def test_model_selection_profile_remains_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            write_json(run_dir / "model_selection.json", {"validation_profile": "docs_only"})

            profile, source = resolve_validation_profile_name(None, run_dir, "scaffold")

        self.assertEqual(profile, "docs_only")
        self.assertEqual(source, "model_selection")

    def test_project_default_is_kept_for_legacy_scaffold_flow(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            profile, source = resolve_validation_profile_name(None, Path(tmpdir), "scaffold")

        self.assertEqual(profile, "scaffold")
        self.assertEqual(source, "project_default")

    def test_conflicting_selected_profiles_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            write_json(run_dir / "task_metadata.json", {"validation_profile": "docs_only"})
            write_json(
                run_dir / "policy_pack_selection.json",
                {
                    "status": "selected",
                    "ok": True,
                    "recommended_validation_profile": "test_fix",
                    "profile_selection_mode": "auto_advisory",
                },
            )

            with self.assertRaises(ValueError) as error:
                resolve_validation_profile_name(None, run_dir, "scaffold")

        message = str(error.exception)
        self.assertIn("Conflicting selected validation profiles", message)
        self.assertIn("task_metadata.validation_profile=docs_only", message)
        self.assertIn("policy_pack_selection.recommended_validation_profile=test_fix", message)
        self.assertIn("Pass --profile to choose explicitly", message)

    def test_invalid_selected_profile_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            write_json(
                run_dir / "policy_pack_selection.json",
                {
                    "status": "selected",
                    "ok": True,
                    "recommended_validation_profile": "missing_profile",
                    "profile_selection_mode": "auto_advisory",
                },
            )

            with self.assertRaises(ValueError) as error:
                resolve_validation_profile_name(None, run_dir, "scaffold")

        message = str(error.exception)
        self.assertIn("Invalid selected validation profile", message)
        self.assertIn("policy_pack_selection.recommended_validation_profile=missing_profile", message)
        self.assertIn("Valid profiles are:", message)

    def test_missing_selected_profile_in_modern_artifact_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            write_json(run_dir / "task_metadata.json", {"execution_host": "goose"})

            with self.assertRaises(ValueError) as error:
                resolve_validation_profile_name(None, run_dir, "scaffold")

        message = str(error.exception)
        self.assertIn("No selected validation profile found", message)
        self.assertIn("task_metadata.json validation_profile", message)
        self.assertIn("policy_pack_selection.json recommended_validation_profile", message)
        self.assertIn("Project default fallback is limited to legacy/scaffold runs", message)

    def test_failed_policy_pack_selection_artifact_does_not_supply_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            write_json(
                run_dir / "policy_pack_selection.json",
                {
                    "status": "error",
                    "ok": False,
                    "recommended_validation_profile": "docs_only",
                    "reason": "Conflicting policy_pack and validation_profile.",
                },
            )

            with self.assertRaises(ValueError) as error:
                resolve_validation_profile_name(None, run_dir, "scaffold")

        message = str(error.exception)
        self.assertIn("No selected validation profile found", message)


if __name__ == "__main__":
    unittest.main()
