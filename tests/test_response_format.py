import unittest

from ai_workbench_mcp.tools.response_format import (
    extract_preferred_response_text,
    missing_required_sections,
    normalize_response_text,
)


class NormalizeResponseTextTests(unittest.TestCase):
    def test_normalizes_structured_response_after_tool_chatter(self) -> None:
        raw_response = "\n".join(
            [
                "Reviewing the target module and existing tests first.",
                "Ran 5 commands",
                "",
                "Summary:",
                "Added focused unit coverage.",
                "",
                "Files touched:",
                "- tests/test_quality_loop.py",
                "",
                "Validation run:",
                "- python -m unittest tests.test_quality_loop -> passed",
                "",
                "Risks / follow-ups:",
                "- Cover determine_auto_trigger separately.",
            ]
        )

        result = normalize_response_text(raw_response)

        self.assertIsNotNone(result.normalized_text)
        self.assertNotIn("Reviewing the target", result.normalized_text)
        self.assertNotIn("Ran 5 commands", result.normalized_text)
        self.assertIn("Summary:\nAdded focused unit coverage.", result.normalized_text)

    def test_normalizes_markdown_heading_section_labels(self) -> None:
        raw_response = "\n".join(
            [
                "### Summary",
                "Fixed the focused fixture bug.",
                "",
                "### Files touched:",
                "- examples/tiny-python-fix/calculator.py",
                "",
                "### Validation run:",
                "- python -m unittest discover -s examples/tiny-python-fix -p test_*.py -> passed",
                "",
                "### Risks / follow-ups:",
                "- None.",
            ]
        )

        result = normalize_response_text(raw_response)

        self.assertIsNotNone(result.normalized_text)
        self.assertIn("Summary:\nFixed the focused fixture bug.", result.normalized_text)
        self.assertIn("Files touched:\n- examples/tiny-python-fix/calculator.py", result.normalized_text)

    def test_infers_summary_and_files_when_other_required_sections_exist(self) -> None:
        raw_response = "\n".join(
            [
                "Updated AGENTS.md and docs/ai/START_HERE.md to match the current repo state.",
                "",
                "Validation run: all 12 documented --help commands passed.",
                "",
                "Risks / follow-ups:",
                "- Re-run the docs audit against the updated files.",
            ]
        )

        result = normalize_response_text(raw_response)

        self.assertIsNotNone(result.normalized_text)
        self.assertTrue(result.used_inferred_summary)
        self.assertTrue(result.used_inferred_files)
        self.assertIn("Files touched:\n- AGENTS.md\n- docs/ai/START_HERE.md", result.normalized_text)


class PreferredResponseSelectionTests(unittest.TestCase):
    def test_prefers_normalized_response_when_present(self) -> None:
        model_output = "\n".join(
            [
                "# Model Output",
                "",
                "## Captured Response",
                "",
                "raw response",
                "",
                "## Normalized Response",
                "",
                "Summary:\nClean response",
            ]
        )

        self.assertEqual(extract_preferred_response_text(model_output), "Summary:\nClean response")

    def test_captured_response_allows_nested_markdown_headings(self) -> None:
        model_output = "\n".join(
            [
                "# Model Output",
                "",
                "## Execution Metadata",
                "",
                "- Status: `response_captured`",
                "",
                "## Captured Response",
                "",
                "## Artifact: Interpretation",
                "",
                "### Details",
                "",
                "The model response uses normal Markdown headings.",
                "",
                "## Normalized Response",
                "",
                "Summary:",
                "Clean response",
            ]
        )

        self.assertEqual(
            extract_preferred_response_text(model_output),
            "Summary:\nClean response",
        )

    def test_captured_response_without_normalized_allows_nested_headings(self) -> None:
        model_output = "\n".join(
            [
                "# Model Output",
                "",
                "## Execution Metadata",
                "",
                "- Status: `response_captured`",
                "",
                "## Captured Response",
                "",
                "## Artifact: Interpretation",
                "",
                "### Details",
                "",
                "The model response uses normal Markdown headings.",
            ]
        )

        self.assertIn(
            "## Artifact: Interpretation",
            extract_preferred_response_text(model_output),
        )

    def test_missing_required_sections_requires_validation_run_or_not_run(self) -> None:
        response_text = "\n".join(
            [
                "Summary:",
                "Did work.",
                "",
                "Files touched:",
                "- foo.py",
                "",
                "Risks / follow-ups:",
                "- None.",
            ]
        )

        self.assertEqual(
            missing_required_sections(response_text),
            ["Validation run: or Validation not run:"],
        )

    def test_missing_required_sections_accepts_markdown_headings(self) -> None:
        response_text = "\n".join(
            [
                "### Summary",
                "Did work.",
                "",
                "### Files touched",
                "- foo.py",
                "",
                "### Validation run",
                "- pytest -> passed",
                "",
                "### Risks / follow-ups",
                "- None.",
            ]
        )

        self.assertEqual(missing_required_sections(response_text), [])


if __name__ == "__main__":
    unittest.main()
