from __future__ import annotations

import fnmatch
from functools import lru_cache
from os import scandir
from pathlib import Path
from typing import Iterator


REPO_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = frozenset({".git", "out"})


@lru_cache(maxsize=4096)
def _segments_match(path_parts: tuple[str, ...], pattern_parts: tuple[str, ...]) -> bool:
    if not pattern_parts:
        return not path_parts
    if pattern_parts[0] == "**":
        return _segments_match(path_parts, pattern_parts[1:]) or (
            bool(path_parts) and _segments_match(path_parts[1:], pattern_parts)
        )
    return bool(path_parts) and fnmatch.fnmatchcase(path_parts[0], pattern_parts[0]) and (
        _segments_match(path_parts[1:], pattern_parts[1:])
    )


def _recursive_candidates(anchor: Path) -> Iterator[Path]:
    stack = [anchor]
    while stack:
        directory = stack.pop()
        with scandir(directory) as entries:
            for entry in entries:
                if entry.name in EXCLUDED_PARTS or entry.is_symlink():
                    continue
                path = Path(entry.path)
                if entry.is_dir(follow_symlinks=False):
                    stack.append(path)
                else:
                    yield path


def _fixed_depth_candidates(anchor: Path, depth: int) -> Iterator[Path]:
    frontier = [anchor]
    for current_depth in range(depth):
        next_frontier: list[Path] = []
        final_depth = current_depth == depth - 1
        for directory in frontier:
            for child in directory.iterdir():
                if child.is_symlink() or child.name in EXCLUDED_PARTS:
                    continue
                if final_depth or child.is_dir():
                    next_frontier.append(child)
        frontier = next_frontier
    return iter(frontier)


def path_or_glob_matches(pattern: str, root: Path = REPO_ROOT) -> bool:
    pattern_path = Path(pattern)
    if pattern_path.is_absolute() or ".." in pattern_path.parts:
        return False
    if EXCLUDED_PARTS & set(pattern_path.parts):
        return False

    try:
        resolved_root = root.resolve(strict=True)
    except (OSError, RuntimeError):
        return False

    if not any(char in pattern for char in "*?["):
        candidate = root
        for part in pattern_path.parts:
            candidate /= part
            if candidate.is_symlink():
                return False
        try:
            resolved_candidate = candidate.resolve(strict=True)
            return (
                candidate.is_file()
                and resolved_candidate.is_relative_to(resolved_root)
                and not (
                    EXCLUDED_PARTS
                    & set(resolved_candidate.relative_to(resolved_root).parts)
                )
            )
        except (OSError, RuntimeError):
            return False

    anchor_parts: list[str] = []
    for part in pattern_path.parts:
        if any(char in part for char in "*?["):
            break
        anchor_parts.append(part)

    anchor = root
    for part in anchor_parts:
        anchor /= part
        if anchor.is_symlink():
            return False
    if not anchor.is_dir():
        return False

    try:
        if not anchor.resolve(strict=True).is_relative_to(resolved_root):
            return False
        if "**" in pattern_path.parts:
            candidates = _recursive_candidates(anchor)
        else:
            candidates = _fixed_depth_candidates(
                anchor,
                len(pattern_path.parts) - len(anchor_parts),
            )
        for path in candidates:
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(root)
            if EXCLUDED_PARTS & set(relative.parts):
                continue
            if not path.resolve(strict=True).is_relative_to(resolved_root):
                continue
            if _segments_match(relative.parts, pattern_path.parts):
                return True
    except (OSError, RuntimeError):
        return False
    return False
