import tempfile
import unittest
from pathlib import Path

from ai_workbench_mcp.tools.policy_packs import PRODUCT_POLICY_PACK_NAMES, load_policy_pack_catalog


REASON_CODES = """    reason_codes:
      accepted: {pack}.accepted
      required_test_missing: {pack}.required_test_missing
      required_test_failed: {pack}.required_test_failed
      required_tests_passed: {pack}.required_tests_passed
"""


def pack_block(pack: str, validation_profile: str | None) -> str:
    validation_line = "" if validation_profile is None else f"    validation_profile: {validation_profile}\n"
    return (
        f"  {pack}:\n"
        f"    name: {pack}\n"
        "    version: v0.2\n"
        f"{validation_line}"
        "    allowed_files:\n"
        "      - \"*.md\"\n"
        "    required_tests:\n"
        "      - smoke\n"
        "    required_evidence:\n"
        "      - model_selection.json\n"
        "    review_triggers:\n"
        "      - model_output_status\n"
        "    blocker_rules:\n"
        "      - blocker\n"
        f"{REASON_CODES.format(pack=pack)}"
    )


def catalog_yaml(overrides: dict[str, str | None] | None = None) -> str:
    overrides = overrides or {}
    blocks = [
        pack_block(pack, overrides.get(pack, pack))
        for pack in PRODUCT_POLICY_PACK_NAMES
    ]
    return "schema_version: 1\npolicy_packs:\n" + "\n".join(blocks)


def profiles_yaml(overrides: dict[str, str] | None = None) -> str:
    overrides = overrides or {}
    lines = ["profiles:"]
    for pack in PRODUCT_POLICY_PACK_NAMES:
        profile_name = overrides.get(pack, pack)
        lines.extend(
            [
                f"  {profile_name}:",
                "    description: Test profile",
                "    policy_pack:",
                f"      name: {pack}",
                "    commands:",
                "      - name: smoke",
                "        command: python --version",
                "        cwd: .",
                "        required: true",
                "        weight: 1.0",
            ]
        )
    return "\n".join(lines) + "\n"


class PolicyPackCatalogTests(unittest.TestCase):
    def write_catalog(self, tmp_path: Path, *, catalog: str, profiles: str) -> Path:
        config_path = tmp_path / "policy_packs.yaml"
        config_path.write_text(catalog, encoding="utf-8")
        (tmp_path / "validation_profiles.yaml").write_text(profiles, encoding="utf-8")
        return config_path

    def test_product_catalog_maps_every_pack_to_matching_validation_profile(self) -> None:
        catalog = load_policy_pack_catalog()

        self.assertEqual(tuple(catalog), PRODUCT_POLICY_PACK_NAMES)
        for pack_name, pack_data in catalog.items():
            with self.subTest(policy_pack=pack_name):
                self.assertEqual(pack_data["validation_profile"], pack_name)

    def test_policy_pack_without_validation_profile_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = self.write_catalog(
                Path(tmpdir),
                catalog=catalog_yaml({"docs_only": None}),
                profiles=profiles_yaml(),
            )

            with self.assertRaisesRegex(ValueError, "docs_only must declare a validation_profile"):
                load_policy_pack_catalog(config_path)

    def test_unknown_validation_profile_mapping_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = self.write_catalog(
                Path(tmpdir),
                catalog=catalog_yaml({"docs_only": "missing_profile"}),
                profiles=profiles_yaml(),
            )

            with self.assertRaisesRegex(ValueError, "unknown validation profile: missing_profile"):
                load_policy_pack_catalog(config_path)

    def test_validation_profile_policy_pack_disagreement_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            profiles = profiles_yaml({"docs_only": "docs_profile"})
            profiles += (
                "  docs_only:\n"
                "    description: Conflicting test profile\n"
                "    policy_pack:\n"
                "      name: docs_only\n"
                "    commands:\n"
                "      - name: smoke\n"
                "        command: python --version\n"
                "        cwd: .\n"
                "        required: true\n"
                "        weight: 1.0\n"
            )
            config_path = self.write_catalog(
                Path(tmpdir),
                catalog=catalog_yaml({"docs_only": "docs_profile"}),
                profiles=profiles,
            )

            with self.assertRaisesRegex(ValueError, "catalog maps that pack to docs_profile"):
                load_policy_pack_catalog(config_path)

    def test_duplicate_validation_profile_mapping_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = self.write_catalog(
                Path(tmpdir),
                catalog=catalog_yaml({"docs_only": "shared_profile", "low_risk_bug_fix": "shared_profile"}),
                profiles=profiles_yaml({"docs_only": "shared_profile", "low_risk_bug_fix": "shared_profile"}),
            )

            with self.assertRaisesRegex(ValueError, "must not share a validation profile"):
                load_policy_pack_catalog(config_path)


if __name__ == "__main__":
    unittest.main()
