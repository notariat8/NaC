from __future__ import annotations

import inspect
import json
import sys
import urllib.parse
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

EXPECTED_ACCEPTANCE_IDS = [f"AC-S4-{number:02d}" for number in range(1, 8)]
EXPECTED_ACCEPTANCE_REQUIREMENTS = {
    "AC-S4-01": "The adapter generates only Graph REST v1.0 GETs for the bound site/list and selects exactly id, eTag, BusinessCaseTypeId, LifecycleStatus, Selectable, and CatalogVersion.",
    "AC-S4-02": "Paging is complete only after a validated end; foreign hosts/bases/sites/lists, loops, invalid payloads, and page/item limit breaches never produce a valid type.",
    "AC-S4-03": "After a complete read, an identical row ETag is mapped locally to NOT_MODIFIED; different ETags return the new row. A row ETag is never misused as collection If-None-Match.",
    "AC-S4-04": "An incorrect site, list, operation, role, or runtime permission is blocked before transport; the contract allows only Sites.Selected and no schema/provisioning rights.",
    "AC-S4-05": "Graph responses are strictly typed and reduced to the registry fields; viewer, process, matter, document, and person fields do not affect type validity.",
    "AC-S4-06": "HTTP/transport errors are mapped to fixed redacted reason codes; tokens, paths, IDs, Graph bodies, and matter values appear in neither results nor exceptions/evidence.",
    "AC-S4-07": "The central CLI, domain/verification contract, standalone validator, fake Graph tests, DE/EN documentation, strict gate, and independent base...head review pass.",
}
EXPECTED_DOMAIN_KEYS = {
    "schema_version", "contract_id", "title", "status", "leading_issue", "slice",
    "adapter_boundary", "binding", "authorization", "graph_request", "response_typing",
    "paging", "etag_semantics", "redaction", "offline_cli", "acceptance_criteria",
}
EXPECTED_VERIFICATION_KEYS = {
    "schema_version", "contract_id", "domain_contract_id", "title", "status",
    "leading_issue", "acceptance_ids", "applies_when", "required_context", "checks",
    "invariants", "thresholds", "required_evidence", "evidence_policy",
    "exit_conditions", "pass_condition", "failure_behavior",
}
EXPECTED_SELECTED_PROPERTIES = [
    "id", "eTag", "BusinessCaseTypeId", "LifecycleStatus", "Selectable", "CatalogVersion",
]
EXPECTED_CLI = "nac m365 teams-sharepoint business-case-type-read-plan"
REQUIRED_APPLIES_PATHS = {
    "src/nac_m365_graph/business_case_type_*.py",
    "src/notary_kg/business_case_type_transport.py",
    "src/nac_cli/cli.py",
    "workflows/contracts/business-case-type-graph-read-edge.contract.json",
    "workflows/verification-contracts/business-case-type-graph-read-edge.verification.json",
    "scripts/validate_business_case_type_graph_read_edge.py",
    "tests/test_business_case_type_graph_read_edge*.py",
}
REQUIRED_CHECKS = {
    "python3 -m unittest tests.test_business_case_type_graph_read_edge tests.test_business_case_type_graph_read_edge_cli tests.test_business_case_type_graph_read_edge_contract",
    "python3 scripts/validate_business_case_type_graph_read_edge.py",
    "python3 scripts/nac.py m365 teams-sharepoint business-case-type-read-plan --help",
    "python3 scripts/nac.py contracts verify",
    "python3 scripts/validate_spec_traceability.py",
    "python3 scripts/validate_language_parity.py",
    "python3 scripts/validate_doc_links.py",
    "python3 scripts/nac.py doctor --profile strict",
    "git diff --check",
}
REQUIRED_AGENT_PATHS = REQUIRED_APPLIES_PATHS | {
    "docs/de/architecture/business-case-type-id.md",
    "docs/en/architecture/business-case-type-id.md",
    "docs/de/cli.md",
    "docs/en/cli.md",
    "docs/de/superpowers/specs/2026-07-11-business-case-type-graph-read-edge-s4-design.md",
    "docs/en/superpowers/specs/2026-07-11-business-case-type-graph-read-edge-s4-design.md",
    "docs/de/superpowers/plans/2026-07-11-business-case-type-graph-read-edge-s4.md",
    "docs/en/superpowers/plans/2026-07-11-business-case-type-graph-read-edge-s4.md",
}
REQUIRED_INVARIANTS = {
    "invariant.business_case_type.graph_exact_sites_selected_read_grant",
    "invariant.business_case_type.graph_same_filter_paging",
    "invariant.business_case_type.graph_no_collection_if_none_match",
    "invariant.business_case_type.graph_redaction_viewer_isolation",
}


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        return []
    return value


