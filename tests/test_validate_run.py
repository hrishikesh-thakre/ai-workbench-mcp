import unittest
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from validate_run import validate_captured_response_format


class ValidateCapturedResponseFormatTests(unittest.TestCase):
    def test_response_captured_without_preferred_sections_needs_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            model_output = Path(tmpdir) / "model_output.md"
            model_output.write_text(
                "\n".join(
                    [
                        "# Model Output",
                        "",
                        "## Execution Metadata",
                        "",
                        "- Status: `response_captured`",
                        "",
                        "## Captured Response",
                        "",
                        "Updated docs and validated the help commands.",
                        "Validation run: all 12 documented --help commands passed.",
                    ]
                ),
                encoding="utf-8",
            )

            check = validate_captured_response_format(model_output)

            self.assertEqual(check.status, "needs_review")
            self.assertIn("Missing required response section: Summary:", check.details)
            self.assertIn("Missing required response section: Files touched:", check.details)

    def test_response_captured_with_normalized_response_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            model_output = Path(tmpdir) / "model_output.md"
            model_output.write_text(
                "\n".join(
                    [
                        "# Model Output",
                        "",
                        "## Execution Metadata",
                        "",
                        "- Status: `response_captured`",
                        "",
                        "## Captured Response",
                        "",
                        "raw response",
                        "",
                        "## Normalized Response",
                        "",
                        "Summary:",
                        "Updated docs.",
                        "",
                        "Files touched:",
                        "- AGENTS.md",
                        "",
                        "Validation run:",
                        "- python tools/validate_run.py --help -> passed",
                        "",
                        "Risks / follow-ups:",
                        "- Re-run the audit.",
                    ]
                ),
                encoding="utf-8",
            )

            check = validate_captured_response_format(model_output)

            self.assertEqual(check.status, "passed")
            self.assertEqual(
                check.summary,
                "Captured model response matches the preferred structured format.",
            )


if __name__ == "__main__":
    unittest.main()
