from __future__ import annotations

import fnmatch
import json
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENT_CONTEXT = REPO_ROOT / "agent-context" / "index.json"
DECISION_INDEX = REPO_ROOT / "agent-context" / "decision-index.json"
INVARIANT_INDEX = REPO_ROOT / "agent-context" / "invariant-index.json"
VERIFICATION_CONTRACT = (
    REPO_ROOT / "workflows" / "verification-contracts" / "m365-matter-access-delegation.verification.json"
)
DOMAIN_CONTRACT = REPO_ROOT / "workflows" / "contracts" / "m365-matter-access-delegation.contract.json"

REQUIRED_DECISIONS = {
    "ADR-M365-MATTER-ACCESS-001",
    "ADR-M365-MATTER-ACCESS-002",
    "ADR-M365-MATTER-ACCESS-003",
}
REQUIRED_INVARIANTS = {
    "invariant.m365_matter_access.no_blanket_visibility",
    "invariant.m365_matter_access.timeboxed_deputy_access",
    "invariant.m365_matter_access.reason_approver_audit_required",
    "invariant.m365_graph.rest_only_no_legacy_sdk",
    "invariant.m365_matter_access.owner_gate_before_live_write",
    "invariant.m365_evidence.redacted_only_no_matter_payloads",
}
REQUIRED_EVIDENCE = {
    "domain_contract",
    "domain_verification_contract",
    "decision_index",
    "invariant_index",
    "matter_access_delegation_smoke",
    "matter_access_apply_readiness",
    "matter_access_apply_request_plan",
    "negative_apply_policy_smoke",
    "release_gate_evidence_index",
}
PROHIBITED_MARKERS = {
    "client" + "_secret",
    "BEGIN " + "PRIVATE KEY",
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
    print("OK: Verification-contract domain pilot, ADR index and invariant index are aligned.")
    return 0


def validate() -> list[str]:
    errors: list[str] = []
    context = _read_json(AGENT_CONTEXT, errors)
    decisions = _read_json(DECISION_INDEX, errors)
    invariants = _read_json(INVARIANT_INDEX, errors)
    verification = _read_json(VERIFICATION_CONTRACT, errors)
    domain = _read_json(DOMAIN_CONTRACT, errors)

    if context:
        errors.extend(_validate_agent_context(context))
    if decisions:
        errors.extend(_validate_decisions(decisions))
    if invariants:
        errors.extend(_validate_invariants(invariants))
    if verification:
        errors.extend(_validate_verification_contract(verification))
    if domain:
        errors.extend(_validate_domain_contract(domain))
    if verification and decisions and invariants:
        errors.extend(_validate_crosswalk(verification, decisions, invariants))
    return errors


def _validate_agent_context(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    verification_contracts = set(_string_list(payload.get("verification_contracts")))
    if "workflows/verification-contracts/m365-matter-access-delegation.verification.json" not in verification_contracts:
        errors.append("agent-context/index.json must list the M365 matter-access verification contract")

    category_paths: dict[str, set[str]] = {}
    for layer in payload.get("layers", []):
        if not isinstance(layer, dict):
            continue
        for category in layer.get("categories", []):
            if isinstance(category, dict):
                category_paths[str(category.get("id"))] = set(_string_list(category.get("paths")))

    if "agent-context/decision-index.json" not in category_paths.get("history", set()):
        errors.append("agent-context/index.json history category must include decision-index.json")
    if "agent-context/invariant-index.json" not in category_paths.get("guardrails", set()):
        errors.append("agent-context/index.json guardrails category must include invariant-index.json")
    return errors


def _validate_decisions(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "nac.agent-decision-index/v0.1":
        errors.append("agent-context/decision-index.json has wrong schema_version")
    decisions = payload.get("decisions")
    if not isinstance(decisions, list):
        return errors + ["agent-context/decision-index.json decisions must be a list"]
    by_id = {str(item.get("id")): item for item in decisions if isinstance(item, dict)}
    for decision_id in sorted(REQUIRED_DECISIONS - set(by_id)):
        errors.append(f"decision-index missing required decision {decision_id}")
    for decision_id, decision in by_id.items():
        if decision.get("status") != "accepted":
            errors.append(f"{decision_id} must be accepted")
        if decision.get("domain") != "m365_matter_access_delegation":
            errors.append(f"{decision_id} must be mapped to m365_matter_access_delegation")
        if not _string_list(decision.get("source_paths")):
            errors.append(f"{decision_id} must list source_paths")
        for rel_path in _string_list(decision.get("source_paths")):
            _require_existing(rel_path, f"{decision_id}.source_paths", errors)
        if "workflows/verification-contracts/m365-matter-access-delegation.verification.json" not in _string_list(
            decision.get("verification_contracts")
        ):
            errors.append(f"{decision_id} must reference the matter-access verification contract")
    return errors


def _validate_invariants(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "nac.agent-invariant-index/v0.1":
        errors.append("agent-context/invariant-index.json has wrong schema_version")
    invariants = payload.get("invariants")
    if not isinstance(invariants, list):
        return errors + ["agent-context/invariant-index.json invariants must be a list"]
    by_id = {str(item.get("id")): item for item in invariants if isinstance(item, dict)}
    for invariant_id in sorted(REQUIRED_INVARIANTS - set(by_id)):
        errors.append(f"invariant-index missing required invariant {invariant_id}")
    for invariant_id, invariant in by_id.items():
        if invariant.get("severity") != "critical":
            errors.append(f"{invariant_id} must be critical")
        if not str(invariant.get("statement", "")).strip():
            errors.append(f"{invariant_id} must include a statement")
        for rel_path in _string_list(invariant.get("source_paths")):
            _require_existing(rel_path, f"{invariant_id}.source_paths", errors)
        enforced_by = _string_list(invariant.get("enforced_by"))
        if "scripts/validate_verification_contracts_domain_pilot.py" not in enforced_by:
            errors.append(f"{invariant_id} must be enforced by validate_verification_contracts_domain_pilot.py")
        for rel_path in enforced_by:
            _require_existing(rel_path, f"{invariant_id}.enforced_by", errors)
    return errors


def _validate_verification_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("schema_version") != "nac.verification-contract/v0.1":
        errors.append("matter-access verification contract has wrong schema_version")
    if payload.get("contract_id") != "verification.m365_matter_access_delegation":
        errors.append("matter-access verification contract has wrong contract_id")
    if payload.get("domain_contract_id") != "m365.matter_access_delegation":
        errors.append("matter-access verification contract must point to the domain contract id")

    applies_when = payload.get("applies_when")
    if not isinstance(applies_when, dict) or not _string_list(applies_when.get("paths")):
        errors.append("matter-access verification contract requires applies_when.paths")
    else:
        for pattern in _string_list(applies_when.get("paths")):
            if not _path_or_glob_matches(pattern):
                errors.append(f"matter-access verification contract applies_when path matches nothing: {pattern}")

    required_context = payload.get("required_context")
    if not isinstance(required_context, dict):
        errors.append("matter-access verification contract requires required_context")
    else:
        for field in ("always_on", "scoped", "on_demand", "runtime"):
            if not _string_list(required_context.get(field)):
                errors.append(f"matter-access verification contract required_context.{field} is empty")

    for field in ("checks", "invariants", "required_evidence"):
        if not _string_list(payload.get(field)):
            errors.append(f"matter-access verification contract {field} must not be empty")

    evidence = set(_string_list(payload.get("required_evidence")))
    for item in sorted(REQUIRED_EVIDENCE - evidence):
        errors.append(f"matter-access verification contract required_evidence missing {item}")

    thresholds = payload.get("thresholds")
    if not isinstance(thresholds, dict):
        errors.append("matter-access verification contract thresholds must be an object")
    else:
        if thresholds.get("minimum_indexed_decisions", 0) < len(REQUIRED_DECISIONS):
            errors.append("minimum_indexed_decisions is below required decisions")
        if thresholds.get("minimum_indexed_invariants", 0) < len(REQUIRED_INVARIANTS):
            errors.append("minimum_indexed_invariants is below required invariants")
        if thresholds.get("required_matter_access_release_gate_artifacts") != 3:
            errors.append("required_matter_access_release_gate_artifacts must be 3")
        if thresholds.get("max_live_apply_steps_without_owner_gate") != 0:
            errors.append("max_live_apply_steps_without_owner_gate must be 0")

    pass_condition = payload.get("pass_condition")
    if not isinstance(pass_condition, dict) or pass_condition.get("all_checks_pass") is not True:
        errors.append("matter-access verification contract pass_condition.all_checks_pass must be true")
    failure_behavior = payload.get("failure_behavior")
    if not isinstance(failure_behavior, dict) or failure_behavior.get("quality_gate_failure") != "block_completion":
        errors.append("matter-access verification contract quality_gate_failure must block completion")
    return errors


def _validate_domain_contract(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("contract_id") != "m365.matter_access_delegation":
        errors.append("domain contract id must stay m365.matter_access_delegation")
    graph = payload.get("graph")
    if not isinstance(graph, dict):
        errors.append("domain contract graph block missing")
    else:
        expected = {
            "rest_only": True,
            "raw_http_required": True,
            "sdk_allowed": False,
            "legacy_sharepoint_api_allowed": False,
            "graph_beta_allowed": False,
        }
        for key, value in expected.items():
            if graph.get(key) is not value:
                errors.append(f"domain contract graph.{key} must be {value!r}")
    scope = payload.get("scope")
    if not isinstance(scope, dict):
        errors.append("domain contract scope block missing")
    else:
        if scope.get("owner_gate_required_before_future_apply") is not True:
            errors.append("domain contract must require owner gate before future apply")
        for key in (
            "tenant_mutation_allowed_now",
            "team_membership_mutation_allowed_now",
            "sharepoint_item_permission_mutation_allowed_now",
            "sharepoint_file_content_read_allowed_now",
            "matter_payload_storage_allowed_now",
            "stores_tokens_or_secrets",
        ):
            if scope.get(key) is not False:
                errors.append(f"domain contract scope.{key} must be false")
    access_decision = payload.get("access_decision")
    if isinstance(access_decision, dict):
        required_true = (
            "grant_must_include_reason",
            "grant_must_include_valid_from",
            "grant_must_include_valid_until",
            "grant_must_include_approver",
            "grant_must_include_audit_correlation_id",
        )
        for key in required_true:
            if access_decision.get(key) is not True:
                errors.append(f"domain contract access_decision.{key} must be true")
        if access_decision.get("automation_may_approve_grant") is not False:
            errors.append("agents must not approve deputy grants")
        if access_decision.get("unbounded_team_access_allowed") is not False:
            errors.append("unbounded team access must remain blocked")
    else:
        errors.append("domain contract access_decision block missing")
    return errors


def _validate_crosswalk(
    verification: dict[str, Any],
    decisions: dict[str, Any],
    invariants: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    verification_invariants = " ".join(_string_list(verification.get("invariants"))).lower()
    for required_phrase in (
        "matter visibility",
        "deputy grants require",
        "graph rest",
        "owner approval",
        "redacted",
    ):
        if required_phrase not in verification_invariants:
            errors.append(f"matter-access verification invariants must mention {required_phrase!r}")

    decision_ids = {str(item.get("id")) for item in decisions.get("decisions", []) if isinstance(item, dict)}
    invariant_ids = {str(item.get("id")) for item in invariants.get("invariants", []) if isinstance(item, dict)}
    if len(decision_ids & REQUIRED_DECISIONS) < len(REQUIRED_DECISIONS):
        errors.append("decision-index crosswalk is incomplete")
    if len(invariant_ids & REQUIRED_INVARIANTS) < len(REQUIRED_INVARIANTS):
        errors.append("invariant-index crosswalk is incomplete")
    return errors


def _read_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"missing JSON file: {path.relative_to(REPO_ROOT)}")
        return None
    text = path.read_text(encoding="utf-8")
    for marker in PROHIBITED_MARKERS:
        if marker.lower() in text.lower():
            errors.append(f"{path.relative_to(REPO_ROOT)} contains prohibited marker {marker}")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        errors.append(f"{path.relative_to(REPO_ROOT)} is invalid JSON: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{path.relative_to(REPO_ROOT)} must be a JSON object")
        return None
    return payload


def _require_existing(rel_path: str, context: str, errors: list[str]) -> None:
    if not (REPO_ROOT / rel_path).exists():
        errors.append(f"{context} references missing path {rel_path}")


def _path_or_glob_matches(pattern: str) -> bool:
    if (REPO_ROOT / pattern).exists():
        return True
    files = [
        path.relative_to(REPO_ROOT).as_posix()
        for path in REPO_ROOT.rglob("*")
        if ".git" not in path.parts and "out" not in path.parts and path.is_file()
    ]
    return any(fnmatch.fnmatch(path, pattern) for path in files)


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item.strip()]


if __name__ == "__main__":
    raise SystemExit(main())
