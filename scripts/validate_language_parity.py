from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STANDARD_LANGUAGES = ("de", "en")
LOCALIZED_SURFACES = ("docs", "prompts")
LANGUAGE_CODE_PATTERN = re.compile(r"^[a-z]{2,3}$")
GERMAN_USECASE_MARKER = "Deutsch ist fuer diese Usecases die fuehrende und rechtlich bindende Sprache"
GERMAN_ROOT_MARKER = "Deutsch ist repo-weit die fuehrende Sprache"


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


def validate_domain_language_rules() -> list[str]:
    errors: list[str] = []
    policy_text = (REPO_ROOT / "policies" / "language-policy.yaml").read_text(encoding="utf-8")
    for required in (
        "repository_language:",
        "applies_to: all_repository_content",
        "root_readme_language: de",
        "github_project_page_language: de",
        "non_localized_human_content_defaults_to_german: true",
        "legal_domain_language:",
        "leading_language: de",
        "legally_binding_language: de",
        "usecases:",
        "default_language: de",
    ):
        if required not in policy_text:
            errors.append(f"Pflicht-Sprachregel fehlt in policies/language-policy.yaml: {required}")

    root_readme = REPO_ROOT / "README.md"
    if not root_readme.exists():
        errors.append("GitHub-Root-README fehlt: README.md")
    else:
        text = root_readme.read_text(encoding="utf-8")
        if not text.startswith("# NoC: Notariat as Code"):
            errors.append("README.md muss als deutscher GitHub-Root-README beginnen: # NoC: Notariat as Code")
        if GERMAN_ROOT_MARKER not in text:
            errors.append("README.md muss Deutsch als repo-weit fuehrende Sprache nennen.")
        if "This repository is maintained" in text:
            errors.append("README.md ist noch englisch formuliert.")

    usecase_index = REPO_ROOT / "usecases" / "README.md"
    if not usecase_index.exists():
        errors.append("Usecase-Index fehlt: usecases/README.md")
    else:
        text = usecase_index.read_text(encoding="utf-8")
        if not text.startswith("# Notarielle Usecases"):
            errors.append("usecases/README.md muss als deutscher Usecase-Index beginnen: # Notarielle Usecases")
        if GERMAN_USECASE_MARKER not in text:
            errors.append("usecases/README.md muss Deutsch als fuehrende und rechtlich bindende Usecase-Sprache nennen.")
        if "This directory contains concrete notarial usecases" in text:
            errors.append("usecases/README.md ist noch englisch formuliert.")
    return errors


def main() -> int:
    errors = validate_language_roots()
    errors.extend(validate_file_parity())
    errors.extend(validate_domain_language_rules())

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
