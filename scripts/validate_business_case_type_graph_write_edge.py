from __future__ import annotations

import importlib.util
import inspect
import json
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) in sys.path:
    sys.path.remove(str(SRC))
sys.path.insert(0, str(SRC))

DOMAIN_PATH = Path(
    "workflows/contracts/business-case-type-graph-write-edge-s4b.contract.json"
)
VERIFICATION_PATH = Path(
    "workflows/verification-contracts/"
    "business-case-type-graph-write-edge-s4b.verification.json"
)
ACCEPTANCE_IDS = [f"AC-S4B-{number:02d}" for number in range(1, 8)]
DOMAIN_KEYS = {
    "schema_version",
    "contract_id",
    "title",
    "status",
    "leading_issue",
    "slice",
    "operations",
    "field_schema",
    "binding",
    "plan_integrity",
    "identity_boundary",
    "authorization",
    "create_idempotency",
    "concurrency",
    "s5_binding",
    "evidence",
    "readback",
    "error_handling",
    "offline_boundary",
    "offline_cli",
    "acceptance_criteria",
}
VERIFICATION_KEYS = {
    "schema_version",
    "contract_id",
    "domain_contract_id",
    "title",
    "status",
    "leading_issue",
    "acceptance_ids",
    "applies_when",
    "required_context",
    "checks",
    "invariants",
    "thresholds",
    "required_evidence",
    "evidence_policy",
    "exit_conditions",
    "pass_condition",
    "failure_behavior",
}
REQUIRED_PATHS = {
    "src/notary_kg/business_case_type_mutation.py",
    "src/nac_m365_graph/business_case_type_write_edge.py",
    "src/nac_m365_graph/business_case_type_write_plan.py",
    "src/nac_m365_graph/business_case_type_write_dry_run.py",
    "src/nac_cli/cli.py",
    "scripts/quality_gate.py",
    "scripts/validate_business_case_type_graph_write_edge.py",
    "tests/test_business_case_type_graph_write_edge*.py",
    "tests/test_business_case_type_graph_write_edge_cli.py",
    "tests/fixtures/business-case-type-graph-write-edge/**",
    "workflows/contracts/business-case-type-graph-write-edge-s4b.contract.json",
    "workflows/verification-contracts/business-case-type-graph-write-edge-s4b.verification.json",
    "agent-context/index.json",
    "docs/de/cli.md",
    "docs/en/cli.md",
    "docs/de/architecture/business-case-type-id.md",
    "docs/en/architecture/business-case-type-id.md",
}
REQUIRED_CHECKS = {
    "python3 -m unittest tests.test_business_case_type_graph_write_edge tests.test_business_case_type_graph_write_edge_contract tests.test_business_case_type_graph_write_edge_cli tests.test_business_case_type_graph_write_edge_graph_contract tests.test_business_case_type_graph_write_edge_reconciliation tests.test_business_case_type_graph_write_edge_schema",
    "python3 scripts/validate_business_case_type_graph_write_edge.py",
    "python3 -m compileall -q src/notary_kg/business_case_type_mutation.py src/nac_m365_graph/business_case_type_write_plan.py src/nac_m365_graph/business_case_type_write_edge.py src/nac_m365_graph/business_case_type_write_dry_run.py scripts/validate_business_case_type_graph_write_edge.py tests/test_business_case_type_graph_write_edge.py tests/test_business_case_type_graph_write_edge_contract.py tests/test_business_case_type_graph_write_edge_cli.py tests/test_business_case_type_graph_write_edge_graph_contract.py tests/test_business_case_type_graph_write_edge_reconciliation.py tests/test_business_case_type_graph_write_edge_schema.py",
    "python3 scripts/nac.py contracts verify",
    "python3 scripts/validate_spec_traceability.py",
    "python3 scripts/validate_language_parity.py",
    "python3 scripts/validate_doc_links.py",
    "git diff --check",
}
EXPECTED_THRESHOLDS = {
    "required_acceptance_criteria": 7,
    "operations": 5,
    "create_operations": 2,
    "patch_operations": 3,
    "legacy_case_create_types": 4,
    "maximum_patch_attempts": 1,
    "dedupe_maximum_rows_accepted": 2,
    "retryable_http_statuses": 4,
    "maximum_dedupe_pages_followed": 0,
    "allowed_live_graph_calls": 0,
    "allowed_tenant_writes": 0,
    "allowed_credential_reads": 0,
    "allowed_live_factories": 0,
}
EXPECTED_OFFLINE_CLI = {
    "command_exact": "nac m365 teams-sharepoint business-case-type-write-dry-run",
    "operations_exact": [
        "case_create",
        "case_status_update",
        "task_create",
        "task_update",
        "business_case_type_backfill",
    ],
    "synthetic_only": True,
    "redacted_output_only": True,
    "resource_identifiers_or_urls_in_output_allowed": False,
    "field_values_in_output_allowed": False,
    "live_factory_allowed": False,
    "credentials_allowed": False,
    "live_graph_calls_allowed": 0,
    "tenant_writes_allowed": 0,
}

