from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Iterable
from pathlib import Path

from .policy_packs import PRODUCT_POLICY_PACK_NAMES, load_policy_pack_catalog


SCHEMA_VERSION = 1
OPERATION = "workbench_select_policy_pack"

SECURITY_PRIVACY_TERMS = (
    "auth",
    "authentication",
    "authorization",
    "credential",
    "credentials",
    "cookie",
    "encryption",
    "gdpr",
    "hipaa",
    "oauth",
    "password",
    "permission",
    "permissions",
    "pii",
    "privacy",
    "private data",
    "secret",
    "secrets",
    "security",
    "session",
    "token",
    "vulnerability",
)
API_CONTRACT_TERMS = (
    "api contract",
    "contract",
    "endpoint",
    "json schema",
    "mcp",
    "protocol",
    "public api",
    "request schema",
    "response schema",
    "schema_version",
    "tool contract",
)
DOCS_TERMS = (
    "docs",
    "docs-only",
    "documentation",
    "markdown",
    "readme",
)
FAILING_TEST_TERMS = (
    "broken test",
    "failing test",
    "failing tests",
    "fix test",
    "known failure",
    "red test",
    "test failure",
    "test repair",
)

DOC_EXTENSIONS = {".adoc", ".md", ".mdx", ".rst", ".txt"}
SOURCE_EXTENSIONS = {
    ".c",
    ".cc",
    ".cpp",
    ".cs",
    ".css",
    ".go",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".kt",
    ".py",
    ".rs",
    ".sh",
    ".ts",
    ".tsx",
}
CONFIG_EXTENSIONS = {".cfg", ".ini", ".json", ".toml", ".yaml", ".yml"}
TEST_PATH_PARTS = {"test", "tests", "__tests__", "spec", "specs"}
CONFIG_PATH_PARTS = {".github", "config", "configs"}
SOURCE_PATH_PARTS = {"src", "source", "lib", "app", "tools"}


def _normalize_text(*values: object) -> str:
    return " ".join(str(value) for value in values if value is not None).lower()


def _normalize_files(changed_files: Iterable[object] | None) -> list[str]:
    if changed_files is None:
        return []
    return [str(path).replace("\\", "/").strip() for path in changed_files if str(path).strip()]


def _contains_any(text: str, terms: Iterable[str]) -> list[str]:
    return [term for term in terms if term in text]


def _path_parts(path: str) -> set[str]:
    return {part.lower() for part in Path(path).parts}


def _is_doc_file(path: str) -> bool:
    normalized = path.lower().replace("\\", "/")
    name = Path(normalized).name
    return (
        Path(normalized).suffix in DOC_EXTENSIONS
        or normalized.startswith("docs/")
        or name in {"readme", "readme.md", "changelog", "changelog.md", "license"}
    )


def _is_source_config_or_test_file(path: str) -> bool:
    normalized = path.lower().replace("\\", "/")
    suffix = Path(normalized).suffix
    parts = _path_parts(normalized)
    name = Path(normalized).name
    if suffix in SOURCE_EXTENSIONS or suffix in CONFIG_EXTENSIONS:
        return True
    if parts & (SOURCE_PATH_PARTS | CONFIG_PATH_PARTS | TEST_PATH_PARTS):
        return True
    return name.startswith("test_") or name.endswith("_test.py") or name.endswith(".spec.ts")


def _matched_file_signals(changed_files: list[str], predicate: Callable[[str], bool], signal: str) -> list[str]:
    matches: list[str] = []
    for path in changed_files:
        if predicate(path):
            matches.append(f"{signal}:{path}")
    return matches


def _docs_only_signals(text: str, changed_files: list[str]) -> list[str]:
    text_signals = [f"term:{term}" for term in _contains_any(text, DOCS_TERMS)]
    has_docs_task = bool(text_signals)
    has_only_doc_files = bool(changed_files) and all(_is_doc_file(path) for path in changed_files)
    has_source_config_or_test = any(_is_source_config_or_test_file(path) for path in changed_files)
    if has_source_config_or_test:
        return []
    if has_docs_task or has_only_doc_files:
        file_signals = _matched_file_signals(changed_files, _is_doc_file, "doc_file")
        return text_signals + file_signals
    return []


def _security_file_signals(changed_files: list[str]) -> list[str]:
    signals: list[str] = []
    for path in changed_files:
        normalized = path.lower().replace("\\", "/")
        parts = _path_parts(normalized)
        name = Path(normalized).name
        if parts & {"auth", "security", "privacy", "secrets"} or any(
            token in name for token in ("auth", "credential", "privacy", "secret", "security")
        ):
            signals.append(f"security_file:{path}")
    return signals


