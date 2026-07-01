from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "nac-onprem-agent-runtime.contract.json"
DOC_DE = REPO_ROOT / "docs" / "de" / "architecture" / "nac-onprem-agent-runtime.md"
DOC_EN = REPO_ROOT / "docs" / "en" / "architecture" / "nac-onprem-agent-runtime.md"
RUNBOOK_DE = REPO_ROOT / "docs" / "de" / "operations" / "ponytail-skill-only-smoke.md"
RUNBOOK_EN = REPO_ROOT / "docs" / "en" / "operations" / "ponytail-skill-only-smoke.md"
RUNTIME_SMOKE_RUNBOOK_DE = REPO_ROOT / "docs" / "de" / "operations" / "nac-runtime-smoke.md"
RUNTIME_SMOKE_RUNBOOK_EN = REPO_ROOT / "docs" / "en" / "operations" / "nac-runtime-smoke.md"
OPERATIONS_DE = REPO_ROOT / "docs" / "de" / "operations" / "README.md"
OPERATIONS_EN = REPO_ROOT / "docs" / "en" / "operations" / "README.md"
EVIDENCE_TEMPLATE = REPO_ROOT / "workflows" / "evidence-templates" / "ponytail-skill-only-smoke.md"
RUNTIME_SMOKE_EVIDENCE_TEMPLATE = REPO_ROOT / "workflows" / "evidence-templates" / "nac-runtime-smoke.md"
QUALITY_DE = REPO_ROOT / "docs" / "de" / "quality-gate.md"
QUALITY_EN = REPO_ROOT / "docs" / "en" / "quality-gate.md"

REQUIRED_TARGET_PATHS = {
    "manifest_path": "blueprints/nac-onprem/agents.yaml",
    "workspace_template_path": "blueprints/nac-onprem/workspace-template",
    "skill_path": "skills/nac-agent/SKILL.md",
    "mcp_readme_path": "mcp/nac/README.md",
    "evidence_path": "evidence/2026-06-28-nac-onprem-agent-solution.md",
}
REQUIRED_TEMPLATE_FILES = {"AGENTS.md", "IDENTITY.md", "SOUL.md", "USER.md", "MEMORY.md"}
REQUIRED_CONNECTOR_IDS = {"xnp_snp", "cyberjack_card_workstation", "register"}
REQUIRED_CONNECTOR_PATHS = {
    "connectors/xnp/README.md",
    "connectors/cyberjack/README.md",
    "connectors/register/README.md",
}
REQUIRED_AGENT_TOOLING_IDS = {"ponytail"}
REQUIRED_PONYTAIL_BLOCKED_USE = {
    "codex_lifecycle_hook_activation",
    "openclaw_runtime_activation_without_owner_gate",
    "mandate_data_processing",
    "shorten_security_privacy_owner_gates_tests_or_validators",
    "github_or_oci_write_from_target",
}
REQUIRED_PONYTAIL_SKILL_ONLY_SMOKE = {
    "status": "passed_no_install_no_activation",
    "runbook_de": "docs/de/operations/ponytail-skill-only-smoke.md",
    "runbook_en": "docs/en/operations/ponytail-skill-only-smoke.md",
    "evidence_template": "workflows/evidence-templates/ponytail-skill-only-smoke.md",
    "target_evidence_directory": "/home/ubuntu/nac-target-control/evidence",
    "target_evidence_file": "evidence/ponytail-skill-only-smoke-2026-06-29.md",
    "execution_date": "2026-06-29",
}
REQUIRED_PONYTAIL_SKILL_ONLY_TRUE_FLAGS = {
    "owner_apply_required_before_execution",
    "execution_performed",
}
REQUIRED_PONYTAIL_SKILL_ONLY_FALSE_FLAGS = {
    "installation_performed",
    "hooks_enabled",
    "runtime_activation_performed",
    "github_write_performed",
    "oci_write_performed",
    "repo_change_required",
    "owner_input_needed",
}
REQUIRED_RUNTIME_SMOKE = {
    "status": "ready_owner_gated_not_executed",
    "runbook_de": "docs/de/operations/nac-runtime-smoke.md",
    "runbook_en": "docs/en/operations/nac-runtime-smoke.md",
    "evidence_template": "workflows/evidence-templates/nac-runtime-smoke.md",
    "target_evidence_directory": "/home/ubuntu/nac-target-control/evidence",
    "target_evidence_file_pattern": "evidence/nac-runtime-smoke-YYYY-MM-DD.md",
    "public_origin_env": "NAC_PUBLIC_ORIGIN",
    "public_origin_config_path": "config/public-origin",
}
REQUIRED_RUNTIME_SMOKE_TRUE_FLAGS = {
    "owner_apply_required_before_execution",
    "public_origin_required",
    "production_public_origin_requires_fixed_domain",
    "production_public_origin_dns_backed_required",
    "temporary_tunnel_origin_allowed_for_demo_only",
}
REQUIRED_RUNTIME_SMOKE_FALSE_FLAGS = {
    "execution_performed",
    "installation_performed",
    "onboard_performed",
    "rebuild_performed",
    "lifecycle_hooks_enabled",
    "openclaw_runtime_mutation_performed",
    "dashboard_token_captured",
    "github_write_performed",
    "oci_write_performed",
    "secrets_required",
    "matter_data_required",
    "temporary_tunnel_origin_provider_specific_production_default_allowed",
    "temporary_tunnel_origin_production_allowed",
    "hardcoded_public_origin_default_allowed",
    "quick_tunnel_origin_default_allowed",
}
REQUIRED_AGENT_ROLES_OR_NAMES = {
    "main",
    "notary-flow",
    "evidence",
    "connector-ops",
}
REQUIRED_OWNER_GATES = {
    "architecture_decision",
    "secret_or_credential",
    "github_write_from_target",
    "productive_connector_apply",
    "oci_apply",
    "release",
    "destructive_action",
}
REQUIRED_TRUE_GUARDRAILS = {
    "target_control_may_use_nac_read_only_mirror",
    "project_manager_keeps_delivery_ownership",
    "protected_pr_required_for_repo_change",
}
REQUIRED_FALSE_GUARDRAILS = {
    "notoclaw_is_project_manager",
    "target_operator_github_write_allowed_by_default",
    "target_operator_pr_creation_allowed_by_default",
    "external_agent_hooks_enabled_by_default",
    "optional_agent_tooling_may_override_nac_governance",
    "secrets_in_target_control_allowed",
    "matter_data_in_target_control_allowed",
    "productive_connector_apply_allowed_without_owner_gate",
    "productive_release_allowed_without_owner_gate",
    "target_control_may_read_codex_runtime_secrets",
}
PROHIBITED_MARKERS = {
    "BEGIN PRIVATE KEY",
    "BEGIN CERTIFICATE",
    "client_secret",
    "ghp_",
    "gho_",
    "oci_session_token",
    "password=",
    "PIN:",
}


