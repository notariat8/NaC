from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STANDARD_LANGUAGES = ("de", "en")
LOCALIZED_SURFACES = ("docs", "prompts")
LANGUAGE_CODE_PATTERN = re.compile(r"^[a-z]{2,3}$")


def collect_files(surface: str, language: str) -> set[str]:
    root = REPO_ROOT / surface / language
    if not root.exists():
        return set()
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }


def validate_language_roots() -> list[str]:
    errors: list[str] = []
    for surface in LOCALIZED_SURFACES:
        surface_root = REPO_ROOT / surface
        if not surface_root.exists():
            errors.append(f"Pflichtordner fehlt: {surface}/")
            continue

        for language_dir in surface_root.iterdir():
            if language_dir.is_dir() and language_dir.name not in STANDARD_LANGUAGES:
                if not LANGUAGE_CODE_PATTERN.fullmatch(language_dir.name):
                    errors.append(
                        f"{surface}/{language_dir.name} ist kein ISO-639-Sprachordner"
                    )

        for language in STANDARD_LANGUAGES:
            required_root = surface_root / language
            if not required_root.exists():
                errors.append(f"Pflicht-Sprachordner fehlt: {surface}/{language}")
    return errors


def validate_file_parity() -> list[str]:
    errors: list[str] = []
    for surface in LOCALIZED_SURFACES:
        by_language = {
            language: collect_files(surface, language)
            for language in STANDARD_LANGUAGES
        }
        expected = set().union(*by_language.values())
        for language, files in by_language.items():
            missing = sorted(expected - files)
            for rel_path in missing:
                errors.append(f"{surface}/{language}/{rel_path} fehlt")
    return errors


def main() -> int:
    errors = validate_language_roots()
    errors.extend(validate_file_parity())

    if errors:
        print("STATUS: FAILED")
        print("ERROR: Sprachparitaet verletzt.")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print("OK: ISO-639-Sprachordner und de/en-Paritaet sind gepflegt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
