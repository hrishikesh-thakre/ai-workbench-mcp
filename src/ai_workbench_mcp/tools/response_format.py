from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


SUMMARY_LABEL = "Summary:"
FILES_TOUCHED_LABEL = "Files touched:"
VALIDATION_RUN_LABEL = "Validation run:"
VALIDATION_NOT_RUN_LABEL = "Validation not run:"
RISKS_LABEL = "Risks / follow-ups:"

RESPONSE_SECTION_ORDER = (
    SUMMARY_LABEL,
    FILES_TOUCHED_LABEL,
    VALIDATION_RUN_LABEL,
    VALIDATION_NOT_RUN_LABEL,
    RISKS_LABEL,
)

REQUIRED_RESPONSE_MARKERS = (
    SUMMARY_LABEL,
    FILES_TOUCHED_LABEL,
    RISKS_LABEL,
)

TOOL_NOISE_PATTERNS = (
    r"^Ran \d+ commands?$",
    r"^Edited \d+ files?$",
    r"^\d+ files changed$",
    r"^Undo$",
)

FILE_REFERENCE_PATTERN = re.compile(
    r"(?P<path>(?:[A-Za-z]:[\\/])?[\w./\\-]+\.(?:md|py|yaml|yml|json|txt|toml|ini|cfg))"
)


@dataclass
class ResponseNormalizationResult:
    normalized_text: str | None
    normalization_notes: list[str]
    used_inferred_summary: bool
    used_inferred_files: bool


def read_text(file_path: Path) -> str:
    if not file_path.exists() or not file_path.is_file():
        return ""
    return file_path.read_text(encoding="utf-8", errors="replace")


WRAPPER_SECTION_HEADINGS = {
    "## Execution Metadata",
    "## Task Summary",
    "## Execution Notes",
    "## Manual Handoff",
    "## Awaiting Response",
    "## Captured Response",
    "## Normalized Response",
}


def get_markdown_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    collected: list[str] = []
    in_section = False
    for line in lines:
        if line.strip() == heading:
            in_section = True
            continue
        if in_section and line.strip() in WRAPPER_SECTION_HEADINGS:
            break
        if in_section:
            collected.append(line.rstrip())
    return "\n".join(collected).strip()


def extract_preferred_response_text(model_output_text: str) -> str:
    normalized = get_markdown_section(model_output_text, "## Normalized Response")
    if normalized:
        return normalized
    return get_markdown_section(model_output_text, "## Captured Response")


def _label_scan_text(stripped_line: str) -> str:
    return re.sub(r"^#{1,6}\s+", "", stripped_line).strip()


def _matched_label(stripped_line: str) -> str | None:
    normalized_line = _label_scan_text(stripped_line)
    for label in RESPONSE_SECTION_ORDER:
        label_name = label.rstrip(":")
        if normalized_line == label_name or normalized_line.startswith(label):
            return label
        if normalized_line.startswith(f"{label_name}:"):
            return label
    return None


