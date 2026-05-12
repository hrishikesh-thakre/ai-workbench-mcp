import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROOTS = [
    ROOT / "README.md",
    ROOT / "configs",
    ROOT / "docs",
    ROOT / "examples",
    ROOT / "prompts",
    ROOT / "recipes",
    ROOT / "src",
    ROOT / "tools",
]
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".py", ".toml", ".txt", ".yaml", ".yml"}


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
            ["accepted-docs-only-smoke", "accepted-tiny-python-fix"],
        )


if __name__ == "__main__":
    unittest.main()
