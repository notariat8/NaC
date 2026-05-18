from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_SBOM_ROOT = REPO_ROOT / "sbom" / "ai"
REQUIRED_FILES = [
    AI_SBOM_ROOT / "nac-ai-sbom-draft.json",
]
REQUIRED_CLUSTERS = {
    "metadata",
    "system_level_properties",
    "models",
    "datasets",
    "infrastructure",
    "security_properties",
    "key_performance_indicators",
}
REQUIRED_INFRASTRUCTURE_IDS = {
    "local-nac-workspace",
    "local-development-toolchain",
    "local-plugin-development-toolchain",
    "local-notary-workstation-xnp-card-path",
}
PROHIBITED_MARKERS = {
    "api_key",
    "client_secret",
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "ghp_",
    "gho_",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"Pflicht-AI-SBOM fehlt: {path.relative_to(REPO_ROOT)}"]

    text = path.read_text(encoding="utf-8")
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in text.lower():
            errors.append(
                f"{path.relative_to(REPO_ROOT)} enthaelt unzulaessigen Marker: {marker}"
            )

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"{path.relative_to(REPO_ROOT)} ist kein gueltiges JSON: {exc}"]

    if payload.get("schema_version") != "nac.ai-sbom/v0.1":
        errors.append(f"{path.relative_to(REPO_ROOT)}: schema_version muss nac.ai-sbom/v0.1 sein")
    if payload.get("status") not in {"draft", "active", "release-bound"}:
        errors.append(f"{path.relative_to(REPO_ROOT)}: status ist ungueltig")

    clusters = payload.get("clusters")
    if not isinstance(clusters, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)}: clusters muss ein Objekt sein")
        return errors

    missing = sorted(REQUIRED_CLUSTERS - set(clusters))
    for cluster in missing:
        errors.append(f"{path.relative_to(REPO_ROOT)}: Cluster fehlt: {cluster}")

    infrastructure = clusters.get("infrastructure")
    if isinstance(infrastructure, list):
        infrastructure_ids = {
            item.get("id")
            for item in infrastructure
            if isinstance(item, dict)
        }
        missing_infrastructure = sorted(REQUIRED_INFRASTRUCTURE_IDS - infrastructure_ids)
        for item_id in missing_infrastructure:
            errors.append(
                f"{path.relative_to(REPO_ROOT)}: Infrastructure-Eintrag fehlt: {item_id}"
            )
    else:
        errors.append(f"{path.relative_to(REPO_ROOT)}: Cluster infrastructure muss eine Liste sein")

    return errors


def main() -> int:
    errors: list[str] = []
    for path in REQUIRED_FILES:
        errors.extend(validate_file(path))

    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print("OK: AI-SBOM-Baseline ist vorhanden und enthaelt die Pflichtcluster.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
