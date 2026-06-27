import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = ROOT / "prompts" / "approved"
README = ROOT / "README.md"
START_HERE = ROOT / "docs" / "ai" / "START_HERE.md"

EXPECTED_PROMPTS = [
    "bug_root_cause_investigation",
    "code_review_patch_risk_audit",
    "data_acquisition_surface_audit",
    "documentation_accuracy_audit",
    "implement_request_change_request",
    "navigation_page_title_ia_audit",
    "performance_latency_hotspot_audit",
    "prompt_failure_improvement_log",
    "repository_context_index_audit",
    "security_privacy_risk_review",
    "test_case_development_meaningful_coverage",
    "ux_visual_accessibility_audit",
]

REFERENCE_ROOTS = [
    ROOT / "tools",
    ROOT / "src",
    ROOT / "configs",
    ROOT / "recipes",
    ROOT / "docs",
    ROOT / "examples",
    README,
]

PROMPTISH_SUFFIXES = (
    "_audit",
    "_review",
    "_request",
    "_investigation",
    "_coverage",
    "_log",
)

NON_PROMPT_IDENTIFIERS = {
    "alternate_model_review",
    "checks_needs_review",
    "evaluate_review",
    "medium_risk_low_capability_review",
    "missing_context_has_needs_review",
    "missing_context_needs_review",
    "missing_context_review",
    "missing_needs_review",
    "model_output_status_needs_review",
    "most_common_missing_context_needs_review",
    "needs_human_review",
    "read_only_audit",
    "require_human_review",
    "runs_needs_review",
    "unresolved_blocking_review",
    "validate_missing_context_review",
    "write_daemon_log",
    "write_run_log",
}


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def reference_files() -> list[Path]:
    files: list[Path] = []
    for root in REFERENCE_ROOTS:
        if root.is_file():
            files.append(root)
            continue
        files.extend(
            path
            for path in root.rglob("*")
            if path.is_file() and path.suffix in {".md", ".py", ".yaml", ".json", ".jsonl"}
        )
    return files


class PromptLibraryTests(unittest.TestCase):
    def test_expected_prompt_files_exist(self) -> None:
        actual = sorted(path.stem for path in PROMPTS_DIR.glob("*.md"))

        self.assertEqual(actual, EXPECTED_PROMPTS)

    def test_each_prompt_starts_with_markdown_h1(self) -> None:
        for prompt_name in EXPECTED_PROMPTS:
            with self.subTest(prompt=prompt_name):
                first_line = read_text(PROMPTS_DIR / f"{prompt_name}.md").splitlines()[0]
                self.assertTrue(first_line.startswith("# "), first_line)

    def test_prompts_do_not_contain_private_paths_target_repos_or_secret_values(self) -> None:
        forbidden_patterns = [
            r"[A-Za-z]:[\\/]",
            r"\bC:/Users\b",
            r"\bD:/ai-workbench\b",
            r"\bD:\\ai-workbench\b",
            r"\bapi[_-]?key\s*[:=]\s*['\"][^'\"]+",
            r"\btoken\s*=\s*['\"][^'\"]+",
            r"\bsk-[A-Za-z0-9_-]{20,}",
            r"BEGIN (?:RSA |OPENSSH |PRIVATE )?KEY",
            r"\bVSCodium\b",
            r"\bCline\b",
        ]

        for prompt_path in PROMPTS_DIR.glob("*.md"):
            text = read_text(prompt_path)
            with self.subTest(prompt=prompt_path.name):
                for pattern in forbidden_patterns:
                    self.assertIsNone(re.search(pattern, text, flags=re.IGNORECASE), pattern)

    def test_every_prompt_referenced_by_tools_docs_and_recipes_exists(self) -> None:
        prompt_names = set(EXPECTED_PROMPTS)
        promptish_name = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+){2,})(?:\.md)?\b")
        missing: dict[str, list[str]] = {}

        for path in reference_files():
            if PROMPTS_DIR in path.parents:
                continue
            text = read_text(path)
            for match in promptish_name.finditer(text):
                name = match.group(1)
                if not name.endswith(PROMPTISH_SUFFIXES) or name in NON_PROMPT_IDENTIFIERS:
                    continue
                if name not in prompt_names:
                    missing.setdefault(name, []).append(str(path.relative_to(ROOT)))

        self.assertEqual(missing, {})

    def test_prompt_catalogs_list_all_approved_prompts(self) -> None:
        combined_catalog_text = read_text(README) + "\n" + read_text(START_HERE)

        for prompt_name in EXPECTED_PROMPTS:
            with self.subTest(prompt=prompt_name):
                self.assertIn(f"{prompt_name}.md", combined_catalog_text)


if __name__ == "__main__":
    unittest.main()
