from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
USECASES_ROOT = REPO_ROOT / "usecases"
KG_FILE_NAME = "knowledge-graph.graph.json"
KG_REVIEW_NAME = "knowledge-graph.md"
ALLOWED_STATUS = {"open", "in_progress", "provided", "blocked", "not_applicable"}
TOP10_SLUGS = {
    "immobilienkaufvertrag",
    "grundschuld-hypothekenbestellung",
    "online-gmbh-gruendung",
    "handelsregisteranmeldung",
    "unterschriftsbeglaubigung",
    "testament-erbvertrag",
    "erbscheinsantrag-nachlass",
    "vorsorgevollmacht-patientenverfuegung",
    "schenkungsvertrag-uebertragungsvertrag",
    "ehevertrag-scheidungsfolgenvereinbarung",
}
NEXT10_SLUGS = {
    "loeschungsbewilligung-grundbuchloeschung",
    "teilungserklaerung-weg",
    "bautraegervertrag",
    "gesellschafterbeschluss-gmbh-ug",
    "geschaeftsanteilsuebertragung-gmbh",
    "vereinsregisteranmeldung",
    "erbausschlagung",
    "pflichtteilsverzicht-erbverzicht",
    "adoption-familienrechtliche-erklaerungen",
    "vollmacht-immobilien-gesellschaftsgeschaefte",
}
CANONICAL_SLUGS = TOP10_SLUGS | NEXT10_SLUGS
REQUIRED_CASE_FIELDS = {
    "id",
    "slug",
    "title",
    "status",
    "usecase_path",
    "required_information",
    "documents",
    "decisions",
    "gates",
    "evidence",
    "edges",
}
PROHIBITED_MARKERS = {
    "api_key",
    "client_secret",
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "ghp_",
    "gho_",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_case(case: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    case_id = str(case.get("id", "<missing-id>"))
    for field in REQUIRED_CASE_FIELDS:
        if field not in case:
            errors.append(f"{case_id}: Pflichtfeld fehlt: {field}")

    usecase_path = case.get("usecase_path")
    if isinstance(usecase_path, str) and not (REPO_ROOT / usecase_path).exists():
        errors.append(f"{case_id}: usecase_path existiert nicht: {usecase_path}")

    required_information = case.get("required_information", [])
    if not isinstance(required_information, list) or len(required_information) < 6:
        errors.append(f"{case_id}: required_information braucht mindestens 6 Knoten")
    else:
        seen: set[str] = set()
        for item in required_information:
            item_id = item.get("id")
            if not isinstance(item_id, str) or not item_id:
                errors.append(f"{case_id}: required_information ohne id")
                continue
            if item_id in seen:
                errors.append(f"{case_id}: doppelte required_information id: {item_id}")
            seen.add(item_id)
            status = item.get("status")
            if status not in ALLOWED_STATUS:
                errors.append(f"{case_id}.{item_id}: ungueltiger status: {status}")
            if item.get("value") not in (None, "", [], {}):
                errors.append(f"{case_id}.{item_id}: value muss leer bleiben")

    for list_name in ["documents", "decisions", "gates", "evidence"]:
        value = case.get(list_name, [])
        if not isinstance(value, list) or not value:
            errors.append(f"{case_id}: {list_name} darf nicht leer sein")

    return errors


def usecase_dirs() -> list[Path]:
    return sorted(path for path in USECASES_ROOT.iterdir() if path.is_dir())


def validate_case_graph(usecase_dir: Path) -> tuple[list[str], set[str]]:
    errors: list[str] = []
    slugs: set[str] = set()
    slug = usecase_dir.name
    kg_file = usecase_dir / KG_FILE_NAME
    review_file = usecase_dir / KG_REVIEW_NAME

    if not review_file.exists():
        errors.append(f"{slug}: Pflicht-KG-Review fehlt: {review_file.relative_to(REPO_ROOT)}")

    if not kg_file.exists():
        errors.append(f"{slug}: Pflicht-KG fehlt: {kg_file.relative_to(REPO_ROOT)}")
    else:
        text = kg_file.read_text(encoding="utf-8")
        for marker in PROHIBITED_MARKERS:
            if marker.lower() in text.lower():
                errors.append(f"{kg_file.relative_to(REPO_ROOT)} enthaelt Marker: {marker}")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            errors.append(f"{kg_file.relative_to(REPO_ROOT)} ist kein gueltiges JSON: {exc}")
            payload = {}

        if payload.get("schema_version") != "noc.knowledge-graph/v0.1":
            errors.append(f"{slug}: KG schema_version muss noc.knowledge-graph/v0.1 sein")
        if payload.get("graph_id") != f"usecase.{slug}":
            errors.append(f"{slug}: graph_id muss usecase.{slug} sein")
        cases = payload.get("cases")
        if not isinstance(cases, list) or len(cases) != 1:
            errors.append(f"{slug}: Usecase-KG muss genau einen Case enthalten")
        else:
            ids: set[str] = set()
            for case in cases:
                case_id = case.get("id")
                if case_id in ids:
                    errors.append(f"Doppelte case id: {case_id}")
                ids.add(str(case_id))
                if isinstance(case.get("slug"), str):
                    slugs.add(str(case["slug"]))
                if case.get("slug") != slug:
                    errors.append(f"{slug}: Case-Slug muss zum Usecase-Ordner passen")
                if case.get("usecase_path") != f"usecases/{slug}":
                    errors.append(f"{slug}: usecase_path muss usecases/{slug} sein")
                errors.extend(validate_case(case))
    return errors, slugs


def main() -> int:
    errors: list[str] = []
    if (REPO_ROOT / "knowledge-graph").exists():
        errors.append("Zentraler knowledge-graph/ Ordner ist nicht erlaubt; KGs muessen unter usecases/<slug>/ liegen.")

    discovered_slugs: set[str] = set()
    for usecase_dir in usecase_dirs():
        graph_errors, graph_slugs = validate_case_graph(usecase_dir)
        errors.extend(graph_errors)
        discovered_slugs.update(graph_slugs)

    missing_slugs = CANONICAL_SLUGS - discovered_slugs
    if missing_slugs:
        errors.append(
            "Canonical Top-10/Next-10 Usecase-KGs fehlen: "
            + ", ".join(sorted(missing_slugs))
        )

    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print("OK: Usecase-lokale Knowledge-Graph-Baselines sind vorhanden und enthalten Top-10 plus Next-10.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
