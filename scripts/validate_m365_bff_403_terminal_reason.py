"""Validate the inactive, request-local Issue #756 terminal-reason contract."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT / "workflows/verification-contracts/m365-bff-403-terminal-reason.verification.json"
)

_REASONS = [
    "GRAPH_READ_UNAVAILABLE",
    "CASE_BINDING_INVALID",
    "ACTOR_ASSIGNMENT_MISSING",
    "DEPUTY_GRANT_INVALID",
    "GRANT_AUDIT_INVALID",
    "DECISION_PROJECTION_INVALID",
    "DENIAL_UNCLASSIFIED",
]
_INFERENCE_BEARING = [
    "ACTOR_ASSIGNMENT_MISSING",
    "DEPUTY_GRANT_INVALID",
    "GRANT_AUDIT_INVALID",
]
_DENIED_GATES = (
    "sink_authorized",
    "provider_read_authorized",
    "credential_access_authorized",
    "token_refresh_authorized",
    "deployment_authorized",
    "new_teams_observation_authorized",
    "issue_739_release_authorized",
    "issue_632_live_authorized",
)
_ZERO_GATES = ("maximum_provider_reads", "maximum_tenant_writes", "maximum_deployments")


def validate_contract(contract: object) -> list[str]:
    if not isinstance(contract, dict):
        return ["contract must be an object"]
    errors: list[str] = []
    if set(contract) != {
        "schema_version", "contract_id", "status", "leading_issue", "base_contract",
        "specifications", "plans", "acceptance_ids", "result", "privacy", "gates",
        "validation_commands",
    }:
        errors.append("contract root fields differ from the closed allowlist")
    for key, expected in {
        "schema_version": "nac.bff-403-terminal-reason.verification/v2",
        "contract_id": "m365-bff-403-terminal-reason",
        "status": "LOCAL_INACTIVE_ONLY",
        "leading_issue": "https://github.com/notariat8/NaC/issues/756",
        "base_contract": "workflows/verification-contracts/m365-bff-403-diagnostic-event.verification.json",
        "acceptance_ids": ["AC-756-SD-03", "AC-756-SD-04", "AC-756-SD-05"],
    }.items():
        if contract.get(key) != expected:
            errors.append(f"invalid {key}")
    for name in ("specifications", "plans"):
        paths = contract.get(name)
        if not isinstance(paths, dict) or set(paths) != {"de", "en"}:
            errors.append(f"invalid {name}")
            continue
        for lang in ("de", "en"):
            if name == "specifications":
                expected = f"docs/{lang}/superpowers/specs/2026-09-26-m365-bff-403-diagnostic-event-design.md"
            else:
                expected = f"docs/{lang}/superpowers/plans/2026-09-26-m365-bff-403-direct-server-diagnosis.md"
            if paths.get(lang) != expected or not (ROOT / expected).is_file():
                errors.append(f"invalid {name}.{lang}")
    if not (ROOT / "workflows/verification-contracts/m365-bff-403-diagnostic-event.verification.json").is_file():
        errors.append("base contract is missing")
    if contract.get("result") != {
        "scope": "single_request_in_process_only",
        "reason_classes": _REASONS,
        "terminal_branch_only": True,
        "maximum_reasons_per_request": 1,
        "unclassified_fallback": "DENIAL_UNCLASSIFIED",
        "existing_public_403_body": '{"status":403,"error":{"code":"ACCESS_DENIED"}}',
    }:
        errors.append("result scope or reason classes changed")
    if contract.get("privacy") != {
        "inference_bearing_classes": _INFERENCE_BEARING,
        "default_external_reason": "ACCESS_DECISION_REJECTED",
        "raw_graph_values_allowed": False,
        "subject_identifiers_allowed": False,
        "request_payload_allowed": False,
        "class_specific_external_output_authorized": False,
        "class_specific_output_requires": [
            "separate_owner_approval",
            "class_specific_dpa_avv_basis",
            "class_specific_readership",
            "class_specific_retention",
            "bound_deployment_and_new_client_observation",
        ],
    }:
        errors.append("privacy boundary changed")
    gates = contract.get("gates")
    if not isinstance(gates, dict) or set(gates) != set(_DENIED_GATES) | set(_ZERO_GATES):
        errors.append("gate fields differ from the closed allowlist")
    else:
        if any(gates[key] is not False for key in _DENIED_GATES):
            errors.append("an inactive gate was enabled")
        if any(type(gates[key]) is not int or gates[key] != 0 for key in _ZERO_GATES):
            errors.append("effect counters must remain zero")
    commands = contract.get("validation_commands")
    required = {
        "python scripts/validate_m365_bff_403_terminal_reason.py",
        "python -m unittest discover -s tests -p test_nac_bff_403_terminal_reason.py",
        "python -m unittest discover -s tests -p test_nac_bff_live_graph_ports.py",
        "python -m unittest discover -s tests -p test_nac_bff_workbench_endpoint.py",
        "python scripts/validate_spec_traceability.py",
        "python scripts/validate_language_parity.py",
        "graft check",
    }
    if not isinstance(commands, list) or any(type(item) is not str for item in commands) or not required.issubset(set(commands)):
        errors.append("required validation commands are missing")
    return errors


def _unique_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def validate() -> list[str]:
    try:
        data = json.loads(
            CONTRACT_PATH.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_pairs,
        )
    except (OSError, ValueError, UnicodeError) as exc:
        return [f"contract cannot be read: {type(exc).__name__}"]
    return validate_contract(data)


if __name__ == "__main__":
    failures = validate()
    for failure in failures:
        print(f"ERROR: {failure}")
    print("STATUS: PASSED" if not failures else "STATUS: FAILED")
    raise SystemExit(bool(failures))