def validate_domain_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(contract) != EXPECTED_DOMAIN_KEYS:
        errors.append("domain contract top-level shape mismatch")
    for field, expected in {
        "schema_version": "nac.business-case-type-graph-read-edge/v0.1",
        "contract_id": "m365.business_case_type_graph_read_edge",
        "status": "implemented_offline",
        "leading_issue": "https://github.com/notariat8/NaC/issues/616",
    }.items():
        if contract.get(field) != expected:
            errors.append(f"domain contract {field} mismatch")

    expected_slice = {
        "id": "S4", "read_edge_only": True, "s3_domain_runtime_unchanged": True,
        "s4b_writes_in_scope": False, "allowed_live_graph_calls": 0,
    }
    if contract.get("slice") != expected_slice:
        errors.append("domain contract S4 slice boundary mismatch")

    adapter = contract.get("adapter_boundary", {})
    expected_adapter = {
        "adapter_package": "nac_m365_graph", "domain_package": "notary_kg",
        "domain_port": "BusinessCaseTypeRegistryReadPort", "domain_result": "RegistryFetchResult",
        "adapter_may_make_domain_validity_decision": False, "adapter_may_read_viewer_port": False,
    }
    if adapter != expected_adapter:
        errors.append("domain contract adapter boundary mismatch")

    binding = contract.get("binding", {})
    expected_binding = {
        "immutable_per_adapter_instance": True,
        "required_values": ["site_id", "list_id", "operation", "role", "runtime_permission", "site_grant_role"],
        "logical_list_name": "Vorgangsartenregister", "site_id_must_equal_bound_value": True,
        "list_id_must_equal_bound_value": True, "mismatch_behavior": "block_before_transport",
        "site_grant_role_exact": "read", "broader_site_grant_roles_allowed": False,
    }
    if binding != expected_binding:
        errors.append("domain contract immutable binding or exact read grant mismatch")

    authorization = contract.get("authorization", {})
    if authorization.get("allowed_runtime_permissions_exact") != ["Sites.Selected"]:
        errors.append("domain contract runtime permission must be exactly Sites.Selected")
    for key in (
        "delegated_permissions_allowed", "schema_permissions_allowed",
        "provisioning_permissions_allowed", "broader_site_permissions_allowed",
    ):
        if authorization.get(key) is not False:
            errors.append(f"domain contract authorization {key} must be false")
    expected_forbidden = ["Sites.Read.All", "Sites.ReadWrite.All", "Sites.Manage.All", "Files.Read.All"]
    if authorization.get("forbidden_permissions") != expected_forbidden:
        errors.append("domain contract forbidden permissions mismatch")
    expected_roles = {
        "case_create_validation": ["notary", "notary_clerk", "substitution_notary", "substitution_clerk", "runtime_service"],
        "matter_type_correction_validation": ["MatterCorrector", "runtime_service"],
        "backfill_validation": ["BackfillOperator", "runtime_service"],
        "optional_process_read": ["notary", "notary_clerk", "substitution_notary", "substitution_clerk", "runtime_service"],
    }
    if authorization.get("operation_role_bindings") != expected_roles or authorization.get("unknown_operation_or_role_behavior") != "block_before_transport":
        errors.append("domain contract operation/role binding mismatch")

    request = contract.get("graph_request", {})
    expected_request = {
        "base_url": "https://graph.microsoft.com/v1.0", "api_version": "v1.0",
        "allowed_methods": ["GET"],
        "collection_path_template": "/sites/{bound-site-id}/lists/{bound-list-id}/items",
        "item_select_exact": ["id", "eTag"],
        "fields_select_exact": ["BusinessCaseTypeId", "LifecycleStatus", "Selectable", "CatalogVersion"],
        "selected_properties_exact": EXPECTED_SELECTED_PROPERTIES,
        "graph_beta_allowed": False, "graph_sdk_allowed": False,
        "sharepoint_rest_allowed": False, "pnp_allowed": False, "redirects_allowed": False,
        "request_headers": {
            "collection_if_none_match_allowed": False,
            "row_etag_as_collection_if_none_match_allowed": False,
        },
        "filter_fields_exact": ["BusinessCaseTypeId", "CatalogVersion"],
    }
    if request != expected_request:
        errors.append("domain contract exact Graph v1.0 GET/projection/filter/header semantics mismatch")

    expected_response = {
        "strict_payload_shape": True, "unknown_properties_discarded": True,
        "required_row_fields": EXPECTED_SELECTED_PROPERTIES,
        "viewer_fields_affect_validity": False, "process_fields_affect_validity": False,
        "matter_fields_affect_validity": False, "document_fields_affect_validity": False,
        "person_fields_affect_validity": False, "raw_graph_response_persisted": False,
        "max_response_bytes": 1048576,
    }
    if contract.get("response_typing") != expected_response:
        errors.append("domain contract strict response typing or viewer isolation mismatch")

    expected_paging = {
        "complete_collection_required": True, "partial_success_allowed": False,
        "next_link_must_be_absolute_https": True, "next_link_host_exact": "graph.microsoft.com",
        "next_link_base_path_exact": "/v1.0", "next_link_same_site_required": True,
        "next_link_same_list_required": True, "next_link_same_collection_required": True,
        "next_link_same_projection_required": True, "canonical_next_link_loop_detection": True,
        "max_pages": 100, "max_items": 1000,
        "loop_or_limit_behavior": "UNAVAILABLE_without_partial_rows",
        "invalid_payload_behavior": "UNAVAILABLE_without_partial_rows",
        "next_link_same_business_case_type_id_filter_required": True,
        "next_link_same_catalog_version_filter_required": True,
    }
    if contract.get("paging") != expected_paging:
        errors.append("domain contract complete same-filter paging semantics mismatch")

    expected_etag = {
        "collection_read_before_comparison": "complete", "local_comparison_only": True,
        "matching_row_count_required": 1, "matching_business_case_type_id_required": True,
        "identical_row_etag_result": "NOT_MODIFIED", "different_row_etag_result": "OK_with_new_row",
        "zero_multiple_or_incomplete_rows_may_return_not_modified": False,
        "http_304_extension_in_scope": False,
    }
    if contract.get("etag_semantics") != expected_etag:
        errors.append("domain contract local row ETag semantics mismatch")

    redaction = contract.get("redaction", {})
    if redaction.get("adapter_reason_codes") != [
        "transport_authentication_failed", "transport_authorization_failed",
        "transport_rate_limited", "transport_timeout", "transport_unavailable",
    ] or redaction.get("unknown_failure_maps_to") != "transport_unavailable":
        errors.append("domain contract fixed redacted reason-code semantics mismatch")
    if redaction.get("forbidden_in_results_exceptions_logs_and_evidence") != [
        "tokens", "credentials", "concrete_graph_paths", "site_ids", "list_ids",
        "item_ids", "graph_bodies", "matter_values",
    ]:
        errors.append("domain contract redaction boundary mismatch")

    offline_cli = contract.get("offline_cli", {})
    expected_cli = {
        "command": EXPECTED_CLI, "output": "redacted_offline_request_plan",
        "credentials_accepted_or_loaded": False, "http_allowed": False, "dns_allowed": False,
        "live_graph_client_instantiated": False, "live_calls_allowed": 0,
        "output_fields": ["method", "graph_version", "logical_resource_binding", "selected_field_names", "page_limit", "item_limit", "response_byte_limit", "gate_results", "contract_version"],
    }
    if offline_cli != expected_cli:
        errors.append("domain contract exact offline CLI/no-live-call semantics mismatch")

    criteria = contract.get("acceptance_criteria")
    expected_criteria = [
        {"id": acceptance_id, "requirement": EXPECTED_ACCEPTANCE_REQUIREMENTS[acceptance_id]}
        for acceptance_id in EXPECTED_ACCEPTANCE_IDS
    ]
    if criteria != expected_criteria:
        errors.append("domain contract AC-S4-01..07 exact semantic drift")
    return errors


