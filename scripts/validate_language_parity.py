from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STANDARD_LANGUAGES = ("de", "en")
LOCALIZED_SURFACES = ("docs", "prompts")
LANGUAGE_CODE_PATTERN = re.compile(r"^[a-z]{2,3}$")
GERMAN_USECASE_MARKER = "Deutsch ist fuer diese Usecases die fuehrende und rechtlich bindende Sprache"
GERMAN_ROOT_MARKER = "Deutsch ist repo-weit die fuehrende Sprache"
TEXT_FILE_SUFFIXES = {".md", ".mdc", ".txt"}
KG_MD_REQUIRED_MARKERS = (
    "Wissensgraph",
    "## Betriebsmodell",
    "## Offene Angabenknoten",
    "## Datenschutzregel",
)
KG_MD_FORBIDDEN_MARKERS = (
    "Knowledge Graph",
    "case-local static KG baseline",
    "Last update:",
    "Catalog group:",
    "Machine-readable KG:",
    "## Operating Model",
    "## Open Information Nodes",
    "## Review Gates",
    "## Privacy Rule",
    "This file is the human review view",
    "All `value` fields remain empty",
)
KG_JSON_FORBIDDEN_MARKERS = (
    "NoC usecase knowledge graph:",
    "Track open information",
    "All value fields are intentionally empty",
    "Real personal, property, health, estate, family or company data",
)
KG_JSON_TEXT_FIELDS = {"title", "summary", "purpose", "privacy_rule", "label", "question", "source"}
ENGLISH_QUESTION_STARTS = (
    "Which ",
    "Who ",
    "What ",
    "When ",
    "Where ",
    "How ",
    "Are ",
    "Is ",
    "Should ",
    "Does ",
    "Do ",
    "Can ",
)
PLUGIN_WORKFLOW_MD_FORBIDDEN_MARKERS = (
    "This directory",
    "This folder",
    "This plugin",
    "This workstream",
    "Install Boundary",
    "Required Accounts And Approvals",
    "Planned Layout",
    "Product Thesis",
    "Target Systems",
    "Runnable MVP",
    "Run the local",
    "Inspect a local",
    "Last update:",
    "Next gate",
    "Packaging Note",
    "Workflow Contracts",
    "Python Workflows",
    "## Scope",
    "## MVP-Scope",
)
USECASE_README_REQUIRED_MARKERS = (
    "## Worum Es Geht",
    "## Was Heute Im Muster Enthalten Ist",
    "## Grenzen Fuer Den Betrieb",
    "## Plugin- Und Workflow-Bindung",
    "## Wie Man Diesen Usecase Prueft",
)
USECASE_README_FORBIDDEN_MARKERS = (
    "## Goal",
    "## Scope",
    "## Out of Scope",
    "## Required Information Nodes",
    "## Documents and Evidence",
    "## Decisions",
    "## Gates",
    "## Plugin Dependencies",
    "## Workflow Dependencies",
    "## Delivery Tasks",
    "## Acceptance Criteria",
    "Source repository checked",
    "The source repository",
    "No real ",
    "No automated",
)


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


def validate_localized_text_is_not_copied() -> list[str]:
    errors: list[str] = []
    for surface in LOCALIZED_SURFACES:
        roots = {language: REPO_ROOT / surface / language for language in STANDARD_LANGUAGES}
        shared = collect_files(surface, "de") & collect_files(surface, "en")
        for rel_path in sorted(shared):
            if Path(rel_path).suffix.lower() not in TEXT_FILE_SUFFIXES:
                continue

            de_text = (roots["de"] / rel_path).read_text(encoding="utf-8").strip()
            en_text = (roots["en"] / rel_path).read_text(encoding="utf-8").strip()
            if de_text and de_text == en_text:
                errors.append(
                    f"{surface}/de/{rel_path} und {surface}/en/{rel_path} sind identisch; "
                    "Uebersetzung oder explizite englische Orientierung fehlt"
                )
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


def validate_usecase_kg_language_rules() -> list[str]:
    errors: list[str] = []
    for review_file in sorted((REPO_ROOT / "usecases").glob("*/knowledge-graph.md")):
        rel_path = review_file.relative_to(REPO_ROOT).as_posix()
        text = review_file.read_text(encoding="utf-8")
        for marker in KG_MD_REQUIRED_MARKERS:
            if marker not in text:
                errors.append(f"{rel_path} muss deutschen KG-Marker enthalten: {marker}")
        for marker in KG_MD_FORBIDDEN_MARKERS:
            if marker in text:
                errors.append(f"{rel_path} enthaelt englischen KG-Altmarker: {marker}")

    for graph_file in sorted((REPO_ROOT / "usecases").glob("*/knowledge-graph.graph.json")):
        rel_path = graph_file.relative_to(REPO_ROOT).as_posix()
        payload = graph_file.read_text(encoding="utf-8")
        for marker in KG_JSON_FORBIDDEN_MARKERS:
            if marker in payload:
                errors.append(f"{rel_path} enthaelt englischen KG-Altmarker: {marker}")
        try:
            graph = json.loads(payload)
        except ValueError:
            continue
        errors.extend(_validate_kg_text_fields(graph, rel_path))
    return errors


def validate_plugin_workflow_language_rules() -> list[str]:
    errors: list[str] = []
    for root_name in ("plugins", "workflows"):
        for md_file in sorted((REPO_ROOT / root_name).rglob("*.md")):
            rel_path = md_file.relative_to(REPO_ROOT)
            if "skills" in rel_path.parts:
                continue
            text = md_file.read_text(encoding="utf-8")
            for marker in PLUGIN_WORKFLOW_MD_FORBIDDEN_MARKERS:
                if marker in text:
                    errors.append(
                        f"{rel_path.as_posix()} enthaelt englischen Plugin-/Workflow-Altmarker: {marker}"
                    )
    return errors


def validate_usecase_readme_language_rules() -> list[str]:
    errors: list[str] = []
    for readme_file in sorted((REPO_ROOT / "usecases").glob("*/README.md")):
        rel_path = readme_file.relative_to(REPO_ROOT).as_posix()
        text = readme_file.read_text(encoding="utf-8")
        for marker in USECASE_README_REQUIRED_MARKERS:
            if marker not in text:
                errors.append(f"{rel_path} muss deutschen Usecase-README-Marker enthalten: {marker}")
        for marker in USECASE_README_FORBIDDEN_MARKERS:
            if marker in text:
                errors.append(f"{rel_path} enthaelt englischen Usecase-README-Altmarker: {marker}")
    return errors


def _validate_kg_text_fields(value: object, rel_path: str) -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in KG_JSON_TEXT_FIELDS and isinstance(child, str):
                if child.startswith(ENGLISH_QUESTION_STARTS):
                    errors.append(
                        f"{rel_path}: Feld {key} beginnt mit englischer Frageformulierung"
                    )
            errors.extend(_validate_kg_text_fields(child, rel_path))
    elif isinstance(value, list):
        for item in value:
            errors.extend(_validate_kg_text_fields(item, rel_path))
    return errors


def main() -> int:
    errors = validate_language_roots()
    errors.extend(validate_file_parity())
    errors.extend(validate_localized_text_is_not_copied())
    errors.extend(validate_domain_language_rules())
    errors.extend(validate_usecase_kg_language_rules())
    errors.extend(validate_usecase_readme_language_rules())
    errors.extend(validate_plugin_workflow_language_rules())

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