def validate_contract(path: Path = CONTRACT_PATH) -> list[str]:
    errors: list[str] = []
    if not path.is_file():
        return [f"missing contract: {path.relative_to(REPO_ROOT)}"]

    text = path.read_text(encoding="utf-8")
    _reject_prohibited_text(path, text, errors)
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"{path.relative_to(REPO_ROOT)} is invalid JSON: {exc}"]
    if not isinstance(payload, dict):
        return [f"{path.relative_to(REPO_ROOT)} must be a JSON object"]

    if payload.get("schema_version") != "nac.workflow-contract/v0.1":
        errors.append("schema_version must be nac.workflow-contract/v0.1")
    if payload.get("contract_id") != "workflow.nac_onprem_agent_runtime":
        errors.append("contract_id must be workflow.nac_onprem_agent_runtime")
    if payload.get("status") != "target_control_ready_no_productive_connector_apply":
        errors.append("status must be target_control_ready_no_productive_connector_apply")

    errors.extend(_validate_operating_model(payload))
    errors.extend(_validate_source_of_truth(payload))
    errors.extend(_validate_target_control(payload))
    errors.extend(_validate_roles_and_connectors(payload))
    errors.extend(_validate_optional_agent_tooling(payload))
    errors.extend(_validate_guardrails(payload))
    errors.extend(_validate_handoff(payload))
    errors.extend(_validate_docs(payload))
    return errors