REQUIRED_RUNTIME_TEST_METHODS = {
    "test_all_five_operations_execute_with_canonical_revalidation",
    "test_execute_rejects_forged_plan_components_before_transport",
    "test_dedupe_next_link_is_ambiguous_without_write",
    "test_create_identity_with_divergent_fields_requires_reconciliation",
    "test_concurrent_create_conflict_deduplicates_after_exact_readback",
    "test_409_ambiguous_readback_requires_reconciliation_without_retry",
    "test_patch_uses_fresh_exact_etag_and_412_is_not_retried",
    "test_412_readback_distinguishes_actual_fields_and_invalid_shape",
    "test_preflight_transport_errors_are_structured_and_redacted",
    "test_negative_readback_distinguishes_actual_fields_and_invalid_shape",
    "test_unacknowledged_durable_intent_blocks_before_write",
    "test_uncertain_patch_uses_bound_item_readback_and_stays_sticky",
    "test_uncertain_write_marks_sticky_reconciliation_before_readback",
    "test_transport_exception_and_reconciliation_hook_failure_stay_sticky",
    "test_failed_marker_ack_blocks_restart_even_when_store_reports_clear",
    "test_lost_closure_confirmation_blocks_fresh_process_replay",
    "test_target_hash_binds_both_lists_for_every_operation",
    "test_patch_5xx_ignores_foreign_response_id_for_readback",
    "test_successful_create_orders_intent_write_outcome_and_readback",
}


REQUIRED_SAFETY_TEST_MODULES = {
    "tests/test_business_case_type_graph_write_edge.py": REQUIRED_RUNTIME_TEST_METHODS,
    "tests/test_business_case_type_graph_write_edge_reconciliation.py": {
        "test_execution_key_isolates_identical_mutation_across_targets",
        "test_retryable_statuses_allow_later_authorized_run",
        "test_unclear_retryable_response_remains_sticky_without_retry",
        "test_terminal_rejection_closes_and_blocks_replay",
        "test_412_remains_terminal_no_retry",
        "test_dedupe_requires_fresh_stable_item_readback",
    },
    "tests/test_business_case_type_graph_write_edge_schema.py": {
        "test_validator_shape_matches_provisioned_mutation_columns",
        "test_case_choices_match_provisioned_akten_schema",
        "test_status_choices_are_scoped_to_the_target_list",
        "test_datetime_requires_valid_iso_8601_value_with_timezone",
        "test_boolean_and_text_fields_reject_substitute_types",
        "test_dry_run_mutations_use_deployable_synthetic_values",
        "test_contract_gate_covers_complete_cli_safety_shape",
    },
    "tests/test_business_case_type_graph_write_edge_graph_contract.py": {
        "test_case_create_uses_only_documented_list_query_options",
        "test_task_create_uses_only_documented_list_query_options",
        "test_odata_literal_quotes_are_doubled_then_percent_encoded",
    },
}

EXPECTED_OPERATION_SHAPES = {
    "case_create": {
        "method": "POST",
        "list_name": "Akten",
        "path_template": "/sites/{site-id}/lists/{list-id}/items",
        "fields_required_exact": [
            "NacCaseId",
            "Aktenzeichen",
            "Vorgangstyp",
            "VorgangstypId",
            "Status",
            "NotarTeam",
            "Vertraulichkeitsstufe",
            "NacWorkflowVersion",
            "KgVersion",
        ],
        "fields_optional_exact": [],
        "dedupe_field_exact": "NacCaseId",
        "legacy_business_case_types_exact": [
            "handelsregisteranmeldung",
            "immobilienkaufvertrag",
            "online-gmbh-gruendung",
            "unterschriftsbeglaubigung",
        ],
    },
    "case_status_update": {
        "method": "PATCH",
        "list_name": "Akten",
        "path_template": "/sites/{site-id}/lists/{list-id}/items/{item-id}/fields",
        "fields_allowed_exact": ["Status"],
        "minimum_fields": 1,
    },
    "task_create": {
        "method": "POST",
        "list_name": "AufgabenFristen",
        "path_template": "/sites/{site-id}/lists/{list-id}/items",
        "fields_required_exact": [
            "NacTaskId",
            "NacCaseId",
            "BpmnStepCode",
            "Status",
            "RequiresNotaryApproval",
        ],
        "fields_optional_exact": ["DueDate"],
        "dedupe_field_exact": "NacTaskId",
    },
    "task_update": {
        "method": "PATCH",
        "list_name": "AufgabenFristen",
        "path_template": "/sites/{site-id}/lists/{list-id}/items/{item-id}/fields",
        "fields_allowed_exact": [
            "Status",
            "DueDate",
            "RequiresNotaryApproval",
            "BlockedReason",
        ],
        "minimum_fields": 1,
    },
    "business_case_type_backfill": {
        "method": "PATCH",
        "list_name": "Akten",
        "path_template": "/sites/{site-id}/lists/{list-id}/items/{item-id}/fields",
        "fields_allowed_exact": ["VorgangstypId"],
        "minimum_fields": 1,
    },
}

