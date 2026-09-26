"""Offline contract check for the inactive Issue #756 BFF 403 diagnostic."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT / "workflows/verification-contracts/m365-bff-403-diagnostic-event.verification.json"
)
EXPECTED_FIELDS = [
    "schema_version",
    "observed_at_utc",
    "route_class",
    "method",
    "http_class",
    "reason_class",
    "request_correlation_binding_sha256",
]
EXPECTED_REASONS = [
    "REQUEST_SCOPE_REJECTED",
    "ACCESS_DECISION_UNAVAILABLE",
    "ACCESS_DECISION_REJECTED",
    "DENIAL_UNCLASSIFIED",
]
EXPECTED_ACCEPTANCE = [f"AC-748-BD-{number:02d}" for number in range(1, 7)]
DENIED_GATES = (
    "sink_enabled_by_default",
    "provider_read_authorized",
    "credential_access_authorized",
    "token_refresh_authorized",
    "deployment_authorized",
    "new_reproduction_authorized",
    "issue_739_release_authorized",
    "issue_632_live_authorized",
)


def validate_contract(contract: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(contract, dict):
        return ["contract must be an object"]
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
        "event",
        "approval_boundary",
        "gates",
        "future_activation_requires",
        "validation_commands",
    }
    if set(contract) != expected_root:
        errors.append("contract root fields differ from the closed allowlist")
    fixed = {
        "schema_version": "nac.bff-403-diagnostic-event.verification/v1",
        "contract_id": "m365-bff-403-diagnostic-event",
        "status": "LOCAL_INACTIVE_ONLY",
        "leading_issue": "https://github.com/notariat8/NaC/issues/756",
        "historical_issue": "https://github.com/notariat8/NaC/issues/748",
        "delivery_mode": "Protected PR",
        "risk_gate": "Human Approval",
        "acceptance_ids": EXPECTED_ACCEPTANCE,
    }
    for key, expected in fixed.items():
        if contract.get(key) != expected:
            errors.append(f"invalid {key}")
    for name, folder in (("specifications", "specs"), ("plans", "plans")):
        paths = contract.get(name)
        if not isinstance(paths, dict) or set(paths) != {"de", "en"}:
            errors.append(f"invalid {name}")
            continue
        for language in ("de", "en"):
            expected = (
                f"docs/{language}/superpowers/{folder}/"
                f"2026-09-26-m365-bff-403-diagnostic-event"
                f"{'-design' if folder == 'specs' else ''}.md"
            )
            if paths.get(language) != expected or not (ROOT / expected).is_file():
                errors.append(f"invalid {name}.{language}")
    if contract.get("target") != {
        "workspace_class": "synthetic_notary_team_01",
        "route_class": "workbench_snapshot",
        "method": "GET",
        "http_class": 403,
    }:
        errors.append("target is not the fixed synthetic GET")
    event = contract.get("event")
    if not isinstance(event, dict) or event != {
        "schema_version": "nac.bff-403-diagnostic-event/v1",
        "field_allowlist": EXPECTED_FIELDS,
        "reason_classes": EXPECTED_REASONS,
        "unbound_correlation_behavior": "NO_EVENT_NO_FALLBACK_HASH",
        "positive_attribution_requires_protected_receipt_match": True,
        "public_403_body": '{"status":403,"error":{"code":"ACCESS_DENIED"}}',
        "maximum_events_per_request": 1,
    }:
        errors.append("event allowlist or correlation gate changed")
    if contract.get("approval_boundary") != {
        "evidence_status": "NOT_CREATED",
        "same_principal_accounts_are_distinct_approvers": False,
        "solo_without_cited_two_person_duty": "OWNER_SOLO_APPROVAL",
        "solo_four_eyes_satisfied": False,
        "uncited_two_person_duty": "BLOCKED_REQUIREMENT_CITATION_MISSING",
        "cited_two_person_duty_with_one_principal": "BLOCKED_SINGLE_PRINCIPAL",
    }:
        errors.append("approval boundary changed or claims unsupported evidence")
    gates = contract.get("gates")
    if not isinstance(gates, dict) or set(gates) != set(DENIED_GATES) | {
        "maximum_provider_reads", "maximum_tenant_writes", "maximum_deployments"
    }:
        errors.append("gate fields differ from the closed allowlist")
    else:
        if any(gates[name] is not False for name in DENIED_GATES):
            errors.append("an inactive gate was enabled")
        if any(
            type(gates[name]) is not int or gates[name] != 0
            for name in (
                "maximum_provider_reads",
                "maximum_tenant_writes",
                "maximum_deployments",
            )
        ):
            errors.append("effect counters must remain zero")
    required = contract.get("future_activation_requires")
    if required != [
        "separate_owner_approval",
        "target_and_package_commit_tree_binding",
        "dpa_avv_basis",
        "retention_and_access_group",
        "telemetry_capture_proof",
        "protected_client_receipt_binding",
        "principal_qualification_and_source_bound_approval",
    ]:
        errors.append("future activation bindings are incomplete")
    commands = contract.get("validation_commands")
    if not isinstance(commands, list) or any(type(command) is not str for command in commands) or not {
        "python scripts/validate_m365_bff_403_diagnostic_event.py",
        "python -m unittest discover -s tests -p test_nac_bff_403_diagnostic_event.py",
        "python scripts/validate_spec_traceability.py",
        "python scripts/validate_language_parity.py",
        "graft check",
        "python scripts/nac.py doctor --profile strict",
    }.issubset(set(commands)):
        errors.append("required validation commands are missing")
    return errors


def validate() -> list[str]:
    try:
        contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"contract cannot be read: {type(exc).__name__}"]
    return validate_contract(contract)


if __name__ == "__main__":
    failures = validate()
    for failure in failures:
        print(f"ERROR: {failure}")
    print("STATUS: PASSED" if not failures else "STATUS: FAILED")
    raise SystemExit(bool(failures))