def _validate_operating_model(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    model = payload.get("operating_model")
    if not isinstance(model, dict):
        return ["operating_model must be an object"]
    for key in ("project_manager", "dev_agent", "target_operator"):
        entry = model.get(key)
        if not isinstance(entry, dict):
            errors.append(f"operating_model.{key} must be an object")
            continue
        if not isinstance(entry.get("location"), str) or not entry["location"]:
            errors.append(f"operating_model.{key}.location must be set")
        if not isinstance(entry.get("responsibility"), str) or not entry["responsibility"]:
            errors.append(f"operating_model.{key}.responsibility must be set")
    return errors


def _validate_source_of_truth(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    source = payload.get("source_of_truth")
    if not isinstance(source, dict):
        return ["source_of_truth must be an object"]
    git_items = set(_string_list(source.get("git")))
    for required in ("nac_repo_code", "nac_repo_contracts", "nac_repo_governance"):
        if required not in git_items:
            errors.append(f"source_of_truth.git missing {required}")
    target_items = set(_string_list(source.get("target_control")))
    for required in ("target_manifests", "target_local_smokes", "target_non_sensitive_evidence"):
        if required not in target_items:
            errors.append(f"source_of_truth.target_control missing {required}")
    excluded = set(_string_list(source.get("not_source_of_truth")))
    for required in ("/home/ubuntu/.codex", "/home/ubuntu/.nemoclaw", "/sandbox/.openclaw/workspace-*"):
        if required not in excluded:
            errors.append(f"source_of_truth.not_source_of_truth missing {required}")
    return errors


def _validate_target_control(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    target = payload.get("target_control")
    if not isinstance(target, dict):
        return ["target_control must be an object"]
    if target.get("host_label") != "notoclaw01-host":
        errors.append("target_control.host_label must be notoclaw01-host")
    if target.get("control_path") != "/home/ubuntu/nac-target-control":
        errors.append("target_control.control_path must be /home/ubuntu/nac-target-control")
    if target.get("runtime_family") != "NemoClaw/OpenClaw":
        errors.append("target_control.runtime_family must be NemoClaw/OpenClaw")
    for key, expected in REQUIRED_TARGET_PATHS.items():
        if target.get(key) != expected:
            errors.append(f"target_control.{key} must be {expected}")
    template_files = set(_string_list(target.get("required_workspace_template_files")))
    for missing in sorted(REQUIRED_TEMPLATE_FILES - template_files):
        errors.append(f"target_control.required_workspace_template_files missing {missing}")
    connector_paths = set(_string_list(target.get("connector_paths")))
    for missing in sorted(REQUIRED_CONNECTOR_PATHS - connector_paths):
        errors.append(f"target_control.connector_paths missing {missing}")
    smoke_commands = _string_list(target.get("smoke_commands"))
    for command in ("bin/nac-target-smoke", "bin/nac-runtime-smoke"):
        if command not in smoke_commands:
            errors.append(f"target_control.smoke_commands missing {command}")
    runtime_smoke = target.get("runtime_smoke")
    if not isinstance(runtime_smoke, dict):
        errors.append("target_control.runtime_smoke must be an object")
        return errors
    for key, expected in REQUIRED_RUNTIME_SMOKE.items():
        if runtime_smoke.get(key) != expected:
            errors.append(f"target_control.runtime_smoke.{key} must be {expected}")
        if key.startswith("runbook_") or key == "evidence_template":
            value = runtime_smoke.get(key)
            if isinstance(value, str) and not (REPO_ROOT / value).is_file():
                errors.append(f"target_control.runtime_smoke.{key} points to missing file: {value}")
    for flag in sorted(REQUIRED_RUNTIME_SMOKE_TRUE_FLAGS):
        if runtime_smoke.get(flag) is not True:
            errors.append(f"target_control.runtime_smoke.{flag} must be true")
    for flag in sorted(REQUIRED_RUNTIME_SMOKE_FALSE_FLAGS):
        if runtime_smoke.get(flag) is not False:
            errors.append(f"target_control.runtime_smoke.{flag} must be false")
    return errors


def _validate_roles_and_connectors(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    roles = set(_string_list(payload.get("required_agent_roles_or_names")))
    for missing in sorted(REQUIRED_AGENT_ROLES_OR_NAMES - roles):
        errors.append(f"required_agent_roles_or_names missing {missing}")

    connector_boundaries = payload.get("connector_boundaries")
    if not isinstance(connector_boundaries, list) or not connector_boundaries:
        return errors + ["connector_boundaries must be a non-empty list"]
    by_id = {
        item.get("id"): item
        for item in connector_boundaries
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for connector_id in sorted(REQUIRED_CONNECTOR_IDS):
        entry = by_id.get(connector_id)
        if not isinstance(entry, dict):
            errors.append(f"connector_boundaries missing {connector_id}")
            continue
        if entry.get("status") != "prepared_stub_only":
            errors.append(f"connector_boundaries.{connector_id}.status must be prepared_stub_only")
        if not isinstance(entry.get("path"), str) or entry["path"] not in REQUIRED_CONNECTOR_PATHS:
            errors.append(f"connector_boundaries.{connector_id}.path must be one of the required connector paths")
        next_gate = entry.get("next_gate")
        if not isinstance(next_gate, str) or "before_live_apply" not in next_gate:
            errors.append(f"connector_boundaries.{connector_id}.next_gate must require before_live_apply")
    return errors


def _validate_optional_agent_tooling(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    candidates = payload.get("optional_agent_tooling_candidates")
    if not isinstance(candidates, list) or not candidates:
        return ["optional_agent_tooling_candidates must be a non-empty list"]
    by_id = {
        item.get("id"): item
        for item in candidates
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for missing in sorted(REQUIRED_AGENT_TOOLING_IDS - set(by_id)):
        errors.append(f"optional_agent_tooling_candidates missing {missing}")

    ponytail = by_id.get("ponytail")
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
            errors.append(f"optional_agent_tooling_candidates.ponytail.{key} must be {expected}")

    allowed_use = set(_string_list(ponytail.get("allowed_use")))
    for use in ("over_engineering_review", "simplicity_check"):
        if use not in allowed_use:
            errors.append(f"optional_agent_tooling_candidates.ponytail.allowed_use missing {use}")

    blocked_use = set(_string_list(ponytail.get("blocked_use")))
    for use in sorted(REQUIRED_PONYTAIL_BLOCKED_USE - blocked_use):
        errors.append(f"optional_agent_tooling_candidates.ponytail.blocked_use missing {use}")

    owner_gates = set(_string_list(ponytail.get("owner_gate_before")))
    for gate in ("plugin_installation", "lifecycle_hook_activation", "runtime_activation"):
        if gate not in owner_gates:
            errors.append(f"optional_agent_tooling_candidates.ponytail.owner_gate_before missing {gate}")

    skill_only = ponytail.get("skill_only_smoke")
    if not isinstance(skill_only, dict):
        errors.append("optional_agent_tooling_candidates.ponytail.skill_only_smoke must be an object")
        return errors
    for key, expected in REQUIRED_PONYTAIL_SKILL_ONLY_SMOKE.items():
        if skill_only.get(key) != expected:
            errors.append(
                f"optional_agent_tooling_candidates.ponytail.skill_only_smoke.{key} must be {expected}"
            )
        if key.startswith("runbook_") or key == "evidence_template":
            value = skill_only.get(key)
            if isinstance(value, str) and not (REPO_ROOT / value).is_file():
                errors.append(
                    f"optional_agent_tooling_candidates.ponytail.skill_only_smoke.{key} points to missing file: {value}"
                )
    for flag in sorted(REQUIRED_PONYTAIL_SKILL_ONLY_TRUE_FLAGS):
        if skill_only.get(flag) is not True:
            errors.append(f"optional_agent_tooling_candidates.ponytail.skill_only_smoke.{flag} must be true")
    for flag in sorted(REQUIRED_PONYTAIL_SKILL_ONLY_FALSE_FLAGS):
        if skill_only.get(flag) is not False:
            errors.append(f"optional_agent_tooling_candidates.ponytail.skill_only_smoke.{flag} must be false")
    return errors


def _validate_guardrails(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    guardrails = payload.get("guardrails")
    if not isinstance(guardrails, dict):
        return ["guardrails must be an object"]
    for key in sorted(REQUIRED_TRUE_GUARDRAILS):
        if guardrails.get(key) is not True:
            errors.append(f"guardrails.{key} must be true")
    for key in sorted(REQUIRED_FALSE_GUARDRAILS):
        if guardrails.get(key) is not False:
            errors.append(f"guardrails.{key} must be false")
    owner_gates = set(_string_list(payload.get("owner_gates")))
    for missing in sorted(REQUIRED_OWNER_GATES - owner_gates):
        errors.append(f"owner_gates missing {missing}")
    return errors


def _validate_handoff(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    handoff = payload.get("handoff")
    if not isinstance(handoff, dict):
        return ["handoff must be an object"]
    if handoff.get("required_when_repo_change_needed") is not True:
        errors.append("handoff.required_when_repo_change_needed must be true")
    fields = set(_string_list(handoff.get("format_fields")))
    for field in ("Handoff", "Scope", "Evidence", "Required NaC repo change", "Owner input needed"):
        if field not in fields:
            errors.append(f"handoff.format_fields missing {field}")
    commands = set(_string_list(payload.get("validation_commands")))
    for command in (
        "python scripts/validate_nac_onprem_agent_runtime.py",
        "python scripts/validate_language_parity.py",
        "python scripts/validate_doc_links.py",
    ):
        if command not in commands:
            errors.append(f"validation_commands missing {command}")
    return errors


def _validate_docs(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    docs = payload.get("documentation")
    if not isinstance(docs, dict):
        errors.append("documentation must be an object")
    else:
        expected = {
            "de": "docs/de/architecture/nac-onprem-agent-runtime.md",
            "en": "docs/en/architecture/nac-onprem-agent-runtime.md",
            "operating_model_de": "docs/de/architecture/nemoclaw-operating-model.md",
            "operating_model_en": "docs/en/architecture/nemoclaw-operating-model.md",
        }
        for key, value in expected.items():
            if docs.get(key) != value:
                errors.append(f"documentation.{key} must be {value}")

    for path, required_text in (
        (DOC_DE, "NaC-On-Prem-Agent-Runtime"),
        (DOC_DE, "Ponytail Skill-Only Smoke"),
        (DOC_DE, "NaC Runtime-Smoke"),
        (DOC_DE, "feste, DNS-gestützte Domain"),
        (DOC_EN, "NaC On-Prem Agent Runtime"),
        (DOC_EN, "fixed, DNS-backed domain"),
        (DOC_EN, "Ponytail skill-only smoke"),
        (DOC_EN, "NaC runtime smoke"),
        (RUNBOOK_DE, "Status: ausgeführt, bestanden"),
        (RUNBOOK_DE, "ponytail-skill-only-smoke-2026-06-29.md"),
        (RUNBOOK_EN, "Status: executed, passed"),
        (RUNBOOK_EN, "ponytail-skill-only-smoke-2026-06-29.md"),
        (RUNTIME_SMOKE_RUNBOOK_DE, "Status: vorbereitet, Owner-gated nicht ausgeführt"),
        (RUNTIME_SMOKE_RUNBOOK_DE, "Owner Apply Approval for NaC runtime smoke"),
        (RUNTIME_SMOKE_RUNBOOK_DE, "Public-Origin ist in Produktions-Smokes Pflichtkonfiguration"),
        (RUNTIME_SMOKE_RUNBOOK_DE, "Produktions-Smokes müssen eine feste, DNS-gestützte Domain verwenden"),
        (RUNTIME_SMOKE_RUNBOOK_DE, "provider-spezifische"),
        (RUNTIME_SMOKE_RUNBOOK_EN, "Status: prepared, owner-gated not executed"),
        (RUNTIME_SMOKE_RUNBOOK_EN, "Owner Apply Approval for NaC runtime smoke"),
        (RUNTIME_SMOKE_RUNBOOK_EN, "Public origin is required configuration for production smokes"),
        (RUNTIME_SMOKE_RUNBOOK_EN, "Production smokes must use a fixed, DNS-backed domain"),
        (RUNTIME_SMOKE_RUNBOOK_EN, "provider-specific tunnel domain"),
        (OPERATIONS_DE, "ponytail-skill-only-smoke.md"),
        (OPERATIONS_DE, "nac-runtime-smoke.md"),
        (OPERATIONS_EN, "ponytail-skill-only-smoke.md"),
        (OPERATIONS_EN, "nac-runtime-smoke.md"),
        (EVIDENCE_TEMPLATE, "Evidence-Status: nur Vorlage"),
        (EVIDENCE_TEMPLATE, "candidate_not_installed"),
        (RUNTIME_SMOKE_EVIDENCE_TEMPLATE, "Evidence-Status: nur Vorlage"),
        (RUNTIME_SMOKE_EVIDENCE_TEMPLATE, "ready_owner_gated_not_executed"),
        (RUNTIME_SMOKE_EVIDENCE_TEMPLATE, "Public-Origin-Konfiguration"),
        (RUNTIME_SMOKE_EVIDENCE_TEMPLATE, "Public-Origin-Klasse"),
        (QUALITY_DE, "nac_onprem_agent_runtime"),
        (QUALITY_EN, "nac_onprem_agent_runtime"),
    ):
        if not path.is_file():
            errors.append(f"missing documentation file: {path.relative_to(REPO_ROOT)}")
            continue
        text = path.read_text(encoding="utf-8")
        _reject_prohibited_text(path, text, errors)
        if required_text not in text:
            errors.append(f"{path.relative_to(REPO_ROOT)} missing marker {required_text}")
    return errors


def _reject_prohibited_text(path: Path, text: str, errors: list[str]) -> None:
    lowered = text.lower()
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in lowered:
            errors.append(f"{path.relative_to(REPO_ROOT)} contains prohibited marker: {marker}")


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def main() -> int:
    errors = validate_contract()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: NaC on-prem agent runtime contract keeps notoclaw target-control, GitOps ownership, connector stubs and owner gates aligned.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