EXPECTED_DRY_RUN_SHAPES = {
    "case_create": {
        "method": "POST",
        "logical_list_name": "Akten",
        "field_names": list(EXPECTED_OPERATION_SHAPES["case_create"]["fields_required_exact"]),
        "request_phases": ["dedupe", "write", "readback"],
    },
    "case_status_update": {
        "method": "PATCH",
        "logical_list_name": "Akten",
        "field_names": ["Status"],
        "request_phases": ["freshness", "write", "readback"],
    },
    "task_create": {
        "method": "POST",
        "logical_list_name": "AufgabenFristen",
        "field_names": [
            *EXPECTED_OPERATION_SHAPES["task_create"]["fields_required_exact"],
            *EXPECTED_OPERATION_SHAPES["task_create"]["fields_optional_exact"],
        ],
        "request_phases": ["dedupe", "write", "readback"],
    },
    "task_update": {
        "method": "PATCH",
        "logical_list_name": "AufgabenFristen",
        "field_names": ["Status"],
        "request_phases": ["freshness", "write", "readback"],
    },
    "business_case_type_backfill": {
        "method": "PATCH",
        "logical_list_name": "Akten",
        "field_names": ["VorgangstypId"],
        "request_phases": ["freshness", "write", "readback"],
    },
}


def validate_domain_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if set(contract) != DOMAIN_KEYS:
        errors.append("domain contract top-level shape mismatch")
    expected_scalars = {
        "schema_version": "nac.business-case-type-graph-write-edge-s4b/v0.1",
        "contract_id": "m365.business_case_type_graph_write_edge_s4b",
        "status": "implemented_offline",
        "leading_issue": "https://github.com/notariat8/NaC/issues/694",
    }
    for name, expected in expected_scalars.items():
        if contract.get(name) != expected:
            errors.append(f"domain contract {name} mismatch")
    if contract.get("slice") != {
        "id": "S4b",
        "offline_only": True,
        "allowed_live_graph_calls": 0,
        "allowed_tenant_writes": 0,
        "live_factory_allowed": False,
        "credentials_allowed": False,
    }:
        errors.append("domain contract offline S4b slice mismatch")
    if contract.get("operations") != EXPECTED_OPERATION_SHAPES:
        errors.append("domain contract operation target or field allowlist mismatch")
    if contract.get("offline_cli") != EXPECTED_OFFLINE_CLI:
        errors.append("domain contract offline CLI boundary mismatch")

    binding = contract.get("binding", {})
    if binding != {
        "immutable_target_fields_exact": [
            "workspace_id",
            "site_id",
            "akten_list_id",
            "aufgaben_list_id",
            "write_identity_id",
            "bff_uami_identity_id",
        ],
        "target_binding_hash_scope_fields_required_exact": [
            "workspace_id",
            "site_id",
            "akten_list_id",
            "aufgaben_list_id",
        ],
        "target_binding_hash_includes_both_lists_for_all_operations": True,
        "inactive_list_drift_behavior": "block_before_transport",
        "runtime_fields_exact": [
            "workspace_id",
            "site_id",
            "list_id",
            "actor_role",
            "purpose",
            "approval_ref",
            "approved_operation",
            "write_approved",
            "write_identity_id",
            "write_identity_permission",
            "write_site_grant_role",
            "write_identity_site_id",
            "bff_uami_identity_id",
            "bff_uami_permission",
            "bff_uami_site_grant_role",
            "bff_uami_site_id",
        ],
        "mismatch_behavior": "block_before_transport",
        "graph_base_url_exact": "https://graph.microsoft.com/v1.0",
        "graph_beta_sdk_sharepoint_rest_pnp_allowed": False,
    }:
        errors.append("domain contract immutable Graph v1 binding mismatch")

    plan_integrity = contract.get("plan_integrity", {})
    if plan_integrity != {
        "canonical_revalidation_before_every_execute": True,
        "builder_issued_snapshot_required": True,
        "canonical_plan_sha256_required": True,
        "revalidated_components_exact": [
            "mutation_and_mutation_id",
            "s5_hash_binding",
            "authorization_and_approval",
            "target_binding_hash",
            "logical_list_name",
            "collection_url",
            "write_method",
            "write_url",
            "write_field_allowlist_and_payload",
            "dedupe_request",
            "freshness_request",
        ],
        "mutation_and_request_payloads_deeply_immutable": True,
        "mismatch_behavior": "block_before_transport",
    }:
        errors.append("domain contract execute-time plan integrity mismatch")

    identity = contract.get("identity_boundary", {})
    if identity != {
        "write_identity_contract_only": True,
        "write_permission_exact": "Sites.Selected",
        "write_site_grant_role_exact": "write",
        "bff_uami_permission_exact": "Sites.Selected",
        "bff_uami_site_grant_role_exact": "read",
        "write_and_bff_identity_must_differ": True,
        "write_identity_credentials_or_factory_in_scope": False,
        "bff_uami_permission_change_in_scope": False,
    }:
        errors.append("domain contract separate write/BFF identity boundary mismatch")

    field_schema = contract.get("field_schema", {})
    if field_schema != {
        "source_exact": "deploy/m365/teams-sharepoint/nac-mvp.teams-sharepoint.json",
        "text_fields_exact": [
            "NacCaseId", "Aktenzeichen", "NacWorkflowVersion", "KgVersion",
            "NacTaskId", "BpmnStepCode", "BlockedReason",
        ],
        "choice_fields_exact": {
            "Vorgangstyp": [
                "immobilienkaufvertrag", "unterschriftsbeglaubigung",
                "online-gmbh-gruendung", "handelsregisteranmeldung",
            ],
            "VorgangstypId": [
                "immobilienkaufvertrag", "unterschriftsbeglaubigung",
                "online-gmbh-gruendung", "handelsregisteranmeldung",
            ],
            "Akten.Status": [
                "Entwurf", "InPrüfung", "Beurkundung", "Vollzug",
                "Abgeschlossen", "Pausiert",
            ],
            "NotarTeam": ["NaC-Notar-01", "NaC-Notar-02"],
            "Vertraulichkeitsstufe": ["Normal", "Sensibel", "Hoch"],
            "AufgabenFristen.Status": [
                "Offen", "InArbeit", "Blockiert", "Erledigt",
            ],
        },
        "date_time_fields_exact": ["DueDate"],
        "boolean_fields_exact": ["RequiresNotaryApproval"],
        "boolean_as_text_or_integer_allowed": False,
        "date_time_format_exact": "ISO-8601 timezone-aware",
    }:
        errors.append("domain contract SharePoint field schema mismatch")

    authorization = contract.get("authorization", {})
    roles = authorization.get("operation_role_bindings", {})
    purposes = authorization.get("operation_purpose_bindings", {})
    if set(roles) != set(EXPECTED_OPERATION_SHAPES):
        errors.append("domain contract operation/role bindings mismatch")
    if purposes != {
        "case_create": "matter_workflow",
        "case_status_update": "matter_workflow",
        "task_create": "matter_workflow",
        "task_update": "matter_workflow",
        "business_case_type_backfill": "business_case_type_migration",
    }:
        errors.append("domain contract operation/purpose bindings mismatch")
    if (
        authorization.get("write_approval_required") is not True
        or authorization.get("approval_operation_must_equal_mutation")
        is not True
        or authorization.get("unknown_or_drifted_binding_behavior")
        != "block_before_transport"
    ):
        errors.append("domain contract approval fail-closed behavior mismatch")

    creates = contract.get("create_idempotency", {})
    if creates != {
        "dedupe_get_precedes_intent_and_post": True,
        "case_identity_field_exact": "NacCaseId",
        "task_identity_field_exact": "NacTaskId",
        "dedupe_projection_equals_create_field_allowlist": True,
        "one_match_requires_exact_create_payload": True,
        "zero_matches_behavior": "continue_to_intent_and_single_post",
        "one_match_behavior": "fresh_item_readback_then_deduplicated_without_post",
        "http_409_exact_readback_behavior": "deduplicated_without_post_retry",
        "multiple_matches_behavior": "sticky_reconciliation_without_post",
        "one_match_payload_drift_behavior": "sticky_reconciliation_without_post",
        "unique_sharepoint_columns_required": True,
        "maximum_followed_pages": 0,
        "odata_next_link_behavior": "sticky_reconciliation_without_post",
        "dedupe_response_shape_and_actual_fields_required": True,
        "dedupe_transport_failure_behavior": "structured_redacted_block_before_post",
        "dedupe_query_options_exact": ["expand", "$filter"],
        "dedupe_top_level_select_allowed": False,
        "dedupe_top_allowed": False,
        "dedupe_maximum_rows_accepted": 2,
        "dedupe_match_requires_fresh_item_readback_after_intent": True,
        "dedupe_fresh_readback_binds_item_id_etag_and_fields": True,
    }:
        errors.append("domain contract create deduplication mismatch")

    concurrency = contract.get("concurrency", {})
    if concurrency != {
        "patch_fresh_item_get_required": True,
        "fresh_item_get_projects_mutation_fields_only": True,
        "fresh_etag_must_equal_expected_etag": True,
        "if_match_header_source_exact": "fresh_item_get.eTag",
        "maximum_patch_attempts": 1,
        "retry_on_412": False,
        "http_412_result_codes_exact": [
            "PRECONDITION_FAILED",
            "PRECONDITION_FAILED_ALREADY_APPLIED",
        ],
        "readback_after_412_required": True,
        "freshness_response_shape_and_actual_fields_required": True,
        "freshness_transport_failure_behavior": "structured_redacted_block_before_patch",
        "http_412_readback_must_verify_status_shape_item_and_actual_fields": True,
        "http_412_invalid_readback_behavior": "sticky_reconciliation",
    }:
        errors.append("domain contract fresh ETag or no-412-retry mismatch")

    s5 = contract.get("s5_binding", {})
    if s5 != {
        "operation_exact": "business_case_type_backfill",
        "target_field_exact": "VorgangstypId",
        "manifest_hash_required": True,
        "record_ref_hash_required": True,
        "idempotency_components_exact": [
            "manifest_hash",
            "record_ref_hash",
            "target_business_case_type_id",
            "current_etag",
        ],
        "operation_hash_required": True,
        "operation_hash_payload_fields_exact": [
            "record_ref_hash",
            "field",
            "value",
            "if_match",
            "idempotency_key",
        ],
        "hash_algorithm_exact": "sha256_canonical_json",
    }:
        errors.append("domain contract S5 hash binding mismatch")

    evidence = contract.get("evidence", {})
    if evidence != {
        "hook_injected": True,
        "intent_before_write": True,
        "outcome_after_write_attempt": True,
        "readback_after_write_attempt": True,
        "normal_order_exact": ["intent", "outcome", "readback"],
        "uncertain_order_exact": [
            "intent",
            "outcome",
            "reconciliation_required",
            "readback",
        ],
        "uncertain_transport_or_5xx_requires_reconciliation": True,
        "successful_readback_auto_closes_reconciliation": False,
        "open_reconciliation_blocks_replay_before_transport": True,
        "evidence_contains_raw_site_list_item_or_field_values": False,
        "durable_acknowledgement_required_for_each_event": True,
        "authoritative_state_store_process_wide": True,
        "open_durable_intent_is_fail_closed_after_restart": True,
        "reconciliation_persistence_confirmation_required": True,
        "reconciliation_state_unavailable_blocks_before_transport": True,
        "local_only_reconciliation_marker_allowed": False,
        "persistent_state_fields_exact": [
            "reconciliation_state",
            "intent_state",
            "intent_generation",
            "closed_generation",
        ],
        "safe_start_intent_states_exact": ["absent", "retryable"],
        "closed_intent_is_terminal": True,
        "closed_intent_replay_behavior": "block_before_transport",
        "same_mutation_id_reopen_allowed": False,
        "post_close_confirmation_failure_behavior": (
            "return_persistence_failed_and_block_fresh_process_replay"
        ),
        "intent_open_requires_durable_readback_before_write": True,
        "reconciliation_clear_with_open_intent_behavior": "block_before_transport",
        "verified_readback_closure_is_atomic": True,
        "closure_proof_exact": "closed_generation_equals_intent_generation",
        "failed_reconciliation_ack_keeps_intent_open": True,
        "fresh_hook_shared_store_restart_must_block_open_intent": True,
        "reconciliation_clear_alone_sufficient": False,
        "execution_key_components_exact": ["target_binding_hash", "mutation_id"],
        "persistent_state_key_exact": "execution_key",
        "legacy_mutation_id_state_lookup_allowed": False,
        "retryable_intent_is_terminal": False,
        "retryable_intent_requires_new_authorized_run": True,
    }:
        errors.append("domain contract evidence order or sticky reconciliation mismatch")

    readback = contract.get("readback", {})
    if readback != {
        "http_status_exact": 200,
        "item_shape_required_fields_exact": ["id", "eTag", "fields"],
        "additional_odata_metadata_ignored": True,
        "item_id_binding_required": True,
        "nonempty_etag_required": True,
        "actual_field_names_equal_mutation_fields": True,
        "verified_not_applied_requires_valid_shape_and_actual_field_difference": True,
        "negative_or_412_invalid_readback_behavior": "sticky_reconciliation",
        "negative_applied_result_exact": "WRITE_REJECTED_STATE_ALREADY_APPLIED",
        "negative_not_applied_result_exact": "WRITE_REJECTED",
        "readback_transport_errors_exposed": False,
        "patch_5xx_item_id_source_exact": "plan.mutation.item_id",
        "post_5xx_response_item_id_allowed": True,
        "patch_5xx_response_item_id_allowed": False,
        "foreign_patch_5xx_response_item_id_in_evidence_allowed": False,
    }:
        errors.append("domain contract strict readback mismatch")

    error_handling = contract.get("error_handling", {})
    if error_handling != {
        "preflight_transport_reason_codes_exact": [
            "dedupe_transport_unavailable",
            "freshness_transport_unavailable",
        ],
        "exception_type_message_url_body_or_headers_exposed": False,
        "structured_result_required": True,
        "write_attempts_on_preflight_error": 0,
        "retryable_http_statuses_exact": [401, 403, 408, 429],
        "automatic_retry_within_execution_allowed": False,
        "later_authorized_retry_after_verified_not_applied": True,
        "authentication_refresh_required_for_401_403": True,
        "uncertain_retryable_readback_behavior": "sticky_reconciliation",
    }:
        errors.append("domain contract redacted transport errors mismatch")

    offline = contract.get("offline_boundary", {})
    if offline != {
        "transport_is_injected_protocol_only": True,
        "synthetic_fake_graph_only": True,
        "http_client_implementation_allowed": False,
        "credential_environment_token_or_certificate_reads_allowed": False,
        "dns_network_graph_sharepoint_entra_calls_allowed": False,
        "tenant_schema_permission_or_data_writes_allowed": False,
        "cli_changes_in_scope": True,
        "production_composition_in_scope": False,
    }:
        errors.append("domain contract offline no-factory boundary mismatch")

    criteria = contract.get("acceptance_criteria")
    if (
        not isinstance(criteria, list)
        or [item.get("id") for item in criteria if isinstance(item, dict)]
        != ACCEPTANCE_IDS
        or any(
            not isinstance(item.get("requirement"), str)
            or not item["requirement"]
            for item in criteria
            if isinstance(item, dict)
        )
    ):
        errors.append("domain contract AC-S4B-01..07 mismatch")
    return errors


