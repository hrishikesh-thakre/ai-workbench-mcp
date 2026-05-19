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
ADOPTION_GROUPS = ("github_workflow", "setup_doc")
BOOTSTRAP_GROUPS = (*DEFAULT_GROUPS, *ADOPTION_GROUPS)
GROUP_ALIASES = {"adoption": ADOPTION_GROUPS}
GITIGNORE_RUNS_ENTRY = "runs/"


@dataclass(frozen=True)
class AssetSpec:
    source_parts: tuple[str, ...]
    destination_parts: tuple[str, ...]


ASSET_GROUPS: dict[str, tuple[AssetSpec, ...]] = {
    "configs": (AssetSpec(("configs",), ("configs",)),),
    "prompts": (AssetSpec(("prompts",), ("prompts",)),),
    "recipes": (AssetSpec(("recipes",), ("recipes",)),),
    "github_workflow": (AssetSpec(("github", "workflows"), (".github", "workflows")),),
    "setup_doc": (AssetSpec(("docs",), ("docs",)),),
}
VALID_GROUPS = (*ASSET_GROUPS.keys(), *GROUP_ALIASES.keys(), "all")


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


def build_bootstrap_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Bootstrap AI Workbench adoption assets into an external repository."
    )
    parser.add_argument(
        "--target",
        default=".",
        help="Repository directory to bootstrap. Defaults to the current directory.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing asset files whose content differs from the packaged defaults.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report the planned bootstrap actions without writing files.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print a JSON summary instead of key=value lines.",
    )
    return parser


def package_assets_root():
    return resources.files(PACKAGE_NAME).joinpath(ASSETS_DIR_NAME)


def normalize_groups(
    groups: Sequence[str] | None,
    *,
    all_groups: Sequence[str] = DEFAULT_GROUPS,
) -> tuple[str, ...]:
    selected = tuple(groups or DEFAULT_GROUPS)
    if "all" in selected:
        selected = tuple(all_groups)

    expanded: list[str] = []
    for group in selected:
        if group in GROUP_ALIASES:
            expanded.extend(GROUP_ALIASES[group])
        else:
            expanded.append(group)

    unknown = sorted(set(expanded) - set(ASSET_GROUPS))
    if unknown:
        raise ValueError(f"Unknown asset group(s): {', '.join(unknown)}")

    ordered: list[str] = []
    for group in expanded:
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
        for asset_spec in ASSET_GROUPS[group]:
            group_root = root.joinpath(*asset_spec.source_parts)
            if not group_root.is_dir():
                raise FileNotFoundError(f"Packaged asset group is missing: {group}")
            yield from iter_resource_files(group_root, asset_spec.destination_parts)


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


def _gitignore_has_runs_entry(text: str) -> bool:
    return any(line.strip() == GITIGNORE_RUNS_ENTRY for line in text.splitlines())


def ensure_runs_gitignore_entry(
    target_dir: str | Path = ".",
    *,
    dry_run: bool = False,
) -> dict[str, str]:
    target_root = Path(target_dir).resolve()
    gitignore_path = target_root / ".gitignore"

    if gitignore_path.exists() and gitignore_path.is_dir():
        raise IsADirectoryError(f"Cannot update .gitignore because it is a directory: {gitignore_path}")

    if not gitignore_path.exists():
        action = "created"
        if not dry_run:
            target_root.mkdir(parents=True, exist_ok=True)
            gitignore_path.write_text(f"{GITIGNORE_RUNS_ENTRY}\n", encoding="utf-8")
        return {"path": ".gitignore", "action": action}

    text = gitignore_path.read_text(encoding="utf-8")
    if _gitignore_has_runs_entry(text):
        return {"path": ".gitignore", "action": "unchanged"}

    action = "appended"
    if not dry_run:
        separator = "" if not text or text.endswith(("\n", "\r")) else "\n"
        gitignore_path.write_text(f"{text}{separator}{GITIGNORE_RUNS_ENTRY}\n", encoding="utf-8")
    return {"path": ".gitignore", "action": action}


def bootstrap_repository(
    target_dir: str | Path = ".",
    *,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, object]:
    summary = bootstrap_assets(
        target_dir,
        groups=BOOTSTRAP_GROUPS,
        force=force,
        dry_run=dry_run,
    )
    summary["gitignore"] = ensure_runs_gitignore_entry(target_dir, dry_run=dry_run)
    return summary


def print_summary(summary: dict[str, object]) -> None:
    counts = summary["counts"]
    print(f"target_dir={summary['target_dir']}")
    print(f"groups={','.join(str(item) for item in summary['groups'])}")
    print(f"total={summary['total']}")
    for action in ("copied", "overwritten", "unchanged", "skipped"):
        print(f"{action}={counts[action]}")
    gitignore = summary.get("gitignore")
    if isinstance(gitignore, dict):
        print(f"gitignore={gitignore.get('action')}")
    if counts["skipped"]:
        print("skipped_note=existing files differ; rerun with --force to overwrite packaged asset files")


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
        print_summary(summary)

    return 2 if summary["counts"]["skipped"] else 0


def bootstrap_main() -> int:
    parser = build_bootstrap_parser()
    args = parser.parse_args()
    summary = bootstrap_repository(
        args.target,
        force=args.force,
        dry_run=args.dry_run,
    )

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print_summary(summary)

    return 2 if summary["counts"]["skipped"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
