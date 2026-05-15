from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CODE_SPAN_PATTERN = re.compile(r"`([^`\n]+)`")
MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def target_files() -> list[Path]:
    files = {
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / ".github" / "copilot-instructions.md",
    }
    files.update((REPO_ROOT / ".cursor" / "rules").glob("*.mdc"))
    for language in ("de", "en"):
        root = REPO_ROOT / "docs" / language
        files.add(root / "README.md")
        files.add(root / "START_HERE.md")
        files.update(root.rglob("README.md"))
    return sorted(path for path in files if path.exists())


def looks_like_doc_reference(value: str) -> bool:
    if " " in value or value.startswith(("http://", "https://")):
        return False
    if "/" not in value and not value.endswith(".md"):
        return False
    return not any(char in value for char in "<>{}|")


def reference_exists(path: Path, value: str) -> bool:
    normalized = value.rstrip("/")
    if not normalized:
        return False
    candidates = [
        REPO_ROOT / normalized,
        path.parent / normalized,
    ]
    return any(candidate.exists() for candidate in candidates)


def markdown_link_exists(path: Path, value: str) -> bool:
    target = value.strip().strip("<>")
    if (
        not target
        or target.startswith(("#", "http://", "https://", "mailto:"))
        or "://" in target
    ):
        return True

    target = target.split("#", maxsplit=1)[0].split("?", maxsplit=1)[0].rstrip("/")
    if not target:
        return True

    if Path(target).is_absolute():
        candidate = Path(target)
    else:
        candidate = path.parent / target
    return candidate.exists()


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    for line_number, line in enumerate(text.splitlines(), start=1):
        for match in CODE_SPAN_PATTERN.finditer(line):
            value = match.group(1).strip()
            if looks_like_doc_reference(value) and reference_exists(path, value):
                rel_path = path.relative_to(REPO_ROOT).as_posix()
                errors.append(
                    f"{rel_path}:{line_number}: Repo-Verweis als Markdown-Link statt Code-Span fuehren: {value}"
                )
        for match in MARKDOWN_LINK_PATTERN.finditer(line):
            value = match.group(1).strip()
            if not markdown_link_exists(path, value):
                rel_path = path.relative_to(REPO_ROOT).as_posix()
                errors.append(
                    f"{rel_path}:{line_number}: Interner Markdown-Link zeigt auf kein vorhandenes Ziel: {value}"
                )
    return errors


def main() -> int:
    errors: list[str] = []
    for path in target_files():
        errors.extend(validate_file(path))

    if errors:
        print("STATUS: FAILED")
        print("ERROR: Interne Repo-Verweise in README-/Index-/Agentenregel-Dateien muessen klickbare Markdown-Links sein.")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print("OK: README-/Index-/Agentenregel-Dateien nutzen klickbare Links fuer interne Repo-Verweise.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
