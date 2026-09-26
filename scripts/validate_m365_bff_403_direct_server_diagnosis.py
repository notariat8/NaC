"""Validate the inactive, offline-only Issue #756 Stage A contract."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "workflows/verification-contracts/"
    "m365-bff-403-direct-server-diagnosis.verification.json"
)

_TARGET_BINDINGS = (
    "workspace_binding_sha256",
    "app_id_binding_sha256",
    "function_binding_sha256",
    "application_insights_binding_sha256",
    "tenant_binding_sha256",
    "package_binding_sha256",
    "account_binding_sha256",
    "principal_id_binding_sha256",
    "permission_binding_sha256",
    "source_evidence_binding_sha256",
    "avv_dpa_binding_sha256",
    "observation_window_binding_sha256",
    "receipt_binding_sha256",
    "retention_binding_sha256",
    "no_refresh_capability_binding_sha256",
    "commit_binding_sha256",
    "tree_binding_sha256",
    "toolchain_binding_sha256",
)

_EXPECTED_RESOURCES = [
    {
        "id": "azure_function_metadata",
        "method": "GET",
        "endpoint_binding_sha256": "UNBOUND",
        "projection": ["deployment_class", "configuration_digest"],
        "maximum_reads": 0,
    },
    {
        "id": "application_insights_metadata",
        "method": "GET",
        "endpoint_binding_sha256": "UNBOUND",
        "projection": ["capture_enabled", "retention_covers_window"],
        "maximum_reads": 0,
    },
    {
        "id": "azure_function_request_log",
        "method": "GET",
        "endpoint_binding_sha256": "UNBOUND",
        "query_sha256": "UNBOUND",
        "projection": [
            "request_observed",
            "http_class",
            "request_correlation_binding_sha256",
        ],
        "maximum_reads": 0,
    },
]

_EXPECTED_READ_POLICY = {
    "required_before_port_factory": True,
    "required_before_every_read": True,
    "atomic_budget_consume": True,
    "maximum_historical_query_gets": 1,
    "redirect_allowed": False,
    "retry_allowed": False,
    "paging_allowed": False,
    "body_allowed": False,
    "resource_discovery_allowed": False,
    "no_refresh_proof_required": True,
    "receipt_provenance_required": True,
}

_EXPECTED_APPROVAL = {
    "evidence_status": "NOT_CREATED",
    "same_principal_accounts_are_distinct_approvers": False,
    "solo_without_cited_two_person_duty": "OWNER_SOLO_APPROVAL",
    "solo_four_eyes_satisfied": False,
    "uncited_two_person_duty": "BLOCKED_REQUIREMENT_CITATION_MISSING",
    "cited_two_person_duty_with_one_principal": "BLOCKED_SINGLE_PRINCIPAL",
}

_EXPECTED_GATES = {
    "provider_read_authorized": False,
    "credential_access_authorized": False,
    "no_refresh_capability_proven": False,
    "token_refresh_authorized": False,
    "login_authorized": False,
    "tenant_write_authorized": False,
    "deployment_authorized": False,
    "new_reproduction_authorized": False,
    "issue_739_release_authorized": False,
    "issue_632_live_authorized": False,
    "maximum_provider_reads": 0,
    "maximum_tenant_writes": 0,
    "maximum_deployments": 0,
}


def _strict_equal(actual: object, expected: object) -> bool:
    """Keep JSON booleans distinct from numbers, including zero budgets."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(
            _strict_equal(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _strict_equal(item, value) for item, value in zip(actual, expected)
        )
    return actual == expected


def validate_contract(contract: object) -> list[str]:
    """Reject every field/value outside the closed, non-live repository contract."""

    if not isinstance(contract, dict):
        return ["contract must be an object"]
    errors: list[str] = []
    expected_root = {
        "schema_version",
        "contract_id",
        "status",
        "leading_issue",
        "historical_issue",
        "delivery_mode",
        "risk_gate",
        "specifications",
        "plans",
        "acceptance_ids",
        "target",
        "resources",
        "read_policy",
        "evidence_states",
        "approval_boundary",
        "gates",
        "validation_commands",
    }
    if set(contract) != expected_root:
        errors.append("contract root fields differ from the closed allowlist")
    for name, expected in {
        "schema_version": "nac.bff-403-direct-server-diagnosis.verification/v1",
        "contract_id": "m365-bff-403-direct-server-diagnosis",
        "status": "LOCAL_INACTIVE_ONLY",
        "leading_issue": "https://github.com/notariat8/NaC/issues/756",
        "historical_issue": "https://github.com/notariat8/NaC/issues/748",
        "delivery_mode": "Protected PR",
        "risk_gate": "Human Approval",
        "acceptance_ids": [f"AC-756-SD-{number:02d}" for number in range(1, 6)],
    }.items():
        if not _strict_equal(contract.get(name), expected):
            errors.append(f"invalid {name}")

    for name, folder, suffix in (
        ("specifications", "specs", "-design"),
        ("plans", "plans", ""),
    ):
        paths = contract.get(name)
        if not isinstance(paths, dict) or set(paths) != {"de", "en"}:
            errors.append(f"invalid {name}")
            continue
        for language in ("de", "en"):
            filename = (
                "2026-09-26-m365-bff-403-diagnostic-event"
                if folder == "specs"
                else "2026-09-26-m365-bff-403-direct-server-diagnosis"
            )
            expected = f"docs/{language}/superpowers/{folder}/{filename}{suffix}.md"
            if paths.get(language) != expected or not (ROOT / expected).is_file():
                errors.append(f"invalid {name}.{language}")

    target = {"workspace_class": "synthetic_notary_team_01"}
    target.update({name: "UNBOUND" for name in _TARGET_BINDINGS})
    if not _strict_equal(contract.get("target"), target):
        errors.append("target must remain opaque and unbound")
    if not _strict_equal(contract.get("resources"), _EXPECTED_RESOURCES):
        errors.append("resource paths, projections or budgets changed")
    if not _strict_equal(contract.get("read_policy"), _EXPECTED_READ_POLICY):
        errors.append("read policy changed")
    if not _strict_equal(contract.get("evidence_states"), [
        "BFF_NOT_DEPLOYED",
        "REQUEST_ATTRIBUTED_STATUS_ONLY",
        "UNPROVEN",
    ]):
        errors.append("evidence states changed")
    if not _strict_equal(contract.get("approval_boundary"), _EXPECTED_APPROVAL):
        errors.append("approval boundary changed")
    if not _strict_equal(contract.get("gates"), _EXPECTED_GATES):
        errors.append("a non-live gate changed")
    commands = contract.get("validation_commands")
    if (
        not isinstance(commands, list)
        or any(type(command) is not str for command in commands)
        or not {
            "python scripts/validate_m365_bff_403_direct_server_diagnosis.py",
            "python -m unittest discover -s tests -p test_nac_bff_403_direct_server_diagnosis.py",
            "python scripts/validate_spec_traceability.py",
            "python scripts/validate_language_parity.py",
            "graft check",
            "python scripts/nac.py doctor --profile strict",
        }.issubset(set(commands))
    ):
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
        contract = json.loads(
            CONTRACT_PATH.read_text(encoding="utf-8"),
            object_pairs_hook=_unique_pairs,
        )
    except (OSError, ValueError, UnicodeError) as exc:
        return [f"contract cannot be read: {type(exc).__name__}"]
    return validate_contract(contract)


if __name__ == "__main__":
    failures = validate()
    for failure in failures:
        print(f"ERROR: {failure}")
    print("STATUS: PASSED" if not failures else "STATUS: FAILED")
    raise SystemExit(bool(failures))
