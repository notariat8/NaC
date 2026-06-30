from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_ai_sbom.export_mapping import load_export_mapping  # noqa: E402

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
REQUIRED_AGENT_TOOLING_CANDIDATE_IDS = {
    "ponytail-agent-tooling-candidate",
}
REQUIRED_PONYTAIL_BLOCKED_ACTIONS = {
    "install_codex_plugin_without_owner_apply",
    "enable_lifecycle_hooks_without_owner_apply",
    "activate_openclaw_skill_runtime_without_owner_apply",
    "run_on_mandate_data",
    "shorten_security_privacy_owner_gates_tests_or_validators",
    "grant_github_or_oci_write_from_target",
}
PROHIBITED_MARKERS = {
    "api_key",
    "client_secret",
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "ghp_",
    "gho_",
    "password=",
    "PIN:",
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

    errors.extend(validate_agent_tooling_candidates(path, clusters))
    return errors


def validate_agent_tooling_candidates(path: Path, clusters: dict) -> list[str]:
    errors: list[str] = []
    candidates = clusters.get("agent_tooling_candidates")
    if not isinstance(candidates, list) or not candidates:
        return [f"{path.relative_to(REPO_ROOT)}: Cluster agent_tooling_candidates fehlt"]

    by_id = {
        item.get("id"): item
        for item in candidates
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for item_id in sorted(REQUIRED_AGENT_TOOLING_CANDIDATE_IDS - set(by_id)):
        errors.append(f"{path.relative_to(REPO_ROOT)}: Agent-Tooling-Kandidat fehlt: {item_id}")

    ponytail = by_id.get("ponytail-agent-tooling-candidate")
    if not isinstance(ponytail, dict):
        return errors

    expected_values = {
        "upstream_repository": "https://github.com/DietrichGebert/ponytail",
        "observed_release": "v4.8.4",
        "license": "MIT",
        "status": "candidate_not_installed",
    }
    for key, expected in expected_values.items():
        if ponytail.get(key) != expected:
            errors.append(f"{path.relative_to(REPO_ROOT)}: Ponytail {key} muss {expected} sein")

    for key in (
        "installed_in_nac",
        "lifecycle_hooks_enabled",
        "runtime_activation_enabled",
        "personal_data_allowed",
        "matter_data_allowed",
        "secrets_allowed",
    ):
        if ponytail.get(key) is not False:
            errors.append(f"{path.relative_to(REPO_ROOT)}: Ponytail {key} muss false sein")

    blocked_actions = set(_string_list(ponytail.get("blocked_actions")))
    for action in sorted(REQUIRED_PONYTAIL_BLOCKED_ACTIONS - blocked_actions):
        errors.append(f"{path.relative_to(REPO_ROOT)}: Ponytail blocked_actions fehlt: {action}")

    owner_apply = set(_string_list(ponytail.get("owner_apply_required_before")))
    for gate in ("plugin_installation", "lifecycle_hook_activation", "openclaw_runtime_activation"):
        if gate not in owner_apply:
            errors.append(f"{path.relative_to(REPO_ROOT)}: Ponytail owner_apply_required_before fehlt: {gate}")

    surfaces = set(_string_list(ponytail.get("integration_surfaces")))
    for surface in ("codex_plugin", "openclaw_skill", "hermes_plugin"):
        if surface not in surfaces:
            errors.append(f"{path.relative_to(REPO_ROOT)}: Ponytail integration_surfaces fehlt: {surface}")

    return errors


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def main() -> int:
    errors: list[str] = []
    for path in REQUIRED_FILES:
        errors.extend(validate_file(path))
    try:
        load_export_mapping(REPO_ROOT)
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"AI-SBOM-Export-Mapping ungueltig: {exc}")

    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print("OK: AI-SBOM-Baseline und Export-Mapping sind vorhanden und enthalten die Pflichtcluster.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
