from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "codex-parallel-review.contract.json"
CONFIG_PATH = REPO_ROOT / ".codex" / "config.toml"
AGENT_DIR = REPO_ROOT / ".codex" / "agents"
REQUIRED_AGENT_NAMES = {
    "nac_scope_mapper",
    "nac_kg_reviewer",
    "nac_bpmn_reviewer",
    "nac_policy_reviewer",
    "nac_docs_parity_reviewer",
    "nac_validation_reviewer",
}
REQUIRED_FALSE_GUARDRAILS = {
    "productive_write_without_user_approval",
    "real_mandate_data_allowed",
    "external_ai_processing_without_avv_dpa_gate",
    "kg_auto_merge_allowed",
    "notarial_truth_from_model_output",
    "secret_oci_apply_release_destructive_delegation_allowed",
}
REQUIRED_TRUE_GUARDRAILS = {
    "agent_profiles_read_only_by_default",
    "human_review_required",
    "git_diff_required",
    "fresh_validation_required",
    "parallel_review_default_when_net_benefit_expected",
    "lead_agent_keeps_ownership",
}
REQUIRED_DEFAULT_POLICY_TRUE_KEYS = {
    "use_when_net_benefit_expected",
    "lead_agent_keeps_ownership",
    "subagents_read_only_by_default",
    "single_owner_for_secrets_oci_apply_release_and_destructive_actions",
}
REQUIRED_DEFAULT_POLICY_DIMENSIONS = {
    "layer_count",
    "risk_level",
    "independent_review_perspectives",
    "validation_surface",
    "coordination_cost",
}
REQUIRED_PROHIBITED_DELEGATIONS = {
    "secrets",
    "certificate_private_material",
    "real_mandate_data",
    "productive_m365_writes",
    "entra_app_credentials",
    "release_apply",
    "destructive_git_cleanup",
}
REQUIRED_VALIDATION_COMMANDS = {
    "python scripts/validate_codex_parallel_review.py",
    "python scripts/validate_language_parity.py",
    "python scripts/validate_governance_sync.py",
}
PROHIBITED_MARKERS = {
    "client" + "_secret",
    "BEGIN " + "PRIVATE KEY",
    "BEGIN " + "CERTIFICATE",
    "gh" + "p_",
    "gh" + "o_",
    "secret_link_value",
    "real_mandate_data_sample",
}


def validate_contract(path: Path = CONTRACT_PATH) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"Pflichtvertrag fehlt: {path.relative_to(REPO_ROOT)}"]

    text = path.read_text(encoding="utf-8")
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in text.lower():
            errors.append(f"{path.relative_to(REPO_ROOT)} enthaelt unzulaessigen Marker: {marker}")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"{path.relative_to(REPO_ROOT)} ist kein gueltiges JSON: {exc}"]

    if payload.get("schema_version") != "nac.workflow-contract/v0.1":
        errors.append("schema_version muss nac.workflow-contract/v0.1 sein")
    if payload.get("contract_id") != "workflow.codex_parallel_review":
        errors.append("contract_id muss workflow.codex_parallel_review sein")
    if payload.get("status") not in {"pilot_ready", "active_mvp"}:
        errors.append("status muss pilot_ready oder active_mvp sein")

    guardrails = payload.get("guardrails")
    if not isinstance(guardrails, dict):
        errors.append("guardrails muss ein Objekt sein")
    else:
        for key in sorted(REQUIRED_FALSE_GUARDRAILS):
            if guardrails.get(key) is not False:
                errors.append(f"guardrails.{key} muss false sein")
        for key in sorted(REQUIRED_TRUE_GUARDRAILS):
            if guardrails.get(key) is not True:
                errors.append(f"guardrails.{key} muss true sein")

    default_policy = payload.get("default_policy")
    if not isinstance(default_policy, dict):
        errors.append("default_policy muss ein Objekt sein")
    else:
        for key in sorted(REQUIRED_DEFAULT_POLICY_TRUE_KEYS):
            if default_policy.get(key) is not True:
                errors.append(f"default_policy.{key} muss true sein")
        dimensions = set(_string_list(default_policy.get("assessment_dimensions")))
        for dimension in sorted(REQUIRED_DEFAULT_POLICY_DIMENSIONS - dimensions):
            errors.append(f"default_policy.assessment_dimensions fehlt: {dimension}")

    operating_gate = payload.get("subagent_operating_gate")
    if not isinstance(operating_gate, dict):
        errors.append("subagent_operating_gate muss ein Objekt sein")
    else:
        expected_values = {
            "exact_agent_registry_required": True,
            "rogue_agent_profiles_allowed": False,
            "worker_agents_allowed_for_disjoint_write_scopes": True,
            "explorer_agents_read_only_by_default": True,
            "lead_agent_integrates_results": True,
            "max_threads": 6,
            "max_depth": 1,
            "job_max_runtime_seconds": 1800,
        }
        for key, expected in expected_values.items():
            if operating_gate.get(key) != expected:
                errors.append(f"subagent_operating_gate.{key} muss {expected!r} sein")
        prohibited_delegations = set(_string_list(operating_gate.get("prohibited_delegations")))
        for missing in sorted(REQUIRED_PROHIBITED_DELEGATIONS - prohibited_delegations):
            errors.append(f"subagent_operating_gate.prohibited_delegations fehlt: {missing}")
        thresholds = operating_gate.get("batch_thresholds")
        if not isinstance(thresholds, dict):
            errors.append("subagent_operating_gate.batch_thresholds muss ein Objekt sein")
        elif thresholds.get("use_subagents_when_independent_questions") != 2:
            errors.append("subagent_operating_gate.batch_thresholds.use_subagents_when_independent_questions muss 2 sein")

    progressive_disclosure = payload.get("progressive_disclosure")
    if not isinstance(progressive_disclosure, dict):
        errors.append("progressive_disclosure muss ein Objekt sein")
    else:
        if progressive_disclosure.get("context_index") != "agent-context/index.json":
            errors.append("progressive_disclosure.context_index muss agent-context/index.json sein")
        for field in ("always_on", "scoped", "on_demand", "runtime"):
            if not _string_list(progressive_disclosure.get(field)):
                errors.append(f"progressive_disclosure.{field} muss eine nicht leere String-Liste sein")

    verification_contracts = set(_string_list(payload.get("verification_contracts")))
    if "workflows/verification-contracts/codex-agent-context.verification.json" not in verification_contracts:
        errors.append("verification_contracts muss codex-agent-context.verification.json referenzieren")

    agent_profiles = payload.get("agent_profiles")
    if not isinstance(agent_profiles, list) or not agent_profiles:
        errors.append("agent_profiles muss eine nicht leere Liste sein")
    else:
        seen_names: set[str] = set()
        for index, profile in enumerate(agent_profiles, start=1):
            if not isinstance(profile, dict):
                errors.append(f"agent_profiles[{index}] muss ein Objekt sein")
                continue
            name = profile.get("name")
            path_value = profile.get("path")
            if not isinstance(name, str) or not name:
                errors.append(f"agent_profiles[{index}].name muss gesetzt sein")
                continue
            if name in seen_names:
                errors.append(f"Agentprofil doppelt: {name}")
            seen_names.add(name)
            if profile.get("sandbox_mode") != "read-only":
                errors.append(f"{name}: sandbox_mode muss read-only sein")
            if not isinstance(path_value, str) or not path_value:
                errors.append(f"{name}: path muss gesetzt sein")
                continue
            agent_path = REPO_ROOT / path_value
            errors.extend(_validate_agent_file(agent_path, name))

        for missing in sorted(REQUIRED_AGENT_NAMES - seen_names):
            errors.append(f"agent_profiles fehlt: {missing}")
        if seen_names != REQUIRED_AGENT_NAMES:
            extra = seen_names - REQUIRED_AGENT_NAMES
            for name in sorted(extra):
                errors.append(f"agent_profiles enthaelt nicht registriertes Profil: {name}")

    for field in ("allowed_inputs", "prohibited_inputs", "review_gates", "evidence_fields"):
        if not _string_list(payload.get(field)):
            errors.append(f"{field} muss eine nicht leere String-Liste sein")

    commands = set(_string_list(payload.get("validation_commands")))
    for command in sorted(REQUIRED_VALIDATION_COMMANDS - commands):
        errors.append(f"validation_commands fehlt: {command}")

    prohibited_inputs = set(_string_list(payload.get("prohibited_inputs")))
    for marker in ("PINs", "Tokens", "echte Mandatsdaten"):
        if marker not in prohibited_inputs:
            errors.append(f"prohibited_inputs fehlt: {marker}")

    return errors


