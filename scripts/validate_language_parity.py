from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STANDARD_LANGUAGES = ("de", "en")
LOCALIZED_SURFACES = ("docs", "prompts")
LANGUAGE_CODE_PATTERN = re.compile(r"^[a-z]{2,3}$")
MARKDOWN_LINK_PATTERN = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
GERMAN_USECASE_MARKER = "Deutsch ist für diese Usecases die führende und rechtlich bindende Sprache"
GERMAN_ROOT_MARKER = "Deutsch ist repo-weit die führende Sprache"
TEXT_FILE_SUFFIXES = {".md", ".mdc", ".txt"}
GERMAN_TEXT_SUFFIXES = {".md", ".mdc", ".yaml", ".yml"}
GERMAN_TEXT_SCAN_FILES = (
    "README.md",
    "HERAUSGEBER.md",
    "AGENTS.md",
    ".github/copilot-instructions.md",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/ISSUE_TEMPLATE/compliance_change.md",
)
GERMAN_TEXT_SCAN_ROOTS = (
    ".cursor/rules",
    "docs/de",
    "plugins",
    "workflows",
    "usecases",
    "roadmap",
    "policies",
)
JSON_HUMAN_TEXT_FIELDS = {
    "about",
    "category",
    "description",
    "displayName",
    "shortDescription",
    "longDescription",
    "defaultPrompt",
    "title",
    "summary",
    "purpose",
    "privacy_rule",
    "label",
    "question",
    "source",
    "text",
    "prompt",
    "message",
    "warning",
}
GERMAN_ASCII_TRANSLITERATION_HINTS = (
    ("fuer", "für"),
    ("Fuer", "Für"),
    ("fuehr", "führ"),
    ("Fuehr", "Führ"),
    ("ueber", "über"),
    ("Ueber", "Über"),
    ("pruef", "prüf"),
    ("Pruef", "Prüf"),
    ("aender", "änder"),
    ("Aender", "Änder"),
    ("oeffent", "öffent"),
    ("Oeffent", "Öffent"),
    ("koenn", "könn"),
    ("Koenn", "Könn"),
    ("muess", "müss"),
    ("Muess", "Müss"),
    ("duerf", "dürf"),
    ("Duerf", "Dürf"),
    ("faeh", "fäh"),
    ("Faeh", "Fäh"),
    ("zulaess", "zuläss"),
    ("Zulaess", "Zuläss"),
    ("bestaet", "bestät"),
    ("Bestaet", "Bestät"),
    ("verstaend", "verständ"),
    ("Verstaend", "Verständ"),
    ("staend", "ständ"),
    ("Staend", "Ständ"),
    ("noet", "nöt"),
    ("Noet", "Nöt"),
    ("verfueg", "verfüg"),
    ("Verfueg", "Verfüg"),
    ("ergaenz", "ergänz"),
    ("Ergaenz", "Ergänz"),
    ("zurueck", "zurück"),
    ("Zurueck", "Zurück"),
    ("ausser", "außer"),
    ("Ausser", "Außer"),
    ("ausschliess", "ausschließ"),
    ("Ausschliess", "Ausschließ"),
    ("heisst", "heißt"),
    ("Heisst", "Heißt"),
    ("Geschaeft", "Geschäft"),
    ("geschaeft", "geschäft"),
    ("Erklaer", "Erklär"),
    ("erklaer", "erklär"),
    ("Loesch", "Lösch"),
    ("loesch", "lösch"),
    ("Gruend", "Gründ"),
    ("gruend", "gründ"),
    ("Uebersetz", "Übersetz"),
    ("uebersetz", "übersetz"),
    ("Qualitaet", "Qualität"),
    ("qualitaet", "qualität"),
    ("Identitaet", "Identität"),
    ("identitaet", "identität"),
    ("enthaelt", "enthält"),
    ("Enthaelt", "Enthält"),
    ("erhaelt", "erhält"),
    ("Erhaelt", "Erhält"),
    ("unterstuetz", "unterstütz"),
    ("Unterstuetz", "Unterstütz"),
    ("spaeter", "später"),
    ("Spaeter", "Später"),
    ("maessig", "mäßig"),
    ("Maessig", "Mäßig"),
    ("taeglich", "täglich"),
    ("Taeglich", "Täglich"),
    ("Buero", "Büro"),
    ("buero", "büro"),
    ("Buerger", "Bürger"),
    ("buerger", "bürger"),
    ("Kaeufer", "Käufer"),
    ("kaeufer", "käufer"),
    ("Verkaeufer", "Verkäufer"),
    ("verkaeufer", "verkäufer"),
    ("Maengel", "Mängel"),
    ("maengel", "mängel"),
    ("Nachlaesse", "Nachlässe"),
    ("nachlaesse", "nachlässe"),
    ("verknuepf", "verknüpf"),
    ("Verknuepf", "Verknüpf"),
    ("buendel", "bündel"),
    ("Buendel", "Bündel"),
    ("praezis", "präzis"),
    ("Praezis", "Präzis"),
    ("schaerf", "schärf"),
    ("Schaerf", "Schärf"),
    ("ursprueng", "ursprüng"),
    ("Ursprueng", "Ursprüng"),
    ("gueltig", "gültig"),
    ("Gueltig", "Gültig"),
    ("gewuensch", "gewünsch"),
    ("Gewuensch", "Gewünsch"),
    ("erfuell", "erfüll"),
    ("Erfuell", "Erfüll"),
    ("zugehoer", "zugehör"),
    ("Zugehoer", "Zugehör"),
    ("Vorschlaeg", "Vorschläg"),
    ("vorschlaeg", "vorschläg"),
    ("Geruest", "Gerüst"),
    ("geruest", "gerüst"),
    ("geoeffnet", "geöffnet"),
    ("spaet", "spät"),
    ("Spaet", "Spät"),
    ("zaehl", "zähl"),
    ("Zaehl", "Zähl"),
    ("Haert", "Härt"),
    ("haert", "härt"),
    ("aehn", "ähn"),
    ("Aehn", "Ähn"),
    ("plaetz", "plätz"),
    ("Plaetz", "Plätz"),
)
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
    "NaC usecase knowledge graph:",
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
SKILL_MD_REQUIRED_MARKERS = (
    "Deutsch ist die führende fachliche Skill-Sprache.",
    "Commands und IDs bleiben englisch/ASCII.",
    "## Englische Kurzfassung",
    "## Einsatzgrenze",
)
SKILL_MD_FORBIDDEN_MARKERS = (
    "description: Use ",
    "description: Inspect ",
    "## Operating Boundary",
    "## Allowed Work",
    "## Prohibited Work",
    "## Workflow",
    "## Output Shape",
    "## Source Plan",
    "Use this skill",
    "This plugin",
    "This installable",
    "Return concise sections named",
)
SKILL_FRONTMATTER_GERMAN_MARKERS = (
    "Nutzen,",
    "Nach ",
    "Zuerst nutzen",
    "Lokale ",
)
USECASE_README_REQUIRED_MARKERS = (
    "## Worum Es Geht",
    "## Was Heute Im Muster Enthalten Ist",
    "## Grenzen Für Den Betrieb",
    "## Plugin- Und Workflow-Bindung",
    "## Wie Man Diesen Usecase Prüft",
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


def localized_surface_language(path: Path) -> tuple[str, str] | None:
    resolved = path.resolve()
    for surface in LOCALIZED_SURFACES:
        for language in STANDARD_LANGUAGES:
            root = (REPO_ROOT / surface / language).resolve()
            try:
                resolved.relative_to(root)
            except ValueError:
                continue
            return surface, language
    return None


def resolve_markdown_target(source: Path, value: str) -> Path | None:
    target = value.strip().strip("<>")
    if (
        not target
        or target.startswith(("#", "http://", "https://", "mailto:"))
        or "://" in target
    ):
        return None

    target = target.split("#", maxsplit=1)[0].split("?", maxsplit=1)[0]
    if not target:
        return None

    if target.startswith("/"):
        return REPO_ROOT / target.lstrip("/")

    candidate = Path(target)
    if candidate.is_absolute():
        return candidate
    return source.parent / candidate


def validate_localized_markdown_link_languages() -> list[str]:
    errors: list[str] = []
    for surface in LOCALIZED_SURFACES:
        for language in STANDARD_LANGUAGES:
            root = REPO_ROOT / surface / language
            if not root.exists():
                continue

            for path in sorted(root.rglob("*.md")):
                text = path.read_text(encoding="utf-8")
                for line_number, line in enumerate(text.splitlines(), start=1):
                    for match in MARKDOWN_LINK_PATTERN.finditer(line):
                        target = resolve_markdown_target(path, match.group(1))
                        if target is None:
                            continue

                        target_language = localized_surface_language(target)
                        if target_language is None:
                            continue

                        _, linked_language = target_language
                        if linked_language != language:
                            rel_path = path.relative_to(REPO_ROOT).as_posix()
                            errors.append(
                                f"{rel_path}:{line_number}: Lokalisierter Markdown-Link "
                                f"muss im Sprachpfad {language} bleiben: {match.group(1)}"
                            )
    return errors


def _strip_markdown_technical_surfaces(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"https?://\S+", " ", text)

    def keep_human_link_label(match: re.Match[str]) -> str:
        label = match.group(1)
        if "/" in label or "." in label or re.fullmatch(r"[a-z0-9_.-]+", label):
            return " "
        return label

    return re.sub(r"!?\[([^\]]*)\]\([^)]+\)", keep_human_link_label, text)


def _find_ascii_transliteration(text: str) -> tuple[str, str] | None:
    for bad, good in GERMAN_ASCII_TRANSLITERATION_HINTS:
        if bad in text:
            return bad, good
    return None


def _scan_text_file_for_umlauts(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() in {".md", ".mdc"}:
        text = _strip_markdown_technical_surfaces(text)
    else:
        text = re.sub(r"https?://\S+", " ", text)

    for line_number, line in enumerate(text.splitlines(), start=1):
        match = _find_ascii_transliteration(line)
        if match is None:
            continue
        bad, good = match
        rel_path = path.relative_to(REPO_ROOT).as_posix()
        errors.append(
            f"{rel_path}:{line_number}: deutscher Menschentext nutzt {bad!r}; "
            f"bitte {good!r} nutzen oder als technischen Identifier in Code/Backticks führen."
        )
    return errors


def _scan_json_value_for_umlauts(value: object, rel_path: str, key: str | None = None) -> list[str]:
    errors: list[str] = []
    if isinstance(value, dict):
        for child_key, child in value.items():
            errors.extend(_scan_json_value_for_umlauts(child, rel_path, child_key))
    elif isinstance(value, list):
        for child in value:
            errors.extend(_scan_json_value_for_umlauts(child, rel_path, key))
    elif isinstance(value, str) and key in JSON_HUMAN_TEXT_FIELDS:
        match = _find_ascii_transliteration(value)
        if match is not None:
            bad, good = match
            errors.append(
                f"{rel_path}: JSON-Feld {key} nutzt {bad!r}; bitte {good!r} nutzen."
            )
    return errors


def validate_german_umlaut_usage() -> list[str]:
    errors: list[str] = []
    files: set[Path] = set()
    for rel_path in GERMAN_TEXT_SCAN_FILES:
        path = REPO_ROOT / rel_path
        if path.exists():
            files.add(path)

    for root_name in GERMAN_TEXT_SCAN_ROOTS:
        root = REPO_ROOT / root_name
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in GERMAN_TEXT_SUFFIXES:
                files.add(path)

    for path in sorted(files):
        errors.extend(_scan_text_file_for_umlauts(path))

    for root_name in (".agents", "plugins", "workflows", "usecases", "policies", "schemas", "sbom/ai"):
        root = REPO_ROOT / root_name
        if not root.exists():
            continue
        for json_file in sorted(root.rglob("*.json")):
            rel_path = json_file.relative_to(REPO_ROOT).as_posix()
            try:
                payload = json.loads(json_file.read_text(encoding="utf-8"))
            except ValueError:
                continue
            errors.extend(_scan_json_value_for_umlauts(payload, rel_path))
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
        "localized_navigation:",
        "localized_markdown_links_follow_source_language: true",
        "cross_language_markdown_links_allowed_in_localized_content: false",
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
        if not text.startswith("# NaC: Notariat as Code"):
            errors.append("README.md muss als deutscher GitHub-Root-README beginnen: # NaC: Notariat as Code")
        if GERMAN_ROOT_MARKER not in text:
            errors.append("README.md muss Deutsch als repo-weit führende Sprache nennen.")
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
            errors.append("usecases/README.md muss Deutsch als führende und rechtlich bindende Usecase-Sprache nennen.")
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


def validate_skill_language_rules() -> list[str]:
    errors: list[str] = []
    for root_name in ("plugins", "workflows"):
        for skill_file in sorted((REPO_ROOT / root_name).rglob("SKILL.md")):
            rel_path = skill_file.relative_to(REPO_ROOT).as_posix()
            text = skill_file.read_text(encoding="utf-8")
            description_line = next(
                (line for line in text.splitlines() if line.startswith("description: ")),
                "",
            )
            if description_line and not any(
                marker in description_line for marker in SKILL_FRONTMATTER_GERMAN_MARKERS
            ):
                errors.append(f"{rel_path} braucht deutsche Skill-Frontmatter-Beschreibung.")
            for marker in SKILL_MD_REQUIRED_MARKERS:
                if marker not in text:
                    errors.append(f"{rel_path} muss Skill-Sprachmarker enthalten: {marker}")
            for marker in SKILL_MD_FORBIDDEN_MARKERS:
                if marker in text:
                    errors.append(f"{rel_path} enthaelt englischen Skill-Altmarker: {marker}")
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
    errors.extend(validate_localized_markdown_link_languages())
    errors.extend(validate_domain_language_rules())
    errors.extend(validate_german_umlaut_usage())
    errors.extend(validate_usecase_kg_language_rules())
    errors.extend(validate_usecase_readme_language_rules())
    errors.extend(validate_plugin_workflow_language_rules())
    errors.extend(validate_skill_language_rules())

    if errors:
        print("STATUS: FAILED")
        print("ERROR: Sprachparitaet verletzt.")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print("OK: ISO-639-Sprachordner, de/en-Parität und sprachgleiche Links sind gepflegt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