def validate_verification_contract(verification: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(verification) != EXPECTED_VERIFICATION_KEYS:
        errors.append("verification contract top-level shape mismatch")
    for field, expected in {
        "schema_version": "nac.verification-contract/v0.1",
        "contract_id": "verification.business_case_type_graph_read_edge_s4",
        "domain_contract_id": "m365.business_case_type_graph_read_edge",
        "status": "implemented_offline",
        "leading_issue": "https://github.com/notariat8/NaC/issues/616",
    }.items():
        if verification.get(field) != expected:
            errors.append(f"verification contract {field} mismatch")
    if verification.get("acceptance_ids") != EXPECTED_ACCEPTANCE_IDS:
        errors.append("verification contract must contain exact AC-S4-01..07 order")
    applies = verification.get("applies_when", {})
    paths = set(_string_list(applies.get("paths"))) if set(applies) == {"paths"} else set()
    for path in sorted(REQUIRED_APPLIES_PATHS - paths):
        errors.append(f"verification contract applies_when.paths missing {path}")
    checks = set(_string_list(verification.get("checks")))
    for check in sorted(REQUIRED_CHECKS - checks):
        errors.append(f"verification contract checks missing {check}")
    invariants = _string_list(verification.get("invariants"))
    if len(invariants) != 7 or [item.split(":", 1)[0] for item in invariants] != EXPECTED_ACCEPTANCE_IDS:
        errors.append("verification contract requires ordered AC-S4-01..07 invariants")
    else:
        for item in invariants:
            acceptance_id, requirement = item.split(": ", 1)
            if requirement != EXPECTED_ACCEPTANCE_REQUIREMENTS[acceptance_id]:
                errors.append(f"verification contract {acceptance_id} semantic drift")
    expected_thresholds = {
        "required_acceptance_criteria": 7, "selected_item_and_registry_fields": 6,
        "max_pages": 100, "max_items": 1000, "max_response_bytes": 1048576,
        "allowed_live_graph_calls": 0,
        "allowed_write_methods": 0, "allowed_runtime_permissions": 1,
    }
    if verification.get("thresholds") != expected_thresholds:
        errors.append("verification contract thresholds mismatch")
    expected_evidence_policy = {
        "redacted_only": True, "raw_graph_responses_allowed": False,
        "credentials_or_tokens_allowed": False, "concrete_graph_paths_or_ids_allowed": False,
        "matter_values_allowed": False, "allowed_live_graph_calls": 0,
    }
    if verification.get("evidence_policy") != expected_evidence_policy:
        errors.append("verification contract redacted no-live evidence policy mismatch")
    expected_pass = {
        "all_checks_pass": True, "all_acceptance_ids_covered": True,
        "all_required_evidence_redacted": True, "s3_unchanged": True,
        "s4b_writes_absent": True, "allowed_live_graph_calls": 0,
        "no_unresolved_review_findings": True,
    }
    if verification.get("pass_condition") != expected_pass:
        errors.append("verification contract pass condition mismatch")
    failures = verification.get("failure_behavior", {})
    for key, expected in {
        "binding_permission_or_site_grant_mismatch": "block_before_transport",
        "next_link_filter_drift": "fail_closed_without_partial_rows",
        "row_etag_used_as_collection_if_none_match": "block_completion",
        "credential_http_dns_or_live_graph_attempt": "block_completion",
    }.items():
        if failures.get(key) != expected:
            errors.append(f"verification contract failure behavior mismatch: {key}")
    context = verification.get("required_context", {})
    if set(context) != {"always_on", "scoped", "on_demand", "runtime"} or any(not _string_list(context.get(key)) for key in context):
        errors.append("verification contract required_context shape mismatch")
    for key in ("required_evidence", "exit_conditions"):
        if not _string_list(verification.get(key)):
            errors.append(f"verification contract {key} must be non-empty")
    return errors


def validate_agent_context(agent_context: dict[str, Any]) -> list[str]:
    routes = [
        category
        for layer in agent_context.get("layers", []) if isinstance(layer, dict)
        for category in layer.get("categories", []) if isinstance(category, dict)
        if category.get("id") == "business_case_type_graph_read_edge_s4"
    ]
    if len(routes) != 1:
        return ["agent context requires exactly one business_case_type_graph_read_edge_s4 route"]
    paths = set(_string_list(routes[0].get("paths")))
    return [f"agent context S4 route missing {path}" for path in sorted(REQUIRED_AGENT_PATHS - paths)]


def validate_decisions_and_invariants(decisions: dict[str, Any], invariants: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    matching_decisions = [
        item for item in decisions.get("decisions", [])
        if isinstance(item, dict) and item.get("context_key") == "business_case_type_graph_read_edge_s4"
    ]
    if len(matching_decisions) != 1:
        errors.append("decision index requires exactly one S4 Graph read-edge decision")
    else:
        text = json.dumps(matching_decisions[0], sort_keys=True)
        for token in ("Sites.Selected", "read", "same-filter", "If-None-Match", "viewer"):
            if token.lower() not in text.lower():
                errors.append(f"S4 decision semantic token missing: {token}")
    indexed = {
        item.get("id"): item for item in invariants.get("invariants", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for invariant_id in sorted(REQUIRED_INVARIANTS - set(indexed)):
        errors.append(f"invariant index missing {invariant_id}")
    required_enforcement = {
        "scripts/validate_business_case_type_graph_read_edge.py",
        "tests/test_business_case_type_graph_read_edge.py",
        "tests/test_business_case_type_graph_read_edge_cli.py",
    }
    for invariant_id in REQUIRED_INVARIANTS & set(indexed):
        enforced_by = set(_string_list(indexed[invariant_id].get("enforced_by")))
        for path in sorted(required_enforcement - enforced_by):
            errors.append(f"{invariant_id} enforced_by missing {path}")
    return errors


def validate_document_traceability(texts: dict[str, str]) -> list[str]:
    errors: list[str] = []
    for label, text in texts.items():
        for acceptance_id in EXPECTED_ACCEPTANCE_IDS:
            if f"**{acceptance_id}:**" not in text:
                errors.append(f"{label} missing mapped acceptance criterion {acceptance_id}")
        if "#616" not in text and "issues/616" not in text:
            errors.append(f"{label} missing traceability token Issue 616")
        for token in (EXPECTED_CLI, "Sites.Selected", "S4b"):
            if token not in text:
                errors.append(f"{label} missing traceability token {token}")
        if label == "DE spec" and "Status: Runtime offline implementiert in PR #617; Governance-Synchronisierung im S5-PR bis zu grüner Remote-CI offen; S4b-Writes bleiben offen" not in text:
            errors.append("DE spec implementation status mismatch")
        if label == "EN spec":
            if "Status: runtime implemented offline in PR #617; governance synchronization remains open in the S5 PR until remote CI is green; S4b writes remain open" not in text:
                errors.append("EN spec implementation status mismatch")
            if "5. the identical `BusinessCaseTypeId` and `CatalogVersion` filters." not in text:
                errors.append("EN spec normative NextLink filter binding missing")
        if label in {"DE plan", "EN plan"}:
            lowered = text.lower()
            for forbidden in ("kein runtime-code", "no runtime code", "planungsstand", "planning state"):
                if forbidden in lowered:
                    errors.append(f"{label} retains forbidden planning-only wording: {forbidden}")
            for wp in range(1, 9):
                if f"- [x] **WP{wp} " not in text:
                    errors.append(f"{label} must mark WP{wp} complete")
            if "- [ ] **WP9 " not in text:
                errors.append(f"{label} must keep WP9 pending until the synchronizing PR passes remote CI")
            if "Remote-CI" not in text and "remote CI" not in text:
                errors.append(f"{label} must bind completion to remote CI")
    return errors


def validate_source_static_boundary(root: Path) -> list[str]:
    errors: list[str] = []
    adapter_paths = sorted((root / "src/nac_m365_graph").glob("business_case_type_*.py"))
    forbidden = {
        "graph.microsoft.com/beta": "Graph beta endpoint",
        "Sites.Read.All": "broad Sites.Read.All permission",
        "Sites.ReadWrite.All": "broad Sites.ReadWrite.All permission",
        "Sites.Manage.All": "broad Sites.Manage.All permission",
        "Files.Read.All": "broad Files.Read.All permission",
    }
    for path in adapter_paths:
        text = path.read_text(encoding="utf-8")
        for token, label in forbidden.items():
            if token in text:
                errors.append(f"{path.relative_to(root)} contains forbidden {label}")
    if adapter_paths and not any(
        "BusinessCaseTypeRegistryReadPort" in path.read_text(encoding="utf-8")
        or "RegistryFetchResult" in path.read_text(encoding="utf-8")
        for path in adapter_paths
    ):
        errors.append("nac_m365_graph BusinessCaseType modules do not expose the domain read-port/result boundary")
    registry_path = root / "src/nac_m365_graph/business_case_type_registry.py"
    if registry_path.exists():
        registry_text = registry_path.read_text(encoding="utf-8")
        for marker in (
            "class GraphBusinessCaseTypeRestClient",
            "class GraphGetClient(Protocol)",
            "class GraphBusinessCaseTypeRegistryReadAdapter",
            "class GraphBusinessCaseTypeRegistryReadScope",
            "redirects_allowed = False",
            "retains_error_body = False",
            "MAX_RESPONSE_BYTES = 1_048_576",
            "response.read(MAX_RESPONSE_BYTES + 1)",
            "self.client.get(path)",
        ):
            if marker not in registry_text:
                errors.append(f"runtime adapter safe-client marker missing: {marker}")
    cli_path = root / "src/nac_cli/cli.py"
    if cli_path.exists() and adapter_paths:
        cli_text = cli_path.read_text(encoding="utf-8")
        if "business-case-type-read-plan" not in cli_text:
            errors.append("central CLI is missing business-case-type-read-plan")
    return errors


def validate_adapter_behavior(registry_module: object | None = None, plan_module: object | None = None) -> list[str]:
    errors: list[str] = []
    if registry_module is None:
        from nac_m365_graph import business_case_type_registry as registry_module
    if plan_module is None:
        from nac_m365_graph import business_case_type_read_plan as plan_module

    adapter_type = getattr(registry_module, "GraphBusinessCaseTypeRegistryReadAdapter", None)
    scope_type = getattr(registry_module, "GraphBusinessCaseTypeRegistryReadScope", None)
    client_protocol = getattr(registry_module, "GraphGetClient", None)
    if not inspect.isclass(adapter_type) or not inspect.isclass(scope_type):
        return ["runtime adapter/scope class marker missing"]
    if not inspect.isclass(client_protocol) or "get" not in client_protocol.__dict__:
        errors.append("safe GET-client protocol marker missing")
        return errors

    type_id = "immobilienkaufvertrag"
    version = "a" * 64

    class FakeClient:
        base_url = "https://graph.microsoft.com/v1.0"
        redirects_allowed = False
        retains_error_body = False

        def __init__(self, responses: list[object]):
            self.responses = list(responses)
            self.calls: list[str] = []

        def get(self, path: str) -> dict[str, object]:
            self.calls.append(path)
            response = self.responses.pop(0)
            if isinstance(response, BaseException):
                raise response
            if not isinstance(response, dict):
                raise TypeError("invalid fake response")
            return response

    def scope(**changes: object) -> object:
        values: dict[str, object] = {
            "site_id": "site-validator", "list_id": "list-validator",
            "operation": "case_create_validation", "role": "runtime_service",
            "runtime_permission": "Sites.Selected", "site_grant_role": "read",
        }
        values.update(changes)
        return scope_type(**values)

    def row() -> dict[str, object]:
        return {
            "id": "item-redacted", "eTag": '"etag-1"',
            "fields": {
                "BusinessCaseTypeId": type_id, "LifecycleStatus": "active",
                "Selectable": True, "CatalogVersion": version, "ViewerUrl": "ignored",
            },
        }

    def fetch(client: object, read_scope: object | None = None, **changes: object) -> object:
        values: dict[str, object] = {
            "site_id": "site-validator", "business_case_type_id": type_id,
            "catalog_version": version, "if_none_match": None,
        }
        values.update(changes)
        return adapter_type(client, read_scope or scope()).fetch_registry(**values)

    # Exact GET, bound collection, projection, and both immutable filters.
    initial_client = FakeClient([{"value": [row()]}])
    initial = fetch(initial_client)
    expected_filter = f"fields/BusinessCaseTypeId eq '{type_id}' and fields/CatalogVersion eq '{version}'"
    if getattr(initial, "status", None) != "OK" or len(initial_client.calls) != 1:
        errors.append("runtime exact GET request fake failed")
    else:
        parsed = urllib.parse.urlsplit(initial_client.calls[0])
        query = urllib.parse.parse_qs(parsed.query)
        if parsed.path != "/sites/site-validator/lists/list-validator/items":
            errors.append("runtime bound collection path mismatch")
        if query.get("$select") != ["id,eTag"] or query.get("$expand") != ["fields($select=BusinessCaseTypeId,LifecycleStatus,Selectable,CatalogVersion)"] or query.get("$filter") != [expected_filter]:
            errors.append("runtime exact projection/filter mismatch")
        if parsed.scheme or parsed.netloc or "If-None-Match" in initial_client.calls[0]:
            errors.append("runtime request is not safe relative GET without collection If-None-Match")

    # Scope, permission, grant, and binding failures must not reach transport.
    invalid_scopes = [
        scope(operation="schema_apply"), scope(role="Viewer"),
        scope(runtime_permission="Sites.Read.All"), scope(site_grant_role="write"),
    ]
    for invalid_scope in invalid_scopes:
        client = FakeClient([])
        result = fetch(client, invalid_scope)
        if getattr(result, "status", None) != "UNAVAILABLE" or client.calls:
            errors.append("runtime pretransport scope/permission/grant block failed")
            break
    mismatch_client = FakeClient([])
    mismatch = fetch(mismatch_client, site_id="site-other")
    if getattr(mismatch, "status", None) != "UNAVAILABLE" or mismatch_client.calls:
        errors.append("runtime pretransport bound-site block failed")

    def next_link(filter_value: str = expected_filter, skiptoken: str = "page-2") -> str:
        query = urllib.parse.urlencode({
            "$select": "id,eTag",
            "$expand": "fields($select=BusinessCaseTypeId,LifecycleStatus,Selectable,CatalogVersion)",
            "$filter": filter_value,
            "$skiptoken": skiptoken,
        }, quote_via=urllib.parse.quote)
        return f"https://graph.microsoft.com/v1.0/sites/site-validator/lists/list-validator/items?{query}"

    drift_client = FakeClient([{"value": [row()], "@odata.nextLink": next_link("fields/BusinessCaseTypeId eq 'other'")}])
    drift = fetch(drift_client)
    if getattr(drift, "status", None) != "UNAVAILABLE" or getattr(drift, "rows", None) != () or len(drift_client.calls) != 1:
        errors.append("runtime NextLink same-filter drift block failed")

    repeated = next_link()
    loop_client = FakeClient([{"value": [], "@odata.nextLink": repeated}, {"value": [], "@odata.nextLink": repeated}])
    loop = fetch(loop_client)
    if getattr(loop, "status", None) != "UNAVAILABLE" or getattr(loop, "rows", None) != () or len(loop_client.calls) != 2:
        errors.append("runtime canonical NextLink loop block failed")

    etag_client = FakeClient([{"value": [], "@odata.nextLink": next_link()}, {"value": [row()]}])
    unchanged = fetch(etag_client, if_none_match='"etag-1"')
    if getattr(unchanged, "status", None) != "NOT_MODIFIED" or len(etag_client.calls) != 2 or any("If-None-Match" in call for call in etag_client.calls):
        errors.append("runtime complete-read local ETag NOT_MODIFIED semantics failed")

    graph_error = getattr(registry_module, "GraphBusinessCaseTypeHttpError", None)
    if graph_error is None:
        errors.append("safe redacted HTTP-error class marker missing")
        return errors
    error_result = fetch(FakeClient([graph_error(403)]))
    if getattr(error_result, "reason_code", None) != "transport_authorization_failed" or "sensitive" in repr(error_result):
        errors.append("runtime fixed redacted transport error mapping failed")

    build_plan = getattr(plan_module, "build_business_case_type_read_plan", None)
    if not callable(build_plan):
        errors.append("offline CLI plan builder marker missing")
    else:
        expected_keys = {"status", "method", "graph_version", "logical_resource_binding", "selected_field_names", "page_limit", "item_limit", "response_byte_limit", "gate_results", "contract_version"}
        expected_gates = {"contract_valid", "operation_allowed", "role_allowed_for_operation", "runtime_permission_allowed", "site_grant_role_allowed", "offline_only"}
        plan = build_plan(ROOT)
        if set(plan) != expected_keys or set(plan.get("gate_results", {})) != expected_gates:
            errors.append("offline CLI exact output/gate matrix mismatch")
        if plan.get("status") != "PASSED" or plan.get("method") != "GET" or plan.get("graph_version") != "v1.0" or plan.get("selected_field_names") != EXPECTED_SELECTED_PROPERTIES:
            errors.append("offline CLI exact safe-plan values mismatch")
        blocked_matrix = [
            {"operation": "schema_apply"}, {"role": "Viewer"},
            {"runtime_permission": "Sites.Read.All"}, {"site_grant_role": "write"},
        ]
        if any(build_plan(ROOT, **case).get("status") != "BLOCKED" for case in blocked_matrix):
            errors.append("offline CLI permission/role/grant block matrix mismatch")
    return errors


def validate_repository(root: Path = ROOT) -> list[str]:
    load = lambda path: json.loads((root / path).read_text(encoding="utf-8"))
    errors = validate_domain_contract(load("workflows/contracts/business-case-type-graph-read-edge.contract.json"))
    errors.extend(validate_verification_contract(load("workflows/verification-contracts/business-case-type-graph-read-edge.verification.json")))
    errors.extend(validate_agent_context(load("agent-context/index.json")))
    errors.extend(validate_decisions_and_invariants(load("agent-context/decision-index.json"), load("agent-context/invariant-index.json")))
    documents = {
        "DE spec": "docs/de/superpowers/specs/2026-07-11-business-case-type-graph-read-edge-s4-design.md",
        "EN spec": "docs/en/superpowers/specs/2026-07-11-business-case-type-graph-read-edge-s4-design.md",
        "DE plan": "docs/de/superpowers/plans/2026-07-11-business-case-type-graph-read-edge-s4.md",
        "EN plan": "docs/en/superpowers/plans/2026-07-11-business-case-type-graph-read-edge-s4.md",
    }
    errors.extend(validate_document_traceability({label: (root / path).read_text(encoding="utf-8") for label, path in documents.items()}))
    errors.extend(validate_source_static_boundary(root))
    if root.resolve() == ROOT.resolve():
        errors.extend(validate_adapter_behavior())
    return errors


def main() -> int:
    errors = validate_repository()
    print(json.dumps({"status": "PASSED" if not errors else "FAILED", "errors": errors}, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