def validate_verification_contract(
    verification: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    if set(verification) != VERIFICATION_KEYS:
        errors.append("verification contract top-level shape mismatch")
    expected_scalars = {
        "schema_version": "nac.verification-contract/v0.1",
        "contract_id": "verification.business_case_type_graph_write_edge_s4b",
        "domain_contract_id": "m365.business_case_type_graph_write_edge_s4b",
        "status": "implemented_offline",
        "leading_issue": "https://github.com/notariat8/NaC/issues/694",
    }
    for name, expected in expected_scalars.items():
        if verification.get(name) != expected:
            errors.append(f"verification contract {name} mismatch")
    if verification.get("acceptance_ids") != ACCEPTANCE_IDS:
        errors.append("verification acceptance IDs mismatch")
    paths = set(
        verification.get("applies_when", {}).get("paths", [])
        if isinstance(verification.get("applies_when"), dict)
        else []
    )
    if not REQUIRED_PATHS.issubset(paths):
        errors.append("verification applies_when paths incomplete")
    if not REQUIRED_CHECKS.issubset(set(verification.get("checks", []))):
        errors.append("verification checks incomplete")
    invariants = verification.get("invariants")
    if (
        not isinstance(invariants, list)
        or len(invariants) != 7
        or [item.split(":", 1)[0] for item in invariants] != ACCEPTANCE_IDS
    ):
        errors.append("verification ordered AC invariants mismatch")
    if verification.get("thresholds") != EXPECTED_THRESHOLDS:
        errors.append("verification thresholds mismatch")
    policy = verification.get("evidence_policy", {})
    if policy != {
        "synthetic_only": True,
        "redacted_only": True,
        "raw_site_list_item_or_field_values_allowed": False,
        "credentials_tokens_certificates_allowed": False,
        "live_graph_calls_allowed": 0,
        "tenant_writes_allowed": 0,
    }:
        errors.append("verification evidence policy mismatch")
    failure_behavior = verification.get("failure_behavior", {})
    required_failure_behavior = {
        "clear_with_open_intent": (
            "block_before_transport_until_persistent_closure_proof"
        ),
        "failed_reconciliation_ack": (
            "keep_durable_intent_open_across_hook_restart"
        ),
        "patch_5xx_foreign_response_item_id": (
            "ignore_and_read_exact_mutation_item"
        ),
        "inactive_list_binding_drift": "block_before_transport",
        "post_close_confirmation_unavailable": (
            "closed_intent_blocks_fresh_process_replay"
        ),
        "cross_workspace_execution_key_collision": (
            "impossible_by_target_binding_hash_plus_mutation_id"
        ),
        "dedupe_hit_without_fresh_stable_readback": (
            "sticky_reconciliation_without_post"
        ),
        "retryable_401_403_408_429": (
            "no_automatic_retry_and_later_authorized_retry_only_after_verified_not_applied"
        ),
        "invalid_sharepoint_field_value": "block_before_transport",
        "unsupported_dedupe_query_option": "block_contract_completion",
    }
    if any(
        failure_behavior.get(name) != expected
        for name, expected in required_failure_behavior.items()
    ):
        errors.append("verification persistent safety failure behavior mismatch")
    passed = verification.get("pass_condition", {})
    if (
        passed.get("allowed_live_graph_calls") != 0
        or passed.get("allowed_tenant_writes") != 0
        or passed.get("implementation_matches_contract") is not True
    ):
        errors.append("verification pass condition mismatch")
    return errors


def validate_implementation() -> list[str]:
    errors: list[str] = []
    try:
        from nac_m365_graph.business_case_type_write_edge import (
            BusinessCaseTypeGraphWriteEdge,
        )
        from nac_m365_graph.business_case_type_write_dry_run import (
            WRITE_DRY_RUN_OPERATIONS,
            build_business_case_type_write_dry_run,
        )
        from nac_m365_graph.business_case_type_write_plan import (
            BoundWriteTarget,
            BusinessCaseTypeWritePlanBuilder,
            MutationAuthorization,
            WritePlanBlocked,
        )
        from notary_kg.business_case_type_mutation import (
            BusinessCaseTypeMutation,
            MutationValidationError,
        )
    except Exception as exc:
        return [f"implementation import failed: {type(exc).__name__}"]

    if tuple(EXPECTED_OFFLINE_CLI["operations_exact"]) != tuple(
        WRITE_DRY_RUN_OPERATIONS
    ):
        errors.append("implementation offline CLI operation registry mismatch")
    for operation, expected_shape in EXPECTED_DRY_RUN_SHAPES.items():
        try:
            dry_run = build_business_case_type_write_dry_run(
                ROOT, operation=operation
            )
        except Exception as exc:
            errors.append(
                f"implementation offline CLI dry run failed for {operation}: "
                f"{type(exc).__name__}"
            )
            continue
        gates = dry_run.get("gate_results", {})
        actual_shape = {
            name: dry_run.get(name)
            for name in (
                "method",
                "logical_list_name",
                "field_names",
                "request_phases",
            )
        }
        if actual_shape != expected_shape:
            errors.append(
                f"implementation offline CLI shape mismatch for {operation}"
            )
        if (
            dry_run.get("status") != "PASSED"
            or dry_run.get("mode") != "offline_dry_run"
            or dry_run.get("operation") != operation
            or dry_run.get("graph_version") != "v1.0"
            or dry_run.get("preflight_method") != "GET"
            or dry_run.get("write_request_prepared") is not True
            or dry_run.get("write_request_executed") is not False
            or dry_run.get("contract_version")
            != "nac.business-case-type-graph-write-edge-s4b/v0.1"
            or len(str(dry_run.get("plan_sha256", ""))) != 64
            or len(str(dry_run.get("target_binding_sha256", ""))) != 64
            or gates
            != {
                "contract_valid": True,
                "operation_allowed": True,
                "synthetic_input_only": True,
                "graph_rest_v1_only": True,
                "separate_write_identity": True,
                "bff_read_identity_unchanged": True,
                "credentials_loaded": False,
                "live_factory_instantiated": False,
                "graph_calls": 0,
                "tenant_writes": 0,
            }
        ):
            errors.append(
                f"implementation offline CLI boundary failed for {operation}"
            )
        serialized = json.dumps(dry_run, sort_keys=True)
        forbidden_output_markers = (
            "https://graph.microsoft.com/",
            "synthetic-workspace-dry-run",
            "synthetic.example,dry-run,site",
            "synthetic-write-identity-dry-run",
            "synthetic-bff-read-identity-dry-run",
            "SYN-DRY-RUN",
            "synthetic-case-dry-run",
            "synthetic-task-dry-run",
            "synthetic-etag",
        )
        if any(marker in serialized for marker in forbidden_output_markers):
            errors.append(
                f"implementation offline CLI output is not redacted for {operation}"
            )

    target = BoundWriteTarget(
        workspace_id="synthetic-workspace-validator",
        site_id="synthetic.example,validator,site",
        akten_list_id="00000000-0000-4000-8000-000000000010",
        aufgaben_list_id="00000000-0000-4000-8000-000000000011",
        write_identity_id="synthetic-write-validator",
        bff_uami_identity_id="synthetic-bff-read-validator",
    )
    auth = MutationAuthorization(
        workspace_id=target.workspace_id,
        site_id=target.site_id,
        list_id=target.akten_list_id,
        actor_role="notary_clerk",
        purpose="matter_workflow",
        approval_ref="synthetic-approval-validator",
        approved_operation="case_create",
        write_approved=True,
        write_identity_id=target.write_identity_id,
        write_identity_permission="Sites.Selected",
        write_site_grant_role="write",
        write_identity_site_id=target.site_id,
        bff_uami_identity_id=target.bff_uami_identity_id,
        bff_uami_permission="Sites.Selected",
        bff_uami_site_grant_role="read",
        bff_uami_site_id=target.site_id,
    )
    fields = {
        "NacCaseId": "synthetic-case-validator",
        "Aktenzeichen": "SYN-VALIDATOR",
        "Vorgangstyp": "immobilienkaufvertrag",
        "VorgangstypId": "immobilienkaufvertrag",
        "Status": "Entwurf",
        "NotarTeam": "NaC-Notar-01",
        "Vertraulichkeitsstufe": "Normal",
        "NacWorkflowVersion": "workflow-v1",
        "KgVersion": "kg-v1",
    }
    try:
        mutation = BusinessCaseTypeMutation.case_create(fields)
        plan = BusinessCaseTypeWritePlanBuilder(target).build(mutation, auth)
        if (
            plan.write_method != "POST"
            or plan.logical_list_name != "Akten"
            or not plan.write_url.startswith(
                "https://graph.microsoft.com/v1.0/sites/"
            )
            or set(plan.write_payload.get("fields", {})) != set(fields)
        ):
            errors.append("implementation case_create plan mismatch")
    except Exception as exc:
        errors.append(f"implementation baseline failed: {type(exc).__name__}")

    try:
        BusinessCaseTypeMutation.case_create(
            {
                **fields,
                "Vorgangstyp": "bautraegervertrag",
                "VorgangstypId": "bautraegervertrag",
            }
        )
        errors.append("implementation accepts non-legacy case_create")
    except MutationValidationError:
        pass

    try:
        BusinessCaseTypeWritePlanBuilder(target).build(
            mutation, replace(auth, write_site_grant_role="read")
        )
        errors.append("implementation accepts write-grant drift")
    except WritePlanBlocked:
        pass

    for module_index, (relative_path, required_methods) in enumerate(
        REQUIRED_SAFETY_TEST_MODULES.items()
    ):
        try:
            runtime_path = ROOT / relative_path
            runtime_spec = importlib.util.spec_from_file_location(
                f"nac_s4b_safety_validator_tests_{module_index}", runtime_path
            )
            if runtime_spec is None or runtime_spec.loader is None:
                raise ImportError("runtime safety test module is unavailable")
            runtime_module = importlib.util.module_from_spec(runtime_spec)
            runtime_spec.loader.exec_module(runtime_module)
            runtime_cases = [
                candidate
                for _, candidate in inspect.getmembers(runtime_module, inspect.isclass)
                if issubclass(candidate, unittest.TestCase)
                and candidate.__module__ == runtime_module.__name__
            ]
            runtime_methods = {
                name
                for runtime_case in runtime_cases
                for name, _ in inspect.getmembers(runtime_case, inspect.isfunction)
                if name.startswith("test_")
            }
            if required_methods - runtime_methods:
                errors.append(f"implementation safety test matrix incomplete: {relative_path}")
            suite = unittest.defaultTestLoader.loadTestsFromModule(runtime_module)
            result = unittest.TestResult()
            suite.run(result)
            if (
                result.failures
                or result.errors
                or result.testsRun < len(required_methods)
            ):
                errors.append(f"implementation safety test matrix failed: {relative_path}")
        except Exception as exc:
            errors.append(
                f"implementation safety validation failed for {relative_path}: "
                f"{type(exc).__name__}"
            )

    constructor = inspect.signature(BusinessCaseTypeGraphWriteEdge)
    if list(constructor.parameters) != ["transport", "evidence_hook", "plan_builder"]:
        errors.append("write edge constructor must contain only injected ports")

    forbidden_markers = (
        "urllib.request",
        "requests.",
        "httpx.",
        "ClientSecretCredential",
        "ManagedIdentityCredential",
        "DefaultAzureCredential",
        "os.environ",
        "subprocess.",
    )
    for relative in (
        Path("src/notary_kg/business_case_type_mutation.py"),
        Path("src/nac_m365_graph/business_case_type_write_plan.py"),
        Path("src/nac_m365_graph/business_case_type_write_edge.py"),
        Path("src/nac_m365_graph/business_case_type_write_dry_run.py"),
    ):
        text = (ROOT / relative).read_text(encoding="utf-8")
        for marker in forbidden_markers:
            if marker in text:
                errors.append(f"{relative} contains forbidden live marker {marker}")
    return errors


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads((ROOT / path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def main() -> int:
    errors = [
        *validate_domain_contract(_load(DOMAIN_PATH)),
        *validate_verification_contract(_load(VERIFICATION_PATH)),
        *validate_implementation(),
    ]
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("BusinessCaseType Graph write edge S4b validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
