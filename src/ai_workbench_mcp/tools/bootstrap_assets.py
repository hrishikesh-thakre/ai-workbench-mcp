from __future__ import annotations

import argparse
from dataclasses import dataclass
from importlib import resources
import json
from pathlib import Path
from typing import Sequence


PACKAGE_NAME = "ai_workbench_mcp"
ASSETS_DIR_NAME = "assets"
DEFAULT_GROUPS = ("configs", "prompts", "recipes")
VALID_GROUPS = (*DEFAULT_GROUPS, "all")


@dataclass(frozen=True)
class BootstrapResult:
    path: str
    action: str


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Copy packaged AI Workbench repo assets into a target directory."
    )
    parser.add_argument(
        "--target-dir",
        default=".",
        help="Directory that should receive configs/, prompts/, and recipes/. Defaults to the current directory.",
    )
    parser.add_argument(
        "--groups",
        nargs="+",
        choices=VALID_GROUPS,
        default=list(DEFAULT_GROUPS),
        help="Asset groups to copy. Defaults to configs prompts recipes.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing files whose content differs from the packaged defaults.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the planned copy actions without writing files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a JSON summary instead of key=value lines.",
    )
    return parser


def package_assets_root():
    return resources.files(PACKAGE_NAME).joinpath(ASSETS_DIR_NAME)


def normalize_groups(groups: Sequence[str] | None) -> tuple[str, ...]:
    selected = tuple(groups or DEFAULT_GROUPS)
    if "all" in selected:
        return DEFAULT_GROUPS

    unknown = sorted(set(selected) - set(DEFAULT_GROUPS))
    if unknown:
        raise ValueError(f"Unknown asset group(s): {', '.join(unknown)}")

    ordered: list[str] = []
    for group in selected:
        if group not in ordered:
            ordered.append(group)
    return tuple(ordered)


def iter_resource_files(resource_root, rel_parts: tuple[str, ...] = ()):
    children = sorted(resource_root.iterdir(), key=lambda child: child.name)
    for child in children:
        child_rel_parts = (*rel_parts, child.name)
        if child.is_file():
            yield Path(*child_rel_parts), child
        elif child.is_dir():
            yield from iter_resource_files(child, child_rel_parts)


def iter_asset_files(groups: Sequence[str] | None = None):
    root = package_assets_root()
    if not root.is_dir():
        raise FileNotFoundError(f"Packaged asset directory is missing: {ASSETS_DIR_NAME}")

    for group in normalize_groups(groups):
        group_root = root.joinpath(group)
        if not group_root.is_dir():
            raise FileNotFoundError(f"Packaged asset group is missing: {group}")
        yield from iter_resource_files(group_root, (group,))


def bootstrap_assets(
    target_dir: str | Path = ".",
    *,
    groups: Sequence[str] | None = None,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, object]:
    target_root = Path(target_dir).resolve()
    selected_groups = normalize_groups(groups)
    if not dry_run:
        target_root.mkdir(parents=True, exist_ok=True)

    results: list[BootstrapResult] = []
    for relative_path, resource_file in iter_asset_files(selected_groups):
        destination = target_root / relative_path
        packaged_content = resource_file.read_bytes()

        if destination.exists() and destination.is_dir():
            raise IsADirectoryError(f"Cannot copy asset over directory: {destination}")

        if destination.exists() and destination.read_bytes() == packaged_content:
            action = "unchanged"
        elif destination.exists() and not force:
            action = "skipped"
        else:
            action = "overwritten" if destination.exists() else "copied"
            if not dry_run:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(packaged_content)

        results.append(BootstrapResult(path=relative_path.as_posix(), action=action))

    counts = {action: 0 for action in ("copied", "overwritten", "unchanged", "skipped")}
    for result in results:
        counts[result.action] = counts.get(result.action, 0) + 1

    return {
        "target_dir": str(target_root),
        "groups": list(selected_groups),
        "total": len(results),
        "counts": counts,
        "files": [result.__dict__ for result in results],
        "dry_run": dry_run,
    }


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    summary = bootstrap_assets(
        args.target_dir,
        groups=args.groups,
        force=args.force,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        counts = summary["counts"]
        print(f"target_dir={summary['target_dir']}")
        print(f"groups={','.join(str(item) for item in summary['groups'])}")
        print(f"total={summary['total']}")
        for action in ("copied", "overwritten", "unchanged", "skipped"):
            print(f"{action}={counts[action]}")
        if counts["skipped"]:
            print("skipped_note=existing files differ; rerun with --force to overwrite packaged asset files")

    return 2 if summary["counts"]["skipped"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
