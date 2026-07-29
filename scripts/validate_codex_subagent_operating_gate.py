from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any


if __package__:
    from scripts.scoped_repo_glob import path_or_glob_matches as _path_or_glob_matches
else:
    from scoped_repo_glob import path_or_glob_matches as _path_or_glob_matches


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "agent-context" / "subagent-registry.json"
CONTRACT_PATH = REPO_ROOT / "workflows" / "contracts" / "codex-parallel-review.contract.json"
VERIFICATION_PATH = (
    REPO_ROOT
    / "workflows"
    / "verification-contracts"
    / "codex-subagent-operating-gate.verification.json"
)
AGENT_CONTEXT_INDEX = REPO_ROOT / "agent-context" / "index.json"
CODEX_CONFIG = REPO_ROOT / ".codex" / "config.toml"
AGENT_DIR = REPO_ROOT / ".codex" / "agents"
QUALITY_GATE = REPO_ROOT / "scripts" / "quality_gate.py"
NAC_CLI = REPO_ROOT / "src" / "nac_cli" / "cli.py"
TEST_FILE = REPO_ROOT / "tests" / "test_codex_subagent_operating_gate.py"

EXPECTED_AGENT_NAMES = {
    "nac_scope_mapper",
    "nac_kg_reviewer",
    "nac_bpmn_reviewer",
    "nac_policy_reviewer",
    "nac_docs_parity_reviewer",
    "nac_validation_reviewer",
}
EXPECTED_LIMITS = {
    "max_threads": 6,
    "max_depth": 1,
    "job_max_runtime_seconds": 1800,
}
EXPECTED_THRESHOLDS = {
    "use_subagents_when_independent_questions": 2,
    "use_worktrees_when_parallel_write_scopes": 2,
    "do_not_split_if_coordination_cost_exceeds_review_value": True,
}
EXPECTED_PROHIBITED_DELEGATIONS = {
    "secrets",
    "certificate_private_material",
    "real_mandate_data",
    "productive_m365_writes",
    "entra_app_credentials",
    "release_apply",
    "destructive_git_cleanup",
}
PROHIBITED_MARKERS = {
    "client" + "_secret",
    "BEGIN " + "PRIVATE KEY",
    "BEGIN " + "CERTIFICATE",
    "gh" + "p_",
    "gh" + "o_",
    "real_mandate_data_sample",
    "password=",
}


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: Codex subagent operating gate enforces registry, read-only profiles, runtime limits and batch boundaries.")
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    registry = _read_json(REGISTRY_PATH, errors)
    contract = _read_json(CONTRACT_PATH, errors)
    verification = _read_json(VERIFICATION_PATH, errors)
    index = _read_json(AGENT_CONTEXT_INDEX, errors)
    config = _read_toml(CODEX_CONFIG, errors)

    if registry is not None:
        errors.extend(_validate_registry(registry))
    if contract is not None and registry is not None:
        errors.extend(_validate_contract(contract, registry))
    if verification is not None:
        errors.extend(_validate_verification_contract(verification))
    if index is not None:
        errors.extend(_validate_agent_context_index(index))
    if config is not None:
        errors.extend(_validate_config(config))
    errors.extend(_validate_docs())
    errors.extend(_validate_quality_gate_and_cli())
    return errors


