from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
src_root_text = str(SRC_ROOT)
if src_root_text in sys.path:
    sys.path.remove(src_root_text)
sys.path.insert(0, src_root_text)

from notary_kg.business_case_inventory import (  # noqa: E402
    CANONICAL_SLUGS,
    build_business_case_inventory,
    validate_business_case_inventory,
)


PROHIBITED_MARKERS = {
    "client_secret",
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "ghp_",
    "raw_mandate",
    "mandatsdaten",
}


def main() -> int:
    payload = build_business_case_inventory(REPO_ROOT)
    validation = validate_business_case_inventory(payload)
    errors = list(validation.errors)
    case_slugs = {entry.get("slug") for entry in payload.get("business_cases", [])}
    for slug in sorted(CANONICAL_SLUGS):
        if slug not in case_slugs:
            errors.append(f"canonical usecase missing: {slug}")

    storage = payload.get("storage_strategy", {})
    if storage.get("sharepoint_role") != "operative_mvp_data_store":
        errors.append("SharePoint must remain operative MVP data store")
    if storage.get("ontology_role") != "versioned_repo_catalog_and_projection_contract":
        errors.append("Ontology must remain a versioned repo projection contract")
    if storage.get("bpmn_role") != "process_model_not_runtime_engine":
        errors.append("BPMN must remain process model, not runtime engine")

    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    lowered = serialized.lower()
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in lowered:
            errors.append(f"prohibited marker found: {marker}")

    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print(
        "OK: Notarial business-case inventory covers canonical usecases "
        "with thin ontology sizing and SharePoint MVP storage boundaries."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
