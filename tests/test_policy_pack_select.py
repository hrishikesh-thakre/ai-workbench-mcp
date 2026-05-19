import unittest

from ai_workbench_mcp.tools.policy_pack_select import select_policy_pack_payload
from ai_workbench_mcp.tools.policy_packs import PRODUCT_POLICY_PACK_NAMES


def assert_selected(test_case: unittest.TestCase, payload: dict[str, object], policy_pack: str) -> None:
    test_case.assertEqual(payload["recommended_policy_pack"], policy_pack)
    test_case.assertEqual(payload["recommended_validation_profile"], policy_pack)
    test_case.assertEqual(payload["profile_selection_mode"], "auto_advisory")


class PolicyPackSelectorTests(unittest.TestCase):
    def test_docs_only_task_selects_docs_policy(self) -> None:
        payload = select_policy_pack_payload(
            task_text="Docs-only update for onboarding copy.",
            changed_files=["docs/ai/START_HERE.md"],
        )

        assert_selected(self, payload, "docs_only")
        self.assertIn("doc_file:docs/ai/START_HERE.md", payload["matched_signals"])

    def test_docs_only_rejects_source_config_or_test_files(self) -> None:
        payload = select_policy_pack_payload(
            task_text="Documentation update with helper code.",
            changed_files=["docs/usage.md", "src/ai_workbench_mcp/server.py"],
        )

        assert_selected(self, payload, "low_risk_bug_fix")

    def test_only_markdown_files_select_docs_policy_without_docs_text(self) -> None:
        payload = select_policy_pack_payload(changed_files=["README.md", "docs/policy-packs/pack.md"])

        assert_selected(self, payload, "docs_only")

    def test_known_failing_test_repair_selects_test_fix(self) -> None:
        payload = select_policy_pack_payload(
            task_text="Repair the known failing test in model routing.",
            task_type="test",
            changed_files=["tests/test_model_select.py"],
        )

        assert_selected(self, payload, "test_fix")

    def test_api_or_mcp_contract_change_selects_contract_policy(self) -> None:
        payload = select_policy_pack_payload(
            task_text="Change the MCP tool response schema_version for the public API contract.",
            changed_files=["contracts/mcp/tool.json"],
        )

        assert_selected(self, payload, "api_contract_change")

    def test_security_privacy_precedence_over_contract_and_docs(self) -> None:
        payload = select_policy_pack_payload(
            task_text="Docs update for MCP auth token handling.",
            changed_files=["docs/security.md"],
        )

        assert_selected(self, payload, "security_privacy_sensitive")

    def test_contract_precedence_over_docs_and_test_fix(self) -> None:
        payload = select_policy_pack_payload(
            task_text="Fix failing tests after MCP contract documentation changed.",
            task_type="test",
            changed_files=["docs/mcp-contract.md", "tests/test_contracts.py"],
        )

        assert_selected(self, payload, "api_contract_change")

    def test_default_selects_low_risk_bug_fix(self) -> None:
        payload = select_policy_pack_payload(
            task_text="Fix a bounded parsing bug in the advisory helper.",
            changed_files=["src/ai_workbench_mcp/tools/helper.py"],
            risk="low",
        )

        assert_selected(self, payload, "low_risk_bug_fix")
        self.assertEqual(payload["matched_signals"], ["default:bounded_bug_fix"])

    def test_payload_shape_lists_existing_candidate_policy_packs(self) -> None:
        payload = select_policy_pack_payload(task_text="Fix bounded bug")

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["operation"], "workbench_select_policy_pack")
        self.assertEqual(payload["status"], "selected")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["candidate_policy_packs"], list(PRODUCT_POLICY_PACK_NAMES))
        self.assertIn(payload["recommended_policy_pack"], payload["candidate_policy_packs"])
        self.assertIn(payload["recommended_validation_profile"], payload["candidate_policy_packs"])
        self.assertEqual(payload["profile_selection_mode"], "auto_advisory")
        self.assertIsInstance(payload["reason"], str)
        self.assertIsInstance(payload["confidence"], float)


if __name__ == "__main__":
    unittest.main()