def _validate_registry(registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if registry.get("schema_version") != "nac.codex-subagent-registry/v0.1":
        errors.append("subagent-registry.json: schema_version muss nac.codex-subagent-registry/v0.1 sein")
    if registry.get("registry_id") != "codex_subagent_registry":
        errors.append("subagent-registry.json: registry_id muss codex_subagent_registry sein")
    if registry.get("source_contract") != "workflows/contracts/codex-parallel-review.contract.json":
        errors.append("subagent-registry.json: source_contract verweist nicht auf codex-parallel-review.contract.json")
    if registry.get("runtime_config") != ".codex/config.toml":
        errors.append("subagent-registry.json: runtime_config muss .codex/config.toml sein")
    if registry.get("default_sandbox_mode") != "read-only":
        errors.append("subagent-registry.json: default_sandbox_mode muss read-only sein")

    errors.extend(_validate_limits("subagent-registry.json:limits", registry.get("limits")))
    errors.extend(_validate_thresholds("subagent-registry.json:batch_thresholds", registry.get("batch_thresholds")))

    rogue = registry.get("rogue_agent_policy")
    if not isinstance(rogue, dict):
        errors.append("subagent-registry.json: rogue_agent_policy muss Objekt sein")
    else:
        expected = {
            "unknown_profile_behavior": "fail_closed",
            "local_extra_toml_allowed": False,
            "registry_must_match_agent_dir_exactly": True,
            "lead_agent_keeps_ownership": True,
        }
        for key, value in expected.items():
            if rogue.get(key) != value:
                errors.append(f"subagent-registry.json: rogue_agent_policy.{key} muss {value!r} sein")

    profiles = registry.get("allowed_profiles")
    if not isinstance(profiles, list):
        errors.append("subagent-registry.json: allowed_profiles muss Liste sein")
        return errors

    registry_names: set[str] = set()
    registry_paths: set[str] = set()
    for index, profile in enumerate(profiles, start=1):
        if not isinstance(profile, dict):
            errors.append(f"subagent-registry.json: allowed_profiles[{index}] muss Objekt sein")
            continue
        name = profile.get("name")
        path_value = profile.get("path")
        if not isinstance(name, str) or not name:
            errors.append(f"subagent-registry.json: allowed_profiles[{index}].name fehlt")
            continue
        if name in registry_names:
            errors.append(f"subagent-registry.json: Profil doppelt: {name}")
        registry_names.add(name)
        if profile.get("sandbox_mode") != "read-only":
            errors.append(f"subagent-registry.json: {name}.sandbox_mode muss read-only sein")
        if profile.get("may_edit_files") is not False:
            errors.append(f"subagent-registry.json: {name}.may_edit_files muss false sein")
        if not isinstance(path_value, str) or not path_value:
            errors.append(f"subagent-registry.json: {name}.path fehlt")
            continue
        registry_paths.add(path_value)
        errors.extend(_validate_agent_profile_toml(path_value, name))

    for missing in sorted(EXPECTED_AGENT_NAMES - registry_names):
        errors.append(f"subagent-registry.json: Pflichtprofil fehlt: {missing}")
    for extra in sorted(registry_names - EXPECTED_AGENT_NAMES):
        errors.append(f"subagent-registry.json: nicht erlaubtes Profil: {extra}")

    actual_paths = {item.relative_to(REPO_ROOT).as_posix() for item in AGENT_DIR.glob("*.toml")}
    for missing in sorted(registry_paths - actual_paths):
        errors.append(f"Agentprofil-Datei fehlt: {missing}")
    for extra in sorted(actual_paths - registry_paths):
        errors.append(f"Nicht registriertes Agentprofil gefunden: {extra}")

    prohibited = set(_string_list(registry.get("prohibited_delegations")))
    for missing in sorted(EXPECTED_PROHIBITED_DELEGATIONS - prohibited):
        errors.append(f"subagent-registry.json: prohibited_delegations fehlt: {missing}")
    return errors


def _validate_contract(contract: dict[str, Any], registry: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    gate = contract.get("subagent_operating_gate")
    if not isinstance(gate, dict):
        return ["codex-parallel-review.contract.json: subagent_operating_gate fehlt"]
    errors.extend(_validate_limits("codex-parallel-review.contract.json:subagent_operating_gate", gate))
    errors.extend(_validate_thresholds("codex-parallel-review.contract.json:batch_thresholds", gate.get("batch_thresholds")))
    if gate.get("exact_agent_registry_required") is not True:
        errors.append("codex-parallel-review.contract.json: exact_agent_registry_required muss true sein")
    if gate.get("rogue_agent_profiles_allowed") is not False:
        errors.append("codex-parallel-review.contract.json: rogue_agent_profiles_allowed muss false sein")
    if gate.get("lead_agent_integrates_results") is not True:
        errors.append("codex-parallel-review.contract.json: lead_agent_integrates_results muss true sein")

    contract_names = {
        item.get("name")
        for item in contract.get("agent_profiles", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    registry_names = {
        item.get("name")
        for item in registry.get("allowed_profiles", [])
        if isinstance(item, dict) and isinstance(item.get("name"), str)
    }
    if contract_names != registry_names:
        errors.append("codex-parallel-review.contract.json: agent_profiles muss exakt zur Subagent-Registry passen")

    verification_contracts = set(_string_list(contract.get("verification_contracts")))
    if "workflows/verification-contracts/codex-subagent-operating-gate.verification.json" not in verification_contracts:
        errors.append("codex-parallel-review.contract.json: Subagent-Verification-Contract fehlt")
    commands = set(_string_list(contract.get("validation_commands")))
    if "python scripts/validate_codex_subagent_operating_gate.py" not in commands:
        errors.append("codex-parallel-review.contract.json: validation_commands fehlt validate_codex_subagent_operating_gate.py")
    return errors


def _validate_verification_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "nac.verification-contract/v0.1":
        errors.append("codex-subagent-operating-gate.verification.json: schema_version muss nac.verification-contract/v0.1 sein")
    if payload.get("contract_id") != "verification.codex_subagent_operating_gate":
        errors.append("codex-subagent-operating-gate.verification.json: contract_id ist falsch")
    applies_when = payload.get("applies_when")
    paths = _string_list(applies_when.get("paths")) if isinstance(applies_when, dict) else []
    for required in (
        "agent-context/subagent-registry.json",
        ".codex/agents/**",
        "scripts/validate_codex_subagent_operating_gate.py",
        "tests/test_codex_subagent_operating_gate.py",
    ):
        if required not in paths:
            errors.append(f"codex-subagent-operating-gate.verification.json: applies_when.paths fehlt {required}")
    for pattern in paths:
        if not _path_or_glob_matches(pattern):
            errors.append(f"codex-subagent-operating-gate.verification.json: applies_when.paths matcht nichts: {pattern}")
    thresholds = payload.get("thresholds")
    if not isinstance(thresholds, dict):
        errors.append("codex-subagent-operating-gate.verification.json: thresholds muss Objekt sein")
    else:
        expected_agent_limits = {
            "max_agent_threads": 6,
            "max_agent_depth": 1,
            "max_agent_runtime_seconds": 1800,
        }
        for key, expected in expected_agent_limits.items():
            if thresholds.get(key) != expected:
                errors.append(f"codex-subagent-operating-gate.verification.json: thresholds.{key} muss {expected} sein")
        if thresholds.get("required_profile_count") != 6:
            errors.append("codex-subagent-operating-gate.verification.json: thresholds.required_profile_count muss 6 sein")
        if thresholds.get("minimum_independent_questions_for_subagents") != 2:
            errors.append("codex-subagent-operating-gate.verification.json: thresholds.minimum_independent_questions_for_subagents muss 2 sein")
    for field in ("checks", "invariants", "required_evidence"):
        if not _string_list(payload.get(field)):
            errors.append(f"codex-subagent-operating-gate.verification.json: {field} muss nicht leer sein")
    pass_condition = payload.get("pass_condition")
    if not isinstance(pass_condition, dict) or pass_condition.get("all_checks_pass") is not True:
        errors.append("codex-subagent-operating-gate.verification.json: pass_condition.all_checks_pass muss true sein")
    failure = payload.get("failure_behavior")
    if not isinstance(failure, dict) or failure.get("unknown_agent_profile") != "fail_closed":
        errors.append("codex-subagent-operating-gate.verification.json: unknown_agent_profile muss fail_closed sein")
    return errors


def _validate_agent_context_index(payload: dict[str, Any]) -> list[str]:
    categories = {
        category.get("id"): category.get("paths")
        for layer in payload.get("layers", [])
        if isinstance(layer, dict)
        for category in layer.get("categories", [])
        if isinstance(category, dict)
    }
    paths = _string_list(categories.get("subagent_operating_gate"))
    required = {
        "agent-context/subagent-registry.json",
        "docs/de/operations/codex-subagent-operating-gate.md",
        "docs/en/operations/codex-subagent-operating-gate.md",
        "workflows/verification-contracts/codex-subagent-operating-gate.verification.json",
    }
    missing = required - set(paths)
    return [f"agent-context/index.json: subagent_operating_gate fehlt Pfad {path}" for path in sorted(missing)]


def _validate_config(config: dict[str, Any]) -> list[str]:
    agents = config.get("agents")
    if not isinstance(agents, dict):
        return [".codex/config.toml: [agents] fehlt"]
    return _validate_limits(".codex/config.toml:[agents]", agents)


def _validate_docs() -> list[str]:
    errors: list[str] = []
    for rel_path in (
        "docs/en/operations/codex-subagent-operating-gate.md",
        "docs/de/operations/codex-subagent-operating-gate.md",
        "docs/en/codex-parallel-review-workflow.md",
        "docs/de/codex-parallel-review-workflow.md",
        "docs/en/operations/README.md",
        "docs/de/operations/README.md",
    ):
        path = REPO_ROOT / rel_path
        if not path.is_file():
            errors.append(f"Pflichtdokument fehlt: {rel_path}")
            continue
        text = path.read_text(encoding="utf-8")
        for marker in PROHIBITED_MARKERS:
            if marker.lower() in text.lower():
                errors.append(f"{rel_path} enthaelt unzulaessigen Marker: {marker}")
        for required in ("subagent-registry.json", "codex-subagent-operating-gate", "read-only"):
            if required not in text:
                errors.append(f"{rel_path} fehlt Marker: {required}")
    return errors


def _validate_quality_gate_and_cli() -> list[str]:
    errors: list[str] = []
    for path, label in (
        (QUALITY_GATE, "scripts/quality_gate.py"),
        (NAC_CLI, "src/nac_cli/cli.py"),
        (TEST_FILE, "tests/test_codex_subagent_operating_gate.py"),
    ):
        if not path.is_file():
            errors.append(f"Pflichtdatei fehlt: {label}")
            continue
        text = path.read_text(encoding="utf-8")
        if "validate_codex_subagent_operating_gate.py" not in text:
            errors.append(f"{label} bindet validate_codex_subagent_operating_gate.py nicht ein")
    return errors


def _validate_agent_profile_toml(rel_path: str, expected_name: str) -> list[str]:
    errors: list[str] = []
    path = REPO_ROOT / rel_path
    if not path.is_file():
        return [f"Agentprofil fehlt: {rel_path}"]
    text = path.read_text(encoding="utf-8")
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in text.lower():
            errors.append(f"{rel_path} enthaelt unzulaessigen Marker: {marker}")
    payload = tomllib.loads(text)
    if payload.get("name") != expected_name:
        errors.append(f"{rel_path}: name muss {expected_name} sein")
    if payload.get("sandbox_mode") != "read-only":
        errors.append(f"{rel_path}: sandbox_mode muss read-only sein")
    instructions = payload.get("developer_instructions")
    if not isinstance(instructions, str):
        errors.append(f"{rel_path}: developer_instructions fehlt")
        return errors
    for required in (
        "Do not edit files.",
        "persistent owner working agreement",
        "Codex command rules",
    ):
        if required not in instructions:
            errors.append(f"{rel_path}: developer_instructions fehlt Marker: {required}")
    return errors


def _validate_limits(label: str, value: object) -> list[str]:
    if not isinstance(value, dict):
        return [f"{label} muss Objekt sein"]
    errors: list[str] = []
    for key, expected in EXPECTED_LIMITS.items():
        if value.get(key) != expected:
            errors.append(f"{label}.{key} muss {expected} sein")
    return errors


def _validate_thresholds(label: str, value: object) -> list[str]:
    if not isinstance(value, dict):
        return [f"{label} muss Objekt sein"]
    errors: list[str] = []
    for key, expected in EXPECTED_THRESHOLDS.items():
        if value.get(key) != expected:
            errors.append(f"{label}.{key} muss {expected!r} sein")
    return errors


def _read_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"JSON-Datei fehlt: {path.relative_to(REPO_ROOT)}")
        return None
    text = path.read_text(encoding="utf-8")
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in text.lower():
            errors.append(f"{path.relative_to(REPO_ROOT)} enthaelt unzulaessigen Marker: {marker}")
    payload = json.loads(text)
    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)} muss JSON-Objekt sein")
        return None
    return payload


def _read_toml(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"TOML-Datei fehlt: {path.relative_to(REPO_ROOT)}")
        return None
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


if __name__ == "__main__":
    raise SystemExit(main())
