from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
import json
from fnmatch import fnmatch
from pathlib import Path
import re
import subprocess

from config_loader import load_simple_yaml


WORKBENCH_ROOT = Path(__file__).resolve().parent.parent
SEARCH_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "build",
    "change",
    "changes",
    "feature",
    "fix",
    "for",
    "from",
    "implement",
    "implementation",
    "into",
    "issue",
    "make",
    "milestone",
    "need",
    "please",
    "problem",
    "request",
    "task",
    "that",
    "the",
    "this",
    "update",
    "use",
    "using",
    "with",
    "work",
    "workflow",
}
SEARCH_BROAD_COMPONENT_TERMS = {
    "config",
    "configs",
    "context",
    "doc",
    "docs",
    "file",
    "files",
    "model",
    "models",
    "policy",
    "prompt",
    "prompts",
    "review",
    "reviews",
    "scout",
    "tool",
    "tools",
    "validation",
}
SEARCH_TEXT_LIMIT = 60000
MAX_SEARCH_TERMS = 12
EXCERPT_MAX_LINES = 18
EXCERPT_MAX_CHARS = 1800
EXCERPT_SOURCE_LIMIT = 5
PRIMARY_REFERENCE_LIMIT = 6
TOP_RANKED_FILE_LIMIT = 25
STALE_AFTER_DAYS = 180
SECRET_PATTERNS = (
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s]+"),
    re.compile(r"(?i)\b(authorization:\s*bearer)\s+[a-z0-9._~+/-]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.DOTALL),
)


@dataclass
class ProjectConfig:
    key: str
    root: Path
    docs: dict[str, str]
    prompts_dir: Path
    runs_dir: Path
    default_context_profile: str
    default_validation_profile: str


@dataclass
class ContextProfile:
    name: str
    docs: list[str]
    include: list[str]
    exclude: list[str]


@dataclass
class GitEvidence:
    status: str
    patch_text: str
    info_notes: list[str]
    review_notes: list[str]


@dataclass
class RankedFile:
    path: Path
    score: int
    matched_terms: list[str]
    boosts: list[str]
    penalties: list[str]
    reason: str


@dataclass
class RedactionSummary:
    redactions_applied: int = 0

    def record(self, count: int) -> None:
        self.redactions_applied += count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build an expert packet from configured docs, file evidence, and optional git context."
    )
    parser.add_argument("--project", required=True, help="Project key from configs/projects.yaml.")
    parser.add_argument("--task", required=True, help="Task summary to investigate or implement.")
    parser.add_argument("--prompt", required=True, help="Approved prompt name for the run.")
    parser.add_argument(
        "--risk",
        choices=["low", "medium", "high"],
        default="medium",
        help="Risk class for the run.",
    )
    parser.add_argument(
        "--include-diff",
        action="store_true",
        help="Include local git diff evidence when available.",
    )
    parser.add_argument(
        "--docs",
        nargs="*",
        default=[],
        help="Extra documentation files to force into the packet.",
    )
    parser.add_argument(
        "--changed-files",
        nargs="*",
        default=[],
        help="Optional list of changed files to prioritize in the packet.",
    )
    parser.add_argument(
        "--context-profile",
        help="Optional override for the context profile from configs/context_profiles.yaml.",
    )
    parser.add_argument("--out-dir", help="Optional explicit output directory under runs/.")
    return parser


def load_project_config(project_key: str) -> ProjectConfig:
    raw_data = load_simple_yaml(WORKBENCH_ROOT / "configs" / "projects.yaml")
    projects = raw_data.get("projects", {})
    if project_key not in projects:
        raise ValueError(f"Unknown project key: {project_key}")

    project_data = projects[project_key]
    project_root = resolve_project_path(project_data.get("root", "."), WORKBENCH_ROOT)
    prompts_dir = resolve_project_path(project_data.get("prompts_dir", "prompts/approved"), project_root)
    runs_dir = resolve_project_path(project_data.get("runs_dir", "runs"), project_root)

    return ProjectConfig(
        key=project_key,
        root=project_root,
        docs=project_data.get("docs", {}),
        prompts_dir=prompts_dir,
        runs_dir=runs_dir,
        default_context_profile=str(project_data.get("default_context_profile", "default_docs_first")),
        default_validation_profile=str(project_data.get("default_validation_profile", "scaffold")),
    )


def load_context_profile(profile_name: str) -> ContextProfile:
    raw_data = load_simple_yaml(WORKBENCH_ROOT / "configs" / "context_profiles.yaml")
    profiles = raw_data.get("profiles", {})
    if profile_name not in profiles:
        raise ValueError(f"Unknown context profile: {profile_name}")

    profile_data = profiles[profile_name]
    return ContextProfile(
        name=profile_name,
        docs=[str(item) for item in profile_data.get("docs", [])],
        include=[str(item) for item in profile_data.get("include", [])],
        exclude=[str(item) for item in profile_data.get("exclude", [])],
    )


def empty_missing_context() -> dict[str, list[str]]:
    return {"needs_review": [], "info": []}


def add_missing_context(missing_context: dict[str, list[str]], severity: str, note: str) -> None:
    missing_context.setdefault(severity, []).append(note)


def resolve_project_path(path_text: str, base_root: Path) -> Path:
    candidate = Path(path_text)
    if candidate.is_absolute():
        return candidate
    return (base_root / candidate).resolve()


