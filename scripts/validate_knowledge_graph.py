from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
KG_ROOT = REPO_ROOT / "knowledge-graph"
KG_FILE = KG_ROOT / "notarial-top10.graph.json"
KG_REVIEW_FILE = KG_ROOT / "notarial-top10.md"
ALLOWED_STATUS = {"open", "in_progress", "provided", "blocked", "not_applicable"}
EXPECTED_SLUGS = {
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


def main() -> int:
    errors: list[str] = []
    if not KG_REVIEW_FILE.exists():
        errors.append(f"Pflicht-KG-Review fehlt: {KG_REVIEW_FILE.relative_to(REPO_ROOT)}")

    if not KG_FILE.exists():
        errors.append(f"Pflicht-KG fehlt: {KG_FILE.relative_to(REPO_ROOT)}")
    else:
        text = KG_FILE.read_text(encoding="utf-8")
        for marker in PROHIBITED_MARKERS:
            if marker.lower() in text.lower():
                errors.append(f"{KG_FILE.relative_to(REPO_ROOT)} enthaelt Marker: {marker}")
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            errors.append(f"{KG_FILE.relative_to(REPO_ROOT)} ist kein gueltiges JSON: {exc}")
            payload = {}

        if payload.get("schema_version") != "noc.knowledge-graph/v0.1":
            errors.append("KG schema_version muss noc.knowledge-graph/v0.1 sein")
        cases = payload.get("cases")
        if not isinstance(cases, list) or len(cases) < 10:
            errors.append("KG muss mindestens 10 notarielle Usecases enthalten")
        else:
            ids: set[str] = set()
            slugs: set[str] = set()
            for case in cases:
                case_id = case.get("id")
                if case_id in ids:
                    errors.append(f"Doppelte case id: {case_id}")
                ids.add(str(case_id))
                if isinstance(case.get("slug"), str):
                    slugs.add(str(case["slug"]))
                errors.extend(validate_case(case))
            missing_slugs = EXPECTED_SLUGS - slugs
            extra_slugs = slugs - EXPECTED_SLUGS
            if missing_slugs:
                errors.append(
                    "KG enthaelt nicht alle erwarteten Top-10-Slugs: "
                    + ", ".join(sorted(missing_slugs))
                )
            if extra_slugs:
                errors.append(
                    "KG enthaelt nicht-katalogisierte Top-10-Slugs: "
                    + ", ".join(sorted(extra_slugs))
                )

    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print("OK: Knowledge-Graph-Baseline ist vorhanden und enthaelt die Top-10-Usecases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