def _api_contract_file_signals(changed_files: list[str]) -> list[str]:
    signals: list[str] = []
    for path in changed_files:
        normalized = path.lower().replace("\\", "/")
        parts = _path_parts(normalized)
        name = Path(normalized).name
        if parts & {"contracts", "schemas", "openapi"}:
            signals.append(f"contract_file:{path}")
        elif "contract" in name or name in {"openapi.json", "openapi.yaml", "schema.json"}:
            signals.append(f"contract_file:{path}")
        elif "mcp" in parts and (parts & {"contracts", "schemas"} or "contract" in name):
            signals.append(f"mcp_contract_file:{path}")
    return signals


def _test_fix_signals(text: str, changed_files: list[str], task_type: str | None) -> list[str]:
    text_signals = [f"term:{term}" for term in _contains_any(text, FAILING_TEST_TERMS)]
    type_signal = ["task_type:test"] if str(task_type or "").lower() in {"test", "tests"} else []
    test_file_signals = _matched_file_signals(
        changed_files,
        lambda path: bool(_path_parts(path) & TEST_PATH_PARTS) or Path(path.lower()).name.startswith("test_"),
        "test_file",
    )
    if text_signals and (type_signal or test_file_signals or "repair" in text or "fix" in text):
        return text_signals + type_signal + test_file_signals
    return []


def _confidence_for(policy_pack: str, matched_signals: list[str]) -> float:
    if policy_pack == "low_risk_bug_fix":
        return 0.55
    if len(matched_signals) >= 3:
        return 0.9
    if len(matched_signals) == 2:
        return 0.8
    return 0.7


def select_policy_pack_payload(
    *,
    task_text: str | None = None,
    task_type: str | None = None,
    changed_files: Iterable[object] | None = None,
    prompt: str | None = None,
    risk: str | None = None,
) -> dict[str, object]:
    files = _normalize_files(changed_files)
    text = _normalize_text(task_text, task_type, prompt, risk)

    security_signals = [f"term:{term}" for term in _contains_any(text, SECURITY_PRIVACY_TERMS)]
    security_signals.extend(_security_file_signals(files))
    if security_signals:
        selected = "security_privacy_sensitive"
        reason = "Security, auth, privacy, or secret-handling signals require the sensitive policy pack."
        matched = security_signals
    else:
        api_signals = [f"term:{term}" for term in _contains_any(text, API_CONTRACT_TERMS)]
        api_signals.extend(_api_contract_file_signals(files))
        if api_signals:
            selected = "api_contract_change"
            reason = "Public API, MCP, schema, or contract signals require the contract-change policy pack."
            matched = api_signals
        else:
            docs_signals = _docs_only_signals(text, files)
            if docs_signals:
                selected = "docs_only"
                reason = "The task is docs-oriented or changes only documentation files, with no source, config, or test files."
                matched = docs_signals
            else:
                test_signals = _test_fix_signals(text, files, task_type)
                if test_signals:
                    selected = "test_fix"
                    reason = "Known failing test repair signals require the test-fix policy pack."
                    matched = test_signals
                else:
                    selected = "low_risk_bug_fix"
                    reason = "No higher-risk signals matched; defaulting to the bounded bug-fix policy pack."
                    matched = ["default:bounded_bug_fix"]

    catalog = load_policy_pack_catalog()
    recommended_validation_profile = str(catalog[selected]["validation_profile"])

    return {
        "schema_version": SCHEMA_VERSION,
        "operation": OPERATION,
        "status": "selected",
        "ok": True,
        "recommended_policy_pack": selected,
        "recommended_validation_profile": recommended_validation_profile,
        "profile_selection_mode": "auto_advisory",
        "reason": reason,
        "matched_signals": matched,
        "confidence": _confidence_for(selected, matched),
        "candidate_policy_packs": list(PRODUCT_POLICY_PACK_NAMES),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Select an advisory Workbench policy pack from task metadata.")
    parser.add_argument("--task-text", default="")
    parser.add_argument("--task-type")
    parser.add_argument("--changed-file", action="append", default=[], help="Changed file path. Repeat as needed.")
    parser.add_argument("--prompt")
    parser.add_argument("--risk")
    parser.add_argument("--out", help="Optional JSON output path.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    payload = select_policy_pack_payload(
        task_text=args.task_text,
        task_type=args.task_type,
        changed_files=args.changed_file,
        prompt=args.prompt,
        risk=args.risk,
    )
    rendered = json.dumps(payload, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