def validate_codex_config(path: Path = CONFIG_PATH) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"Codex-Projektkonfiguration fehlt: {path.relative_to(REPO_ROOT)}"]

    text = path.read_text(encoding="utf-8")
    if "[agents]" not in text:
        errors.append(".codex/config.toml braucht [agents]")
    if "max_threads = 6" not in text:
        errors.append(".codex/config.toml soll agents.max_threads = 6 setzen")
    if "max_depth = 1" not in text:
        errors.append(".codex/config.toml soll agents.max_depth = 1 setzen")
    if "job_max_runtime_seconds = 1800" not in text:
        errors.append(".codex/config.toml soll agents.job_max_runtime_seconds = 1800 setzen")
    return errors


def validate_agent_registry(path: Path = AGENT_DIR) -> list[str]:
    errors: list[str] = []
    if not path.is_dir():
        return [f"Agentprofilordner fehlt: {path.relative_to(REPO_ROOT)}"]
    actual = {item.stem.replace("-", "_") for item in path.glob("*.toml")}
    expected = {name.replace("_", "_") for name in REQUIRED_AGENT_NAMES}
    for missing in sorted(expected - actual):
        errors.append(f"Agentprofil-Datei fehlt fuer Registry-Eintrag: {missing}")
    for extra in sorted(actual - expected):
        errors.append(f"Nicht registriertes Agentprofil gefunden: {extra}")
    return errors


def _validate_agent_file(path: Path, expected_name: str) -> list[str]:
    errors: list[str] = []
    rel_path = path.relative_to(REPO_ROOT).as_posix()
    if not path.is_file():
        return [f"Agentprofil fehlt: {rel_path}"]

    text = path.read_text(encoding="utf-8")
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in text.lower():
            errors.append(f"{rel_path} enthaelt unzulaessigen Marker: {marker}")
    if f'name = "{expected_name}"' not in text:
        errors.append(f"{rel_path}: name muss {expected_name} sein")
    if 'sandbox_mode = "read-only"' not in text:
        errors.append(f"{rel_path}: sandbox_mode muss read-only sein")
    if "Do not edit files." not in text:
        errors.append(f"{rel_path}: developer_instructions muessen Datei-Edits untersagen")
    if "developer_instructions" not in text:
        errors.append(f"{rel_path}: developer_instructions fehlt")
    return errors


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def main() -> int:
    errors: list[str] = []
    errors.extend(validate_contract())
    errors.extend(validate_codex_config())
    errors.extend(validate_agent_registry())

    if not AGENT_DIR.is_dir():
        errors.append(f"Agentprofilordner fehlt: {AGENT_DIR.relative_to(REPO_ROOT)}")

    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("STATUS: PASSED")
    print("OK: Codex Parallel Review Workflow hat Default-Policy, read-only Agentprofile, Guardrails, Vertrag und Pflichtvalidierungen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