def resolve_prompt_path(prompt_name: str, prompts_dir: Path) -> Path:
    prompt_path = Path(prompt_name)
    file_name = prompt_path.name if prompt_path.suffix else f"{prompt_path.name}.md"
    return (prompts_dir / file_name).resolve()


def resolve_cli_path(path_text: str, project_root: Path) -> Path:
    candidate = Path(path_text)
    if candidate.is_absolute():
        return candidate
    return (project_root / candidate).resolve()


def build_run_id(task: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    slug = slugify(task)
    return f"{timestamp}_{slug}"


def slugify(task: str, max_length: int = 48) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", task.lower()).strip("_")
    if not cleaned:
        cleaned = "task"
    return cleaned[:max_length].rstrip("_") or "task"


def collect_docs(
    project: ProjectConfig,
    profile: ContextProfile,
    prompt_path: Path,
    extra_docs: list[str],
    missing_context: dict[str, list[str]],
) -> list[Path]:
    ordered_docs: list[Path] = []

    agents_path = project.root / "AGENTS.md"
    if agents_path.exists():
        ordered_docs.append(agents_path)
    else:
        add_missing_context(missing_context, "needs_review", "AGENTS.md is missing from the project root.")

    if prompt_path.exists():
        ordered_docs.append(prompt_path)
    else:
        add_missing_context(
            missing_context,
            "needs_review",
            f"Approved prompt file is missing: {relative_path(prompt_path, project.root)}",
        )

    for doc_text in extra_docs:
        doc_path = resolve_cli_path(doc_text, project.root)
        if doc_path.exists():
            ordered_docs.append(doc_path)
        else:
            add_missing_context(missing_context, "needs_review", f"Explicit doc is missing: {doc_text}")

    for doc_text in profile.docs:
        doc_path = resolve_cli_path(doc_text, project.root)
        if doc_path.exists():
            ordered_docs.append(doc_path)
        else:
            add_missing_context(missing_context, "needs_review", f"Configured profile doc is missing: {doc_text}")

    return dedupe_paths(ordered_docs)


def collect_candidate_files(project: ProjectConfig, profile: ContextProfile) -> list[Path]:
    matched_files: list[Path] = []
    for include_pattern in profile.include:
        for candidate in project.root.glob(include_pattern):
            if candidate.is_file() and not is_excluded(candidate, project.root, profile.exclude):
                matched_files.append(candidate.resolve())
    return sorted(dedupe_paths(matched_files), key=lambda path: relative_path(path, project.root))


def extract_search_terms(task: str, prompt_name: str, changed_files: list[Path]) -> list[str]:
    phrase_terms: list[str] = []
    keyword_tokens: list[str] = []

    for token in re.findall(r"[A-Za-z0-9_./-]+", f"{task} {Path(prompt_name).stem}"):
        normalized = token.lower().strip("._/-")
        if not normalized:
            continue

        if any(separator in normalized for separator in ("_", "/", "-", ".")):
            phrase_terms.append(normalized)
            parts = [part for part in re.split(r"[_/.-]+", normalized) if part]
        else:
            parts = [normalized]

        for part in parts:
            if len(part) >= 3 and part not in SEARCH_STOPWORDS:
                keyword_tokens.append(part)

    for changed_file in changed_files:
        stem = changed_file.stem.lower()
        phrase_terms.append(stem)
        for part in re.split(r"[_/.-]+", stem):
            if len(part) >= 3 and part not in SEARCH_STOPWORDS:
                keyword_tokens.append(part)

    for left, right in zip(keyword_tokens, keyword_tokens[1:]):
        phrase_terms.append(f"{left}_{right}")
        phrase_terms.append(f"{left} {right}")

    compound_components: set[str] = set()
    for phrase in phrase_terms:
        if not any(separator in phrase for separator in ("_", "/", "-", ".", " ")):
            continue
        compound_components.update(part for part in re.split(r"[_/ .-]+", phrase) if part)

    raw_terms: list[str] = []
    raw_terms.extend(phrase_terms)
    for token in keyword_tokens:
        if token in compound_components and token in SEARCH_BROAD_COMPONENT_TERMS:
            continue
        raw_terms.append(token)

    search_terms: list[str] = []
    seen: set[str] = set()
    for raw_term in raw_terms:
        normalized = re.sub(r"\s+", " ", raw_term.strip().lower())
        if len(normalized) < 3 or normalized in seen:
            continue
        if normalized in SEARCH_STOPWORDS:
            continue
        seen.add(normalized)
        search_terms.append(normalized)
        if len(search_terms) >= MAX_SEARCH_TERMS:
            break

    if search_terms:
        return search_terms

    fallback = [part for part in re.findall(r"[a-z0-9]+", task.lower()) if len(part) >= 3]
    return dedupe_strings(fallback)[:MAX_SEARCH_TERMS] or [Path(prompt_name).stem.lower()]


def is_excluded(candidate: Path, project_root: Path, exclude_patterns: list[str]) -> bool:
    relative_candidate = relative_path(candidate, project_root)
    return any(fnmatch(relative_candidate, pattern) for pattern in exclude_patterns)


def normalize_changed_files(
    changed_files: list[str], project_root: Path, missing_context: dict[str, list[str]]
) -> list[Path]:
    normalized: list[Path] = []
    if not changed_files:
        add_missing_context(
            missing_context,
            "info",
            "No changed files were supplied; scout used profile-based discovery only.",
        )
        return normalized

    for changed_file in changed_files:
        changed_path = resolve_cli_path(changed_file, project_root)
        if changed_path.exists() and changed_path.is_file():
            normalized.append(changed_path)
        else:
            add_missing_context(missing_context, "needs_review", f"Changed file was not found on disk: {changed_file}")

    return dedupe_paths(normalized)


def dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    ordered_paths: list[Path] = []
    for path in paths:
        resolved = str(path.resolve())
        if resolved in seen:
            continue
        seen.add(resolved)
        ordered_paths.append(path.resolve())
    return ordered_paths


def dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered_values: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        ordered_values.append(value)
    return ordered_values


def relative_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def format_score_component(label: str, amount: int) -> str:
    return f"{label} {amount:+d}"


def build_rank_reason(
    path: Path,
    resolved_key: str,
    matched_terms: list[str],
    docs_priority: dict[str, int],
    changed_priority: dict[str, int],
    prompt_key: str,
    target_tool_stems: set[str],
) -> str:
    if resolved_key == prompt_key:
        return "Selected approved prompt"

    if changed_priority.get(resolved_key, 0):
        return "Explicit changed file"

    if len(path.parts) >= 2 and path.parts[-2] == "tools":
        tool_stem = normalize_tool_stem(path)
        if tool_stem in target_tool_stems:
            if path.suffix.lower() == ".py":
                return "Direct target tool"
            if path.name.endswith("_layer.md"):
                return "Adjacent design doc"
            return "Target tool surface"

        if target_tool_stems:
            if path.name.endswith("_layer.md"):
                return "Broad adjacent layer only"
            if path.suffix.lower() == ".py":
                return "Neighboring tool implementation"

    if docs_priority.get(resolved_key, 0):
        return "Priority document from configured context"

    if matched_terms:
        return "Matched task terms in path or content"

    return "Included by context profile"


def collect_git_evidence(project_root: Path, include_diff: bool) -> GitEvidence:
    if not include_diff:
        return GitEvidence(
            status="not_requested",
            patch_text="Git diff not requested.\n",
            info_notes=[],
            review_notes=[],
        )

    git_check = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if git_check.returncode != 0 or git_check.stdout.strip().lower() != "true":
        return GitEvidence(
            status="unavailable",
            patch_text=(
                "No git diff captured.\n\n"
                "Reason: the workspace is not currently inside a git repository.\n"
            ),
            info_notes=["Git diff unavailable because the workspace is not currently inside a git repository."],
            review_notes=[],
        )

    diff_result = subprocess.run(
        ["git", "diff", "--no-ext-diff", "--binary"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if diff_result.returncode != 0:
        return GitEvidence(
            status="error",
            patch_text=(
                "No git diff captured.\n\n"
                f"Reason: git diff failed with exit code {diff_result.returncode}.\n"
            ),
            info_notes=[],
            review_notes=[f"git diff failed with exit code {diff_result.returncode}."],
        )

    if not diff_result.stdout.strip():
        return GitEvidence(
            status="clean",
            patch_text="No local git diff detected.\n",
            info_notes=["Git diff requested, but no local modifications were detected."],
            review_notes=[],
        )

    return GitEvidence(status="captured", patch_text=diff_result.stdout, info_notes=[], review_notes=[])


def redact_sensitive_text(text: str) -> tuple[str, int]:
    redacted = text
    total = 0
    for pattern in SECRET_PATTERNS:
        redacted, count = pattern.subn("[REDACTED]", redacted)
        total += count
    return redacted, total


def read_excerpt(
    file_path: Path,
    redaction_summary: RedactionSummary | None = None,
    max_lines: int = EXCERPT_MAX_LINES,
    max_chars: int = EXCERPT_MAX_CHARS,
) -> str:
    lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    excerpt = "\n".join(lines[:max_lines]).strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[: max_chars - 1].rstrip() + "…"
    excerpt, redaction_count = redact_sensitive_text(excerpt)
    if redaction_summary is not None:
        redaction_summary.record(redaction_count)
    return excerpt or "[empty file]"


def read_searchable_text(file_path: Path) -> str:
    text = file_path.read_text(encoding="utf-8", errors="replace")
    return text[:SEARCH_TEXT_LIMIT].lower()


def normalize_tool_stem(path: Path) -> str:
    stem = path.stem.lower()
    if stem.endswith("_layer"):
        stem = stem[: -len("_layer")]
    return stem


def source_kind_for(path: Path, project_root: Path) -> str:
    relative = relative_path(path, project_root)
    first_part = relative.split("/", 1)[0]
    suffix = path.suffix.lower()
    if relative.startswith("prompts/"):
        return "prompt"
    if relative == "AGENTS.md" or relative.startswith("docs/") or suffix in {".md", ".rst", ".txt"}:
        return "documentation"
    if relative.startswith("configs/") or suffix in {".yaml", ".yml", ".toml", ".json"}:
        return "configuration"
    if first_part == "tools" or suffix in {".py", ".ts", ".tsx", ".js", ".jsx"}:
        return "code"
    if first_part == "tests":
        return "test"
    return "other"


def freshness_for(path: Path) -> dict[str, object]:
    try:
        modified_at = datetime.fromtimestamp(path.stat().st_mtime)
    except OSError:
        return {
            "status": "MISSING",
            "modified_at": None,
            "age_days": None,
            "reason": "Path could not be statted.",
        }
    age_days = max(0, (datetime.now() - modified_at).days)
    status = "STALE" if age_days > STALE_AFTER_DAYS else "CURRENT"
    return {
        "status": status,
        "modified_at": modified_at.isoformat(timespec="seconds"),
        "age_days": age_days,
        "stale_after_days": STALE_AFTER_DAYS,
    }


def conflict_signals_for(path: Path) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")[:SEARCH_TEXT_LIMIT]
    except OSError:
        return ["unreadable"]
    signals: list[str] = []
    line_markers = {line.strip()[:7] for line in text.splitlines()}
    if {"<<<<<<<", "=======", ">>>>>>>"} <= line_markers:
        signals.append("merge_conflict_marker")
    return signals


def selection_provenance_for(ranked_file: RankedFile) -> list[str]:
    provenance: list[str] = []
    if any(boost.startswith("prompt_file") for boost in ranked_file.boosts):
        provenance.append("prompt_file")
    if any(boost.startswith("changed_file") for boost in ranked_file.boosts):
        provenance.append("changed_file")
    if any(boost.startswith("docs_priority") for boost in ranked_file.boosts):
        provenance.append("configured_document")
    if ranked_file.matched_terms:
        provenance.append("deterministic_search")
    if not provenance:
        provenance.append("context_profile")
    return provenance


def derive_target_tool_stems(files: list[Path], search_terms: list[str]) -> set[str]:
    known_tool_stems = {
        normalize_tool_stem(path)
        for path in files
        if len(path.parts) >= 2 and path.parts[-2] == "tools"
    }
    targets: set[str] = set()
    for term in search_terms:
        normalized = term.replace(" ", "_").lower()
        if normalized in known_tool_stems:
            targets.add(normalized)
    return targets


def rank_files_for_task(
    files: list[Path],
    project_root: Path,
    search_terms: list[str],
    docs_read: list[Path],
    changed_files: list[Path],
    prompt_path: Path,
) -> list[RankedFile]:
    docs_priority = {
        str(path.resolve()): max(0, 60 - (index * 6)) for index, path in enumerate(docs_read)
    }
    changed_priority = {
        str(path.resolve()): max(0, 180 - (index * 12)) for index, path in enumerate(changed_files)
    }
    prompt_key = str(prompt_path.resolve())
    target_tool_stems = derive_target_tool_stems(files, search_terms)
    ranked_files: list[RankedFile] = []

    for path in files:
        resolved_key = str(path.resolve())
        relative = relative_path(path, project_root)
        lower_relative = relative.lower()
        searchable_text = read_searchable_text(path)
        path_segments = {segment for segment in re.split(r"[/_.-]+", lower_relative) if segment}

        score = docs_priority.get(resolved_key, 0)
        boosts: list[str] = []
        penalties: list[str] = []

        docs_score = docs_priority.get(resolved_key, 0)
        if docs_score:
            boosts.append(format_score_component("docs_priority", docs_score))

        if resolved_key == prompt_key:
            score += 90
            boosts.append(format_score_component("prompt_file", 90))

        changed_score = changed_priority.get(resolved_key, 0)
        if changed_score:
            score += changed_score
            boosts.append(format_score_component("changed_file", changed_score))

        matched_terms: list[str] = []
        for term in search_terms:
            term_score = 0
            normalized_path_term = term.replace(" ", "_")
            path_term_score = 0
            if term in lower_relative or normalized_path_term in lower_relative:
                if term in path_segments or normalized_path_term in path_segments:
                    path_term_score += 40
                else:
                    path_term_score += 24
                term_score += path_term_score
                boosts.append(format_score_component(f"path_hit:{term}", path_term_score))

            hit_count = searchable_text.count(term)
            if not hit_count and normalized_path_term != term:
                hit_count = searchable_text.count(normalized_path_term)
            if hit_count:
                content_term_score = min(hit_count, 3) * (14 if len(term) > 8 else 10)
                term_score += content_term_score
                boosts.append(format_score_component(f"content_hit:{term}", content_term_score))

            if term_score:
                score += term_score
                matched_terms.append(term)

        if matched_terms:
            matched_bonus = min(len(matched_terms), 5) * 8
            score += matched_bonus
            boosts.append(format_score_component("matched_terms_bonus", matched_bonus))

        if len(path.parts) >= 2 and path.parts[-2] == "tools" and target_tool_stems:
            tool_stem = normalize_tool_stem(path)
            if tool_stem not in target_tool_stems:
                if path.name.endswith("_layer.md"):
                    score -= 28
                    penalties.append(format_score_component("non_target_tool_layer", -28))
                elif path.suffix.lower() == ".py":
                    score -= 10
                    penalties.append(format_score_component("non_target_tool_file", -10))

        if path.suffix.lower() in {".py", ".ts", ".tsx", ".js", ".jsx"}:
            score += 4
            boosts.append(format_score_component("code_file", 4))

        deduped_matched_terms = dedupe_strings(matched_terms)[:5]

        ranked_files.append(
            RankedFile(
                path=path,
                score=score,
                matched_terms=deduped_matched_terms,
                boosts=boosts,
                penalties=penalties,
                reason=build_rank_reason(
                    path=path,
                    resolved_key=resolved_key,
                    matched_terms=deduped_matched_terms,
                    docs_priority=docs_priority,
                    changed_priority=changed_priority,
                    prompt_key=prompt_key,
                    target_tool_stems=target_tool_stems,
                ),
            )
        )

    return sorted(
        ranked_files,
        key=lambda item: (-item.score, relative_path(item.path, project_root)),
    )


def classify_task(prompt_name: str) -> str:
    prompt_key = Path(prompt_name).stem
    mapping = {
        "implement_request_change_request": "implementation",
        "bug_root_cause_investigation": "bug investigation",
        "code_review_patch_risk_audit": "code review",
        "test_case_development_meaningful_coverage": "test development",
        "security_privacy_risk_review": "security/privacy review",
        "documentation_accuracy_audit": "documentation update",
        "performance_latency_hotspot_audit": "performance audit",
        "repository_context_index_audit": "repository orientation",
    }
    return mapping.get(prompt_key, "general investigation")


def build_expert_packet(
    run_id: str,
    project: ProjectConfig,
    profile: ContextProfile,
    task: str,
    prompt_name: str,
    risk: str,
    search_terms: list[str],
    docs_read: list[Path],
    changed_files: list[Path],
    ranked_files: list[RankedFile],
    git_evidence: GitEvidence,
    missing_context: dict[str, list[str]],
    redaction_summary: RedactionSummary | None = None,
) -> str:
    task_type = classify_task(prompt_name)
    files_considered = [item.path for item in ranked_files]
    primary_references = files_considered[:PRIMARY_REFERENCE_LIMIT]
    excerpt_sources = files_considered[:EXCERPT_SOURCE_LIMIT]

    lines: list[str] = [
        "# Expert Packet",
        "",
        f"Run ID: `{run_id}`",
        f"Generated: `{datetime.now().isoformat(timespec='seconds')}`",
        f"Project: `{project.key}`",
        f"Task Type: `{task_type}`",
        f"Prompt: `{Path(prompt_name).stem}`",
        f"Risk: `{risk}`",
        f"Context Profile: `{profile.name}`",
        "",
        "## Task",
        "",
        task,
        "",
        "## Search Terms",
        "",
    ]

    if search_terms:
        for term in search_terms:
            lines.append(f"- `{term}`")
    else:
        lines.append("- No search terms derived from the task.")

    lines.extend(
        [
        "## Primary References",
        "",
        ]
    )

    for path in primary_references:
        lines.append(f"- `{relative_path(path, project.root)}`")

    lines.extend(
        [
            "",
            "## Evidence Summary",
            "",
            f"- Docs read: {len(docs_read)} (see `docs_read.txt`)",
            f"- Files considered: {len(files_considered)} (see `files_considered.txt` and `search_results.md`)",
            f"- Changed files provided: {len(changed_files)}",
            f"- Git evidence: {git_evidence.status} (see `git_diff.patch`)",
            "",
        ]
    )

    if changed_files:
        lines.append("## Changed Files Provided")
        lines.append("")
        for path in changed_files:
            lines.append(f"- `{relative_path(path, project.root)}`")
        lines.append("")

    lines.extend(
        [
            "## Top Files Considered",
            "",
        ]
    )
    top_ranked_files = ranked_files[:TOP_RANKED_FILE_LIMIT]
    if top_ranked_files:
        for ranked_file in top_ranked_files:
            relative = relative_path(ranked_file.path, project.root)
            line = f"- `{relative}` (score={ranked_file.score}"
            if ranked_file.matched_terms:
                line += f"; matched: {', '.join(ranked_file.matched_terms)}"
            line += ")"
            lines.append(line)
        if len(ranked_files) > len(top_ranked_files):
            lines.append(f"- ... {len(ranked_files) - len(top_ranked_files)} additional files listed in `files_considered.txt`")
    else:
        lines.append("- No files were considered from the selected context profile.")

    lines.extend(["", "## Evidence Excerpts", ""])
    for path in excerpt_sources:
        lines.append(f"### `{relative_path(path, project.root)}`")
        lines.append("")
        lines.append("```text")
        lines.append(read_excerpt(path, redaction_summary=redaction_summary))
        lines.append("```")
        lines.append("")

    if redaction_summary and redaction_summary.redactions_applied:
        lines.extend(
            [
                "## Redaction Note",
                "",
                f"- Sensitive-looking values were redacted {redaction_summary.redactions_applied} time(s) in packet excerpts.",
                "- Review source files directly if exact values are required and access is appropriate.",
                "",
            ]
        )

    lines.extend(["## Missing Context", ""])
    needs_review_notes = missing_context.get("needs_review", [])
    info_notes = missing_context.get("info", [])
    if not needs_review_notes and not info_notes:
        lines.append("- No missing context detected in this scout run.")
    else:
        lines.extend(["### Needs Review", ""])
        if needs_review_notes:
            for note in needs_review_notes:
                lines.append(f"- {note}")
        else:
            lines.append("- None.")
        lines.extend(["", "### Info", ""])
        if info_notes:
            for note in info_notes:
                lines.append(f"- {note}")
        else:
            lines.append("- None.")

    return "\n".join(lines).rstrip() + "\n"


def write_lines(file_path: Path, entries: list[str]) -> None:
    file_path.write_text("\n".join(entries).rstrip() + "\n", encoding="utf-8")


def write_json(file_path: Path, payload: dict[str, object]) -> None:
    file_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_missing_context(file_path: Path, missing_context: dict[str, list[str]]) -> None:
    lines = ["# Missing Context", ""]
    needs_review_notes = missing_context.get("needs_review", [])
    info_notes = missing_context.get("info", [])
    if needs_review_notes or info_notes:
        lines.extend(["## Needs Review", ""])
        if needs_review_notes:
            for note in needs_review_notes:
                lines.append(f"- {note}")
        else:
            lines.append("- None.")
        lines.extend(["", "## Info", ""])
        if info_notes:
            for note in info_notes:
                lines.append(f"- {note}")
        else:
            lines.append("- None.")
    else:
        lines.append("No missing context detected in this scout run.")
    file_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def evidence_label_for(ranked_file: RankedFile) -> str:
    if conflict_signals_for(ranked_file.path):
        return "CONFLICTING"
    if freshness_for(ranked_file.path).get("status") == "STALE":
        return "STALE"
    if any(boost.startswith("changed_file") or boost.startswith("prompt_file") for boost in ranked_file.boosts):
        return "DIRECT"
    if ranked_file.reason in {"Priority document from configured context", "Selected approved prompt"}:
        return "DIRECT"
    if ranked_file.matched_terms:
        return "INFERRED"
    return "INFERRED"


def write_missing_context_json(file_path: Path, missing_context: dict[str, list[str]]) -> None:
    needs_review = missing_context.get("needs_review", [])
    info = missing_context.get("info", [])
    write_json(
        file_path,
        {
            "schema_version": 2,
            "needs_review": needs_review,
            "info": info,
            "items": [
                {"severity": "needs_review", "evidence_label": "MISSING", "note": note}
                for note in needs_review
            ]
            + [
                {"severity": "info", "evidence_label": "INFERRED", "note": note}
                for note in info
            ],
            "evidence_labels": {
                "MISSING": needs_review,
                "INFERRED": info,
            },
        },
    )


def candidate_manifest_entries(project: ProjectConfig, ranked_files: list[RankedFile]) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for index, ranked_file in enumerate(ranked_files, start=1):
        freshness = freshness_for(ranked_file.path)
        conflict_signals = conflict_signals_for(ranked_file.path)
        entries.append(
            {
                "rank": index,
                "path": relative_path(ranked_file.path, project.root),
                "source_kind": source_kind_for(ranked_file.path, project.root),
                "score": ranked_file.score,
                "matched_terms": ranked_file.matched_terms,
                "boosts": ranked_file.boosts,
                "penalties": ranked_file.penalties,
                "reason": ranked_file.reason,
                "selection_provenance": selection_provenance_for(ranked_file),
                "freshness": freshness,
                "conflict_signals": conflict_signals,
                "evidence_label": evidence_label_for(ranked_file),
            }
        )
    return entries


def write_candidate_manifest(file_path: Path, project: ProjectConfig, ranked_files: list[RankedFile]) -> None:
    candidates = candidate_manifest_entries(project, ranked_files)
    label_counts = Counter(str(candidate["evidence_label"]) for candidate in candidates)
    source_kind_counts = Counter(str(candidate["source_kind"]) for candidate in candidates)
    write_json(
        file_path,
        {
            "schema_version": 2,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project": project.key,
            "candidate_count": len(ranked_files),
            "candidate_count_by_label": dict(label_counts),
            "candidate_count_by_source_kind": dict(source_kind_counts),
            "evidence_label_definitions": {
                "DIRECT": "Selected through explicit prompt, changed-file, or configured document evidence.",
                "INFERRED": "Selected by deterministic search or context-profile inclusion.",
                "MISSING": "Required context was absent and recorded in missing_context artifacts.",
                "STALE": "Candidate exists but is older than the configured freshness threshold.",
                "CONFLICTING": "Candidate contains deterministic conflict signals such as merge markers.",
            },
            "freshness_policy": {
                "stale_after_days": STALE_AFTER_DAYS,
            },
            "candidates": candidates,
        },
    )


def write_scout_run(
    file_path: Path,
    run_id: str,
    project: ProjectConfig,
    profile: ContextProfile,
    task: str,
    prompt_name: str,
    risk: str,
    search_terms: list[str],
    docs_read: list[Path],
    changed_files: list[Path],
    ranked_files: list[RankedFile],
    git_evidence: GitEvidence,
    missing_context: dict[str, list[str]],
    redaction_summary: RedactionSummary | None = None,
) -> None:
    labels = Counter(evidence_label_for(ranked_file) for ranked_file in ranked_files)
    if missing_context.get("needs_review"):
        labels["MISSING"] += len(missing_context["needs_review"])
    source_kind_counts = Counter(source_kind_for(ranked_file.path, project.root) for ranked_file in ranked_files)
    conflict_count = sum(1 for ranked_file in ranked_files if conflict_signals_for(ranked_file.path))
    stale_count = sum(1 for ranked_file in ranked_files if freshness_for(ranked_file.path).get("status") == "STALE")
    write_json(
        file_path,
        {
            "schema_version": 2,
            "run_id": run_id,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "project": project.key,
            "task": task,
            "task_type": classify_task(prompt_name),
            "prompt": Path(prompt_name).stem,
            "risk": risk,
            "context_profile": profile.name,
            "search_terms": search_terms,
            "docs_read_count": len(docs_read),
            "changed_files_count": len(changed_files),
            "candidate_count": len(ranked_files),
            "top_files": [relative_path(item.path, project.root) for item in ranked_files[:10]],
            "git_evidence_status": git_evidence.status,
            "missing_context_counts": {
                "needs_review": len(missing_context.get("needs_review", [])),
                "info": len(missing_context.get("info", [])),
            },
            "evidence_label_counts": dict(labels),
            "source_kind_counts": dict(source_kind_counts),
            "artifact_quality": {
                "has_direct_evidence": labels.get("DIRECT", 0) > 0,
                "has_inferred_evidence": labels.get("INFERRED", 0) > 0,
                "missing_review_count": len(missing_context.get("needs_review", [])),
                "stale_candidate_count": stale_count,
                "conflicting_candidate_count": conflict_count,
                "redactions_applied": 0 if redaction_summary is None else redaction_summary.redactions_applied,
                "semantic_ranking_enabled": False,
            },
            "semantic_ranking": {
                "enabled": False,
                "reason": "Deterministic Context Scout V1 keeps semantic ranking off by default.",
            },
        },
    )


def write_packet_budget(
    file_path: Path,
    expert_packet_text: str,
    docs_read: list[Path],
    ranked_files: list[RankedFile],
    git_evidence: GitEvidence,
    redaction_summary: RedactionSummary | None = None,
) -> None:
    truncated_sections: list[str] = []
    if len(ranked_files) > EXCERPT_SOURCE_LIMIT:
        truncated_sections.append("evidence_excerpts")
    if len(ranked_files) > PRIMARY_REFERENCE_LIMIT:
        truncated_sections.append("primary_references")
    if len(ranked_files) > TOP_RANKED_FILE_LIMIT:
        truncated_sections.append("top_ranked_files")
    if any(path.path.stat().st_size > SEARCH_TEXT_LIMIT for path in ranked_files if path.path.exists()):
        truncated_sections.append("searchable_text")
    write_json(
        file_path,
        {
            "schema_version": 2,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "expert_packet_chars": len(expert_packet_text),
            "expert_packet_lines": len(expert_packet_text.splitlines()),
            "docs_read_count": len(docs_read),
            "files_considered_count": len(ranked_files),
            "evidence_excerpt_count": min(len(ranked_files), EXCERPT_SOURCE_LIMIT),
            "primary_reference_count": min(len(ranked_files), PRIMARY_REFERENCE_LIMIT),
            "git_diff_chars": len(git_evidence.patch_text),
            "redactions_applied": 0 if redaction_summary is None else redaction_summary.redactions_applied,
            "limits": {
                "search_text_limit_chars_per_file": SEARCH_TEXT_LIMIT,
                "excerpt_source_limit": EXCERPT_SOURCE_LIMIT,
                "excerpt_max_lines_per_file": EXCERPT_MAX_LINES,
                "excerpt_max_chars_per_file": EXCERPT_MAX_CHARS,
                "primary_reference_limit": PRIMARY_REFERENCE_LIMIT,
                "top_ranked_file_limit": TOP_RANKED_FILE_LIMIT,
            },
            "truncated_sections": truncated_sections,
            "budget_status": "bounded" if truncated_sections else "within_limits",
            "semantic_ranking_enabled": False,
        },
    )


def write_initial_check_hints(
    file_path: Path,
    project: ProjectConfig,
    risk: str,
    ranked_files: list[RankedFile],
    missing_context: dict[str, list[str]],
    redaction_summary: RedactionSummary | None = None,
) -> None:
    conflict_count = sum(1 for ranked_file in ranked_files if conflict_signals_for(ranked_file.path))
    stale_count = sum(1 for ranked_file in ranked_files if freshness_for(ranked_file.path).get("status") == "STALE")
    lines = [
        "# Initial Check Hints",
        "",
        f"Project: `{project.key}`",
        f"Risk: `{risk}`",
        "",
        "## Suggested First Checks",
        "",
    ]
    if missing_context.get("needs_review"):
        lines.append("- Resolve `missing_context.md` Needs Review items before relying on the packet.")
    else:
        lines.append("- Review `expert_packet.md` and the top ranked files before making changes.")
    if ranked_files:
        lines.append(f"- Start with `{relative_path(ranked_files[0].path, project.root)}`.")
    if conflict_count:
        lines.append(f"- Review {conflict_count} conflicting candidate(s) in `candidate_manifest.json` before relying on excerpts.")
    if stale_count:
        lines.append(f"- Review {stale_count} stale candidate(s) in `candidate_manifest.json` for freshness risk.")
    if redaction_summary and redaction_summary.redactions_applied:
        lines.append("- Sensitive-looking values were redacted from scout packet excerpts; inspect source files only if exact values are needed.")
    lines.append("- The default workflow now attempts the selected provider automatically; use manual handoff only when the operator explicitly wants that boundary.")
    lines.extend(
        [
            "",
            "## Evidence Labels",
            "",
            "- `DIRECT`: selected by explicit prompt, docs, or changed-file evidence.",
            "- `INFERRED`: selected by deterministic search/ranking.",
            "- `MISSING`: required context is absent or review-blocking.",
            "- `STALE`: evidence may be low-confidence or outdated.",
            "- `CONFLICTING`: deterministic conflict signals such as merge markers were found.",
        ]
    )
    file_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def escape_markdown_cell(text: str) -> str:
    return text.replace("|", r"\|").replace("\n", " ")


def write_search_results(
    file_path: Path,
    run_id: str,
    project: ProjectConfig,
    search_terms: list[str],
    ranked_files: list[RankedFile],
) -> None:
    lines = [
        "# Search Results",
        "",
        f"Run ID: `{run_id}`",
        f"Project: `{project.key}`",
        "",
        "## Search Terms",
        "",
    ]

    if search_terms:
        for term in search_terms:
            lines.append(f"- `{term}`")
    else:
        lines.append("- No search terms derived.")

    lines.extend(
        [
            "",
            "## Ranked Files",
            "",
            "| Rank | File | Score | Matched | Boosts | Penalties | Reason |",
            "|---:|---|---:|---|---|---|---|",
        ]
    )

    for index, ranked_file in enumerate(ranked_files, start=1):
        relative = relative_path(ranked_file.path, project.root)
        matched = ", ".join(ranked_file.matched_terms) if ranked_file.matched_terms else "none"
        boosts = ", ".join(ranked_file.boosts) if ranked_file.boosts else "none"
        penalties = ", ".join(ranked_file.penalties) if ranked_file.penalties else "none"
        reason = ranked_file.reason or "none"
        lines.append(
            "| "
            f"{index} | {escape_markdown_cell(relative)} | {ranked_file.score} | "
            f"{escape_markdown_cell(matched)} | {escape_markdown_cell(boosts)} | "
            f"{escape_markdown_cell(penalties)} | {escape_markdown_cell(reason)} |"
        )

    if not ranked_files:
        lines.append("| 0 | none | 0 | none | none | none | No files were considered |")

    file_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def ensure_output_dir(project: ProjectConfig, requested_out_dir: str | None, task: str) -> tuple[str, Path]:
    if requested_out_dir:
        out_dir = resolve_cli_path(requested_out_dir, project.root)
        run_id = out_dir.name
    else:
        run_id = build_run_id(task)
        out_dir = project.runs_dir / run_id
    out_dir.mkdir(parents=True, exist_ok=True)
    return run_id, out_dir


def context_scout_payload(args: argparse.Namespace) -> dict[str, object]:
    project = load_project_config(args.project)
    profile_name = args.context_profile or project.default_context_profile
    profile = load_context_profile(profile_name)
    run_id, out_dir = ensure_output_dir(project, args.out_dir, args.task)

    missing_context = empty_missing_context()
    prompt_path = resolve_prompt_path(args.prompt, project.prompts_dir)
    docs_read = collect_docs(project, profile, prompt_path, args.docs, missing_context)
    changed_files = normalize_changed_files(args.changed_files, project.root, missing_context)
    search_terms = extract_search_terms(args.task, args.prompt, changed_files)
    ranked_files = rank_files_for_task(
        files=dedupe_paths(docs_read + changed_files + collect_candidate_files(project, profile)),
        project_root=project.root,
        search_terms=search_terms,
        docs_read=docs_read,
        changed_files=changed_files,
        prompt_path=prompt_path,
    )
    files_considered = [item.path for item in ranked_files]

    if not files_considered:
        add_missing_context(missing_context, "needs_review", "Context profile did not yield any candidate files.")

    git_evidence = collect_git_evidence(project.root, args.include_diff)
    for note in git_evidence.info_notes:
        add_missing_context(missing_context, "info", note)
    for note in git_evidence.review_notes:
        add_missing_context(missing_context, "needs_review", note)
    redaction_summary = RedactionSummary()
    redacted_patch_text, git_redaction_count = redact_sensitive_text(git_evidence.patch_text)
    redaction_summary.record(git_redaction_count)
    git_evidence = GitEvidence(
        status=git_evidence.status,
        patch_text=redacted_patch_text,
        info_notes=git_evidence.info_notes,
        review_notes=git_evidence.review_notes,
    )

    write_lines(
        out_dir / "docs_read.txt",
        [relative_path(path, project.root) for path in docs_read],
    )
    write_lines(
        out_dir / "files_considered.txt",
        [relative_path(path, project.root) for path in files_considered],
    )
    write_search_results(
        out_dir / "search_results.md",
        run_id=run_id,
        project=project,
        search_terms=search_terms,
        ranked_files=ranked_files,
    )
    (out_dir / "git_diff.patch").write_text(git_evidence.patch_text, encoding="utf-8")
    write_missing_context(out_dir / "missing_context.md", missing_context)
    write_missing_context_json(out_dir / "missing_context.json", missing_context)
    expert_packet_text = build_expert_packet(
        run_id=run_id,
        project=project,
        profile=profile,
        task=args.task,
        prompt_name=args.prompt,
        risk=args.risk,
        search_terms=search_terms,
        docs_read=docs_read,
        changed_files=changed_files,
        ranked_files=ranked_files,
        git_evidence=git_evidence,
        missing_context=missing_context,
        redaction_summary=redaction_summary,
    )
    (out_dir / "expert_packet.md").write_text(expert_packet_text, encoding="utf-8")
    write_candidate_manifest(out_dir / "candidate_manifest.json", project, ranked_files)
    write_scout_run(
        out_dir / "scout_run.json",
        run_id=run_id,
        project=project,
        profile=profile,
        task=args.task,
        prompt_name=args.prompt,
        risk=args.risk,
        search_terms=search_terms,
        docs_read=docs_read,
        changed_files=changed_files,
        ranked_files=ranked_files,
        git_evidence=git_evidence,
        missing_context=missing_context,
        redaction_summary=redaction_summary,
    )
    write_packet_budget(
        out_dir / "packet_budget.json",
        expert_packet_text,
        docs_read,
        ranked_files,
        git_evidence,
        redaction_summary=redaction_summary,
    )
    write_initial_check_hints(
        out_dir / "initial_check_hints.md",
        project,
        args.risk,
        ranked_files,
        missing_context,
        redaction_summary=redaction_summary,
    )

    return {
        "run_id": run_id,
        "project": args.project,
        "output_dir": str(out_dir),
        "docs_read": len(docs_read),
        "files_considered": len(files_considered),
        "git_status": git_evidence.status,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    payload = context_scout_payload(args)

    print(f"run_id={payload['run_id']}")
    print(f"output_dir={payload['output_dir']}")
    print(f"docs_read={payload['docs_read']}")
    print(f"files_considered={payload['files_considered']}")
    print(f"git_status={payload['git_status']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