def _strip_noise(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if cleaned and cleaned[-1] != "":
                cleaned.append("")
            continue
        if any(re.match(pattern, stripped) for pattern in TOOL_NOISE_PATTERNS):
            continue
        cleaned.append(stripped)
    while cleaned and cleaned[-1] == "":
        cleaned.pop()
    return cleaned


def _parse_sections(text: str) -> tuple[list[str], dict[str, list[str]]]:
    preamble: list[str] = []
    sections = {label: [] for label in RESPONSE_SECTION_ORDER}
    current_label: str | None = None

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        label = _matched_label(stripped)
        if label:
            current_label = label
            normalized_line = _label_scan_text(stripped)
            label_name = label.rstrip(":")
            if normalized_line == label_name:
                remainder = ""
            elif normalized_line.startswith(label):
                remainder = normalized_line[len(label) :].strip()
            else:
                remainder = normalized_line[len(label_name) :].lstrip(":").strip()
            if remainder:
                sections[label].append(remainder)
            continue

        if current_label is None:
            preamble.append(raw_line.rstrip())
        else:
            sections[current_label].append(raw_line.rstrip())

    return preamble, sections


def _clean_section_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        stripped = line.rstrip()
        if stripped.strip():
            cleaned.append(stripped)
    return cleaned


def _extract_file_references(text: str) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for match in FILE_REFERENCE_PATTERN.finditer(text):
        candidate = match.group("path").strip().rstrip(".,)")
        if candidate.lower().startswith("python tools/"):
            continue
        if candidate not in seen:
            seen.add(candidate)
            values.append(candidate)
    return values


def normalize_response_text(response_text: str) -> ResponseNormalizationResult:
    raw_text = response_text.strip()
    if not raw_text:
        return ResponseNormalizationResult(
            normalized_text=None,
            normalization_notes=["Response file is empty."],
            used_inferred_summary=False,
            used_inferred_files=False,
        )

    preamble, sections = _parse_sections(raw_text)
    summary_lines = _clean_section_lines(sections[SUMMARY_LABEL])
    files_lines = _clean_section_lines(sections[FILES_TOUCHED_LABEL])
    validation_run_lines = _clean_section_lines(sections[VALIDATION_RUN_LABEL])
    validation_not_run_lines = _clean_section_lines(sections[VALIDATION_NOT_RUN_LABEL])
    risks_lines = _clean_section_lines(sections[RISKS_LABEL])

    notes: list[str] = []
    used_inferred_summary = False
    used_inferred_files = False

    if not summary_lines:
        inferred_summary = _strip_noise(preamble)
        if inferred_summary:
            summary_lines = inferred_summary
            used_inferred_summary = True
            notes.append("Summary was inferred from leading response text.")

    if not files_lines:
        file_references = _extract_file_references(raw_text)
        if file_references:
            files_lines = [f"- {value}" for value in file_references]
            used_inferred_files = True
            notes.append("Files touched were inferred from file references in the captured response.")

    if not summary_lines or not files_lines or not risks_lines:
        return ResponseNormalizationResult(
            normalized_text=None,
            normalization_notes=notes,
            used_inferred_summary=used_inferred_summary,
            used_inferred_files=used_inferred_files,
        )

    if not validation_run_lines and not validation_not_run_lines:
        return ResponseNormalizationResult(
            normalized_text=None,
            normalization_notes=notes,
            used_inferred_summary=used_inferred_summary,
            used_inferred_files=used_inferred_files,
        )

    lines: list[str] = [SUMMARY_LABEL]
    lines.extend(summary_lines)
    lines.extend(["", FILES_TOUCHED_LABEL])
    lines.extend(files_lines)

    if validation_run_lines:
        lines.extend(["", VALIDATION_RUN_LABEL])
        lines.extend(validation_run_lines)

    if validation_not_run_lines:
        lines.extend(["", VALIDATION_NOT_RUN_LABEL])
        lines.extend(validation_not_run_lines)

    lines.extend(["", RISKS_LABEL])
    lines.extend(risks_lines)

    return ResponseNormalizationResult(
        normalized_text="\n".join(lines).strip() + "\n",
        normalization_notes=notes,
        used_inferred_summary=used_inferred_summary,
        used_inferred_files=used_inferred_files,
    )


def missing_required_sections(response_text: str) -> list[str]:
    present_markers = {
        label
        for line in response_text.splitlines()
        if (label := _matched_label(line.strip())) is not None
    }
    missing = [marker for marker in REQUIRED_RESPONSE_MARKERS if marker not in present_markers]
    if VALIDATION_RUN_LABEL not in present_markers and VALIDATION_NOT_RUN_LABEL not in present_markers:
        missing.append(f"{VALIDATION_RUN_LABEL} or {VALIDATION_NOT_RUN_LABEL}")
    return missing
