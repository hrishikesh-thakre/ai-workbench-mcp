from __future__ import annotations

from pathlib import Path
import re


def load_simple_yaml(file_path: Path) -> dict[str, object]:
    parsed_lines: list[tuple[int, str]] = []
    for raw_line in file_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        parsed_lines.append((indent, stripped))

    if not parsed_lines:
        return {}

    data, next_index = parse_yaml_block(parsed_lines, 0, parsed_lines[0][0])
    if next_index != len(parsed_lines):
        raise ValueError(f"Failed to fully parse YAML file: {file_path}")
    if not isinstance(data, dict):
        raise ValueError(f"Top-level YAML structure must be a mapping: {file_path}")
    return data


def parse_yaml_block(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[object, int]:
    current_indent, current_content = lines[index]
    if current_indent != indent:
        raise ValueError("Unexpected indentation in YAML content.")
    if current_content.startswith("- "):
        return parse_yaml_list(lines, index, indent)
    return parse_yaml_mapping(lines, index, indent)


def parse_yaml_mapping(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[dict[str, object], int]:
    mapping: dict[str, object] = {}
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if current_indent != indent:
            raise ValueError("Unsupported nested YAML mapping indentation.")
        if content.startswith("- "):
            break

        key, separator, value = content.partition(":")
        if not separator:
            raise ValueError(f"Invalid YAML mapping entry: {content}")

        key = key.strip()
        value = value.strip()
        index += 1

        if value:
            mapping[key] = parse_yaml_scalar(value)
            continue

        if index >= len(lines) or lines[index][0] <= current_indent:
            mapping[key] = {}
            continue

        nested_value, index = parse_yaml_block(lines, index, lines[index][0])
        mapping[key] = nested_value

    return mapping, index


def parse_yaml_list(lines: list[tuple[int, str]], index: int, indent: int) -> tuple[list[object], int]:
    items: list[object] = []
    while index < len(lines):
        current_indent, content = lines[index]
        if current_indent < indent:
            break
        if current_indent != indent or not content.startswith("- "):
            break

        item_text = content[2:].strip()
        index += 1

        if not item_text:
            if index >= len(lines) or lines[index][0] <= current_indent:
                items.append(None)
                continue
            nested_value, index = parse_yaml_block(lines, index, lines[index][0])
            items.append(nested_value)
            continue

        key, separator, value = item_text.partition(":")
        quoted_scalar = item_text.startswith(("'", '"')) and item_text.endswith(("'", '"')) and len(item_text) >= 2
        if separator and not quoted_scalar:
            item_mapping: dict[str, object] = {
                key.strip(): parse_yaml_scalar(value.strip()) if value.strip() else {}
            }
            if index < len(lines) and lines[index][0] > current_indent:
                nested_value, index = parse_yaml_block(lines, index, lines[index][0])
                if not isinstance(nested_value, dict):
                    raise ValueError("List item mappings may only contain flat nested mappings.")
                item_mapping.update(nested_value)
            items.append(item_mapping)
            continue

        items.append(parse_yaml_scalar(item_text))

    return items, index


def parse_yaml_scalar(value: str) -> object:
    lower_value = value.lower()
    if lower_value == "true":
        return True
    if lower_value == "false":
        return False
    if lower_value in {"null", "none", "~"}:
        return None
    if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
        return value[1:-1]
    if re.fullmatch(r"-?\d+", value):
        return int(value)
    if re.fullmatch(r"-?\d+\.\d+", value):
        return float(value)
    return value
