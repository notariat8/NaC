#!/usr/bin/env python3
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
src_path = str(SRC)
if src_path in sys.path:
    sys.path.remove(src_path)
sys.path.insert(0, src_path)

from nac_runtime.immutable_evidence import (  # noqa: E402
    ETAG_KEYS,
    LIVE_STATUS,
    MINIMUM_RETENTION_YEARS,
    MUTATION_ACTIONS,
    PHASES,
    ReconciliationStorePort,
    REGISTERED_BUSINESS_CASE_TYPE_IDS,
    REGISTERED_CATALOG_VERSIONS,
    REGISTERED_ROLE_IDS,
    REGISTERED_TOOL_IDS,
    S6_STATUS,
    SignatureAnchorPort,
    WormJournalPort,
    _delivery_key,
)
from notary_kg.business_case_type_immutable_evidence import (  # noqa: E402
    build_synthetic_evidence_dry_run,
)
from notary_kg.business_case_type_runtime import BusinessCaseTypeCatalog  # noqa: E402


DOMAIN = ROOT / "workflows/contracts/business-case-type-immutable-evidence-s6.contract.json"
VERIFICATION = ROOT / "workflows/verification-contracts/business-case-type-immutable-evidence-s6.verification.json"
EXPECTED_ACCEPTANCE = [f"AC-S6-{index:02d}" for index in range(1, 9)]
CATALOG = BusinessCaseTypeCatalog.from_repo(ROOT)
EXPECTED_BUSINESS_CASE_TYPE_IDS = sorted(
    entry.business_case_type_id for entry in CATALOG.entries
)
EXPECTED_CATALOG_VERSIONS = [CATALOG.catalog_version]
EXPECTED_ZERO_ACTIVITY_COUNTERS = [
    "network_calls",
    "provider_calls",
    "tenant_calls",
    "tenant_writes",
    "credential_reads",
    "live_mutations",
]
EXPECTED_RECONCILIATION_STORE_OPERATIONS = [
    "claim_publication",
    "advance_publication",
    "complete_publication",
    "authorize_publication_retry",
    "require",
    "close",
    "is_required",
]
EXPECTED_PUBLICATION_STAGES = [
    "outbox-snapshot",
    "broker-in-flight",
    "broker-complete",
    "anchor-in-flight",
    "anchor-readback-in-flight",
    "anchor-readback-complete",
    "worm-commit-in-flight",
    "worm-readback-in-flight",
    "worm-readback-complete",
]
EXPECTED_PORTS = [
    "postgresql_outbox",
    "broker_with_dlq",
    "detached_signature_and_daily_anchor",
    "worm_journal_with_retention_readback",
    "persistent_reconciliation_store",
]

EXPECTED_BASE_FIELDS = [
    "schema_version",
    "event_id",
    "idempotency_key_sha256",
    "delivery_key_sha256",
    "correlation_id",
    "phase",
    "sequence",
    "previous_event_sha256",
    "actor_ref",
    "actor_principal_ref",
    "tenant_binding_sha256",
    "principal_key_binding_sha256",
    "tool_id",
    "role_id",
    "action",
    "business_case_type_id",
    "catalog_version",
    "manifest_sha256",
    "occurred_at",
    "retention",
    "privacy",
    "etags",
]
EXPECTED_RECONCILIATION_CLOSED_FIELDS = [
    "result_code",
    "operator_ref",
    "operator_principal_ref",
    "operator_tenant_binding_sha256",
    "operator_principal_key_binding_sha256",
    "approver_ref",
    "approver_principal_ref",
    "approver_tenant_binding_sha256",
    "approver_principal_key_binding_sha256",
]


def main() -> int:
    errors: list[str] = []
    domain = _load(DOMAIN, errors)
    verification = _load(VERIFICATION, errors)
    if errors:
        return _finish(errors)

    _expect(domain.get("status") == S6_STATUS, "domain status drift", errors)
    _expect(domain.get("leading_issue", "").endswith("/687"), "leading issue drift", errors)
    slice_contract = domain.get("slice", {})
    _expect(slice_contract.get("offline_only") is True, "offline-only boundary missing", errors)
    _expect(slice_contract.get("live_status_exact") == LIVE_STATUS, "live gate drift", errors)
    for field in (
        "allowed_network_calls",
        "allowed_provider_calls",
        "allowed_tenant_calls",
        "allowed_tenant_writes",
        "allowed_credential_reads",
        "allowed_live_mutations",
    ):
        _expect(slice_contract.get(field) == 0, f"{field} must remain zero", errors)
    _expect(slice_contract.get("production_adapters_implemented") is False, "production adapter claim", errors)

    envelope = domain.get("evidence_envelope", {})
    _expect(envelope.get("phases_exact") == list(PHASES), "phase contract drift", errors)
    _expect(envelope.get("floats_allowed") is False, "float boundary drift", errors)
    _expect(
        "delivery_key_sha256" in envelope.get("base_fields_exact", []),
        "delivery key field missing",
        errors,
    )
    _expect(
        envelope.get("base_fields_exact") == EXPECTED_BASE_FIELDS
        and envelope.get("phase_specific_fields", {}).get("reconciliation_closed")
        == EXPECTED_RECONCILIATION_CLOSED_FIELDS,
        "persisted principal security-binding evidence fields drift",
        errors,
    )
    _expect(
        envelope.get("etag_storage_exact")
        == "hmac-sha256:k<positive_integer>:<64_lowercase_hex>",
        "ETag HMAC storage drift",
        errors,
    )
    _expect(
        envelope.get("etag_hmac_algorithm_exact") == "HMAC-SHA256"
        and envelope.get("etag_hmac_domain_separator_exact")
        == r"nac.etag-evidence.v1\u0000"
        and envelope.get("etag_hmac_minimum_key_bytes") == 32
        and envelope.get("etag_hmac_key_version_required") is True
        and envelope.get("etag_hmac_tenant_bound") is True
        and envelope.get("etag_hmac_tenant_binding_exact")
        == r"SHA-256(nac.tenant-binding.v1\u0000,tenant_id)",
        "ETag HMAC boundary drift",
        errors,
    )
    _expect(
        set(domain.get("mutation_boundary", {}).get("actions_exact", [])) == MUTATION_ACTIONS,
        "mutation action drift",
        errors,
    )
    retention = domain.get("retention_legal_hold_and_access", {})
    _expect(
        retention.get("minimum_retention_years") == MINIMUM_RETENTION_YEARS,
        "retention boundary drift",
        errors,
    )
    _expect(retention.get("event_read_role_exact") == "revision_audit", "read role drift", errors)

    acceptance = [item.get("id") for item in domain.get("acceptance_criteria", [])]
    _expect(acceptance == EXPECTED_ACCEPTANCE, "domain acceptance IDs drift", errors)
    _expect(verification.get("acceptance_ids") == EXPECTED_ACCEPTANCE, "verification acceptance IDs drift", errors)

    output = build_synthetic_evidence_dry_run()
    _expect(output.get("status") == S6_STATUS, "dry-run status drift", errors)
    _expect(output.get("live_status") == LIVE_STATUS, "dry-run live gate drift", errors)
    _expect(output.get("production_worm_claim") is False, "dry-run WORM claim", errors)
    _expect(output.get("required_production_ports") == EXPECTED_PORTS, "production ports drift", errors)
    for field in EXPECTED_ZERO_ACTIVITY_COUNTERS:
        _expect(output.get(field) == 0, f"dry-run {field} must remain zero", errors)
    _expect(output.get("normal_chain", {}).get("complete") is True, "normal chain incomplete", errors)
    _expect(
        output.get("reconciliation_chain", {}).get("complete") is True,
        "reconciliation chain incomplete",
        errors,
    )
    _expect(output.get("reconciliation_store_clear") is True, "reconciliation store not closed", errors)
    for name, expected_count in (
        ("normal_publication", 3),
        ("reconciliation_publication", 5),
    ):
        publication = output.get(name, {})
        _expect(
            publication.get("status") == "SYNTHETIC_PORT_ORCHESTRATION_COMPLETE",
            f"{name} status drift",
            errors,
        )
        _expect(
            publication.get("event_count") == expected_count,
            f"{name} event count drift",
            errors,
        )
        _expect(
            publication.get("broker_ack_count") == expected_count,
            f"{name} acknowledgement count drift",
            errors,
        )
        _expect(
            publication.get("worm_readback_verified") is True,
            f"{name} WORM readback missing",
            errors,
        )
        _expect(
            publication.get("production_durability_claim") is False,
            f"{name} production claim",
            errors,
        )
        chain_name = name.replace("_publication", "_chain")
        _expect(
            publication.get("chain_head_sha256")
            == output.get(chain_name, {}).get("head_sha256"),
            f"{name} chain-head completion binding drift",
            errors,
        )
        for field in (
            "chain_head_sha256",
            "anchor_ref_sha256",
            "signature_ref_sha256",
            "worm_receipt_ref_sha256",
            "worm_readback_ref_sha256",
        ):
            value = publication.get(field)
            _expect(
                type(value) is str
                and len(value) == 64
                and all(character in "0123456789abcdef" for character in value),
                f"{name} {field} is invalid",
                errors,
            )

    ports = domain.get("ports", {})
    orchestrator = ports.get("orchestrator", {})
    _expect(
        orchestrator.get("implementation") == "ImmutableEvidencePublisher",
        "port orchestrator drift",
        errors,
    )
    _expect(
        orchestrator.get("missing_or_invalid_receipt_sets_sticky_reconciliation")
        is True,
        "sticky receipt reconciliation missing",
        errors,
    )
    _expect(
        orchestrator.get("defensive_copy_per_port_call") is True,
        "defensive port-copy boundary missing",
        errors,
    )
    _expect(
        orchestrator.get("broker_ack_event_binding_required") is True,
        "broker acknowledgement binding missing",
        errors,
    )
    _expect(
        orchestrator.get("worm_readback_is_separate_operation") is True,
        "separate WORM readback missing",
        errors,
    )
    correlation = domain.get("correlation_and_binding", {})
    _expect(
        correlation.get("correlation_id_pattern")
        == "^correlation-v1-k[0-9]+-[0-9a-f]{64}$",
        "opaque correlation pattern drift",
        errors,
    )
    _expect(
        correlation.get("raw_correlation_source_allowed") is False,
        "raw correlation source boundary drift",
        errors,
    )
    _expect(
        correlation.get("delivery_binding_components_exact")
        == [
            "canonical_event_without_event_id_or_delivery_key_sha256"
        ]
        and correlation.get("delivery_key_is_event_specific") is True
        and correlation.get("delivery_key_reuse_across_events_allowed") is False
        and "delivery_payload.pop(\"event_id\", None)"
        in inspect.getsource(_delivery_key)
        and "delivery_payload.pop(\"delivery_key_sha256\", None)"
        in inspect.getsource(_delivery_key)
        and "canonical_json_bytes(delivery_payload)"
        in inspect.getsource(_delivery_key),
        "event-specific delivery binding drift",
        errors,
    )
    _expect(
        correlation.get("correlation_and_actor_tenant_binding_must_match") is True
        and correlation.get("cross_tenant_event_or_retry_allowed") is False
        and correlation.get("tenant_binding_algorithm_exact")
        == r"SHA-256(nac.tenant-binding.v1\u0000,tenant_id)"
        and correlation.get("tenant_binding_persisted_in_event") is True
        and all(
            field in correlation.get("immutable_across_chain_exact", [])
            and field in correlation.get("idempotency_binding_fields_exact", [])
            for field in (
                "tenant_binding_sha256",
                "principal_key_binding_sha256",
            )
        ),
        "tenant/principal-key correlation binding drift",
        errors,
    )
    _expect(
        REGISTERED_BUSINESS_CASE_TYPE_IDS
        == frozenset(EXPECTED_BUSINESS_CASE_TYPE_IDS),
        "runtime business-case type authority differs from S3 catalog",
        errors,
    )
    _expect(
        REGISTERED_CATALOG_VERSIONS
        == frozenset(EXPECTED_CATALOG_VERSIONS),
        "runtime catalog-version authority differs from S3 catalog",
        errors,
    )
    typed = domain.get("typed_identifiers", {})
    for field, pattern in (
        ("tool_id_pattern", r"^tool-[a-z0-9]+(?:-[a-z0-9]+)*$"),
        ("role_id_pattern", r"^role-[a-z0-9]+(?:-[a-z0-9]+)*$"),
        (
            "business_case_type_id_pattern",
            r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        ),
        ("catalog_version_pattern", r"^[0-9a-f]{64}$"),
    ):
        _expect(typed.get(field) == pattern, f"{field} drift", errors)
    for field, values in (
        ("registered_tool_ids_exact", REGISTERED_TOOL_IDS),
        ("registered_role_ids_exact", REGISTERED_ROLE_IDS),
        (
            "registered_business_case_type_ids_exact",
            EXPECTED_BUSINESS_CASE_TYPE_IDS,
        ),
        ("registered_catalog_versions_exact", EXPECTED_CATALOG_VERSIONS),
        ("etag_keys_exact", ETAG_KEYS),
    ):
        _expect(
            typed.get(field) == sorted(values),
            f"{field} registry drift",
            errors,
        )
    _expect(
        typed.get("free_form_or_resolvable_identifiers_allowed") is False,
        "free-form identifier boundary drift",
        errors,
    )
    _expect(
        typed.get("registry_source_exact") == "BusinessCaseTypeCatalog.from_repo"
        and typed.get("registry_must_exactly_match_s3_catalog") is True,
        "S3 catalog source boundary drift",
        errors,
    )
    actor = domain.get("actor_ref", {})
    _expect(
        actor.get("stable_principal_binding_algorithm_exact") == "HMAC-SHA256"
        and actor.get("stable_principal_binding_domain_separator_exact")
        == r"nac.principal-ref.v1\u0000"
        and actor.get("stable_principal_binding_format_pattern")
        == r"^principal-v1-[0-9a-f]{64}$"
        and actor.get("stable_principal_binding_minimum_key_bytes") == 32
        and actor.get("stable_principal_binding_is_tenant_bound") is True
        and actor.get("stable_principal_binding_is_key_version_independent") is True
        and actor.get("stable_principal_binding_persisted_in_event") is True
        and actor.get("dual_control_uses_stable_principal_binding") is True
        and actor.get("persisted_principal_fields_exact")
        == [
            "actor_principal_ref",
            "operator_principal_ref",
            "approver_principal_ref",
        ]
        and actor.get("closure_principal_refs_must_match_factory_actor_refs") is True
        and actor.get("principal_key_binding_algorithm_exact")
        == r"SHA-256(nac.principal-key-binding.v1\u0000,principal_key)"
        and actor.get("principal_key_binding_persisted_in_event") is True
        and actor.get("principal_key_binding_must_match_actor_operator_and_approver")
        is True
        and actor.get("different_principal_keys_fail_closed") is True
        and actor.get("closure_security_binding_fields_exact")
        == [
            "operator_tenant_binding_sha256",
            "operator_principal_key_binding_sha256",
            "approver_tenant_binding_sha256",
            "approver_principal_key_binding_sha256",
        ],
        "stable-principal boundary drift",
        errors,
    )
    reconciliation = domain.get("reconciliation", {})
    _expect(
        reconciliation.get("publication_failure_close_supported_in_s6a") is False,
        "S6a publication-failure closure boundary drift",
        errors,
    )
    _expect(
        reconciliation.get("publication_failure_retry_allowed_while_required") is False,
        "sticky publication retry boundary drift",
        errors,
    )
    _expect(
        reconciliation.get("publication_failure_retry_after_dual_control_authorization") is True
        and reconciliation.get("publication_retry_authorization_operator_and_approver_must_differ") is True
        and reconciliation.get("publication_retry_resumes_same_chain_head_and_progress") is True,
        "authorized publication retry boundary drift",
        errors,
    )
    _expect(
        reconciliation.get("uncertain_outcome_requires_reconciliation_before_readback") is True
        and reconciliation.get("direct_readback_after_uncertain_outcome_allowed") is False
        and reconciliation.get("failed_closure_requires_new_successful_readback_before_reconciled_closure") is True,
        "reconciliation recovery model drift",
        errors,
    )
    broker = ports.get("broker", {})
    _expect(
        broker.get("ack_ref_pattern") == r"^broker-ack-v1-[0-9a-f]{64}$",
        "broker reference pattern drift",
        errors,
    )
    _expect(
        broker.get("ack_refs_unique_per_publication") is True,
        "broker acknowledgement uniqueness drift",
        errors,
    )
    _expect(
        broker.get("ack_fields_exact")
        == [
            "ack_ref",
            "event_id",
            "event_sha256",
            "idempotency_key_sha256",
            "delivery_key_sha256",
        ]
        and broker.get("delivery_key_binding_required") is True,
        "broker delivery-key binding drift",
        errors,
    )
    anchor = ports.get("signature_anchor", {})
    _expect(
        anchor.get("independent_readback_must_exactly_match_receipt") is True
        and anchor.get("anchor_call_keyword_fields_exact")
        == ["idempotency_key_sha256"]
        and anchor.get("idempotency_key_required") is True
        and anchor.get("idempotency_key_operation_exact") == "signature-anchor"
        and anchor.get("idempotency_key_derivation_exact")
        == r"SHA-256(nac.immutable-evidence-publication-operation.v1\u0000,operation,chain_head_sha256)"
        and anchor.get("same_key_must_return_same_receipt_for_resume") is True,
        "anchor readback/idempotency boundary drift",
        errors,
    )
    worm = ports.get("worm_journal", {})
    _expect(
        worm.get("readback_retention_may_exceed_event_minimum") is True
        and worm.get("commit_call_keyword_fields_exact")
        == ["idempotency_key_sha256"]
        and worm.get("idempotency_key_required") is True
        and worm.get("idempotency_key_operation_exact") == "worm-commit"
        and worm.get("idempotency_key_derivation_exact")
        == r"SHA-256(nac.immutable-evidence-publication-operation.v1\u0000,operation,chain_head_sha256)"
        and worm.get("same_key_must_return_same_receipt_for_resume") is True,
        "WORM retention/idempotency boundary drift",
        errors,
    )
    reconciliation_port = ports.get("reconciliation_store", {})
    runtime_port_operations = [
        name
        for name in EXPECTED_RECONCILIATION_STORE_OPERATIONS
        if name in ReconciliationStorePort.__dict__
    ]
    _expect(
        runtime_port_operations == EXPECTED_RECONCILIATION_STORE_OPERATIONS,
        "runtime reconciliation-store interface drift",
        errors,
    )
    claim_signature = inspect.signature(ReconciliationStorePort.claim_publication)
    _expect(
        list(claim_signature.parameters)
        == [
            "self",
            "correlation_id",
            "chain_head_sha256",
            "claim_id",
            "tenant_binding_sha256",
            "principal_key_binding_sha256",
            "event_sha256s",
        ]
        and all(
            claim_signature.parameters[field].kind
            is inspect.Parameter.KEYWORD_ONLY
            for field in (
                "claim_id",
                "tenant_binding_sha256",
                "principal_key_binding_sha256",
                "event_sha256s",
            )
        )
        and claim_signature.parameters["event_sha256s"].default
        is inspect.Parameter.empty,
        "runtime claim-publication signature drift",
        errors,
    )
    require_signature = inspect.signature(ReconciliationStorePort.require)
    _expect(
        list(require_signature.parameters)
        == [
            "self",
            "correlation_id",
            "reason_code",
            "chain_head_sha256",
            "claim_id",
            "publication_progress",
            "tenant_binding_sha256",
            "principal_key_binding_sha256",
            "event_sha256s",
        ]
        and all(
            require_signature.parameters[field].kind
            is inspect.Parameter.KEYWORD_ONLY
            and require_signature.parameters[field].default is None
            for field in (
                "claim_id",
                "publication_progress",
                "tenant_binding_sha256",
                "principal_key_binding_sha256",
                "event_sha256s",
            )
        ),
        "runtime reconciliation-require signature drift",
        errors,
    )
    anchor_signature = inspect.signature(SignatureAnchorPort.anchor)
    _expect(
        list(anchor_signature.parameters)
        == ["self", "records", "idempotency_key_sha256"]
        and anchor_signature.parameters["idempotency_key_sha256"].kind
        is inspect.Parameter.KEYWORD_ONLY,
        "runtime signature-anchor signature drift",
        errors,
    )
    worm_signature = inspect.signature(WormJournalPort.commit)
    _expect(
        list(worm_signature.parameters)
        == ["self", "records", "anchor", "idempotency_key_sha256"]
        and worm_signature.parameters["idempotency_key_sha256"].kind
        is inspect.Parameter.KEYWORD_ONLY,
        "runtime WORM-commit signature drift",
        errors,
    )
    _expect(
        reconciliation_port.get("publication_progress_fields_exact")
        == [
            "stage",
            "acknowledged_event_sha256s",
            "anchor_ref_sha256",
            "signature_ref_sha256",
            "worm_receipt_ref_sha256",
        ],
        "publication progress fields drift",
        errors,
    )
    _expect(
        reconciliation_port.get("publication_stages_exact")
        == EXPECTED_PUBLICATION_STAGES,
        "write-ahead publication stage drift",
        errors,
    )
    _expect(
        reconciliation_port.get("interface_operations_exact")
        == EXPECTED_RECONCILIATION_STORE_OPERATIONS,
        "restart-safe publication interface drift",
        errors,
    )
    _expect(
        reconciliation_port.get("publication_claim_id_pattern")
        == r"^claim-v1-[0-9a-f]{64}$"
        and reconciliation_port.get("publication_claim_is_exclusive") is True
        and reconciliation_port.get("publication_claim_binds_chain_head") is True
        and reconciliation_port.get("publication_claim_returns_completed_result_for_idempotent_replay") is True,
        "exclusive publication claim drift",
        errors,
    )
    _expect(
        reconciliation_port.get("claim_publication_keyword_fields_exact")
        == [
            "claim_id",
            "tenant_binding_sha256",
            "principal_key_binding_sha256",
            "event_sha256s",
        ]
        and reconciliation_port.get("publication_claim_binds_tenant_binding") is True
        and reconciliation_port.get("publication_claim_binds_principal_key_binding")
        is True
        and reconciliation_port.get("publication_security_binding_mismatch_fails_closed")
        is True
        and reconciliation_port.get("completed_claim_fields_exact")
        == ["status", "result", "publication_progress"]
        and reconciliation_port.get("completed_claim_returns_validated_progress")
        is True
        and reconciliation_port.get("requirement_security_binding_fields_exact")
        == ["tenant_binding_sha256", "principal_key_binding_sha256"]
        and reconciliation_port.get(
            "retry_authorization_binds_correlation_operator_and_approver_to_same_tenant"
        )
        is True
        and reconciliation_port.get(
            "retry_authorization_binds_operator_and_approver_to_publication_principal_key"
        )
        is True,
        "publication security-binding/completed-claim drift",
        errors,
    )
    _expect(
        reconciliation_port.get("require_keyword_fields_exact")
        == [
            "claim_id",
            "publication_progress",
            "tenant_binding_sha256",
            "principal_key_binding_sha256",
            "event_sha256s",
        ]
        and reconciliation_port.get("require_security_binding_fields_are_optional")
        is True
        and reconciliation_port.get(
            "pre_claim_publication_requirement_reason_exact"
        )
        == "evidence-publication-incomplete"
        and reconciliation_port.get(
            "pre_claim_publication_requirement_fields_exact"
        )
        == [
            "reason_code",
            "chain_head_sha256",
            "publication_progress",
            "tenant_binding_sha256",
            "principal_key_binding_sha256",
            "event_sha256s",
            "retry_authorized",
            "retry_authorizations",
        ]
        and reconciliation_port.get(
            "pre_claim_publication_requirement_initial_retry_authorized"
        )
        is False
        and reconciliation_port.get(
            "pre_claim_publication_requirement_initial_retry_authorizations_exact"
        )
        == []
        and reconciliation_port.get(
            "pre_claim_retry_authorization_is_principal_key_bound"
        )
        is True
        and reconciliation_port.get(
            "pre_claim_retry_without_principal_key_binding_fails_closed"
        )
        is True
        and reconciliation_port.get(
            "pre_claim_authorization_persisted_before_claim"
        )
        is True
        and reconciliation_port.get(
            "claim_atomically_consumes_authorized_requirement"
        )
        is True
        and reconciliation_port.get(
            "claim_copies_retry_authorizations_into_publication_state"
        )
        is True
        and reconciliation_port.get("claim_removes_consumed_requirement")
        is True
        and reconciliation_port.get("claim_event_sha256s_required_and_nonempty")
        is True
        and reconciliation_port.get(
            "claim_event_sha256s_last_must_equal_chain_head"
        )
        is True
        and reconciliation_port.get(
            "pre_claim_requirement_binds_ordered_event_hash_prefix"
        )
        is True
        and reconciliation_port.get(
            "pre_claim_event_hash_prefix_may_be_empty_before_snapshot"
        )
        is True
        and reconciliation_port.get(
            "claim_must_exactly_extend_pre_claim_event_hash_prefix"
        )
        is True
        and reconciliation_port.get(
            "publication_state_persists_complete_ordered_event_hash_sequence"
        )
        is True
        and reconciliation_port.get(
            "existing_publication_reclaim_requires_exact_event_hash_sequence"
        )
        is True,
        "pre-claim authorization/atomic-consumption drift",
        errors,
    )
    _expect(
        reconciliation_port.get("publication_retry_requires_authorization") is True
        and reconciliation_port.get("publication_retry_authorization_requires_dual_control") is True
        and reconciliation_port.get("publication_retry_resumes_persisted_progress") is True
        and reconciliation_port.get("publication_retry_skips_acknowledged_broker_events") is True
        and reconciliation_port.get("publication_retry_preserves_anchor_signature_and_worm_bindings") is True
        and reconciliation_port.get("interrupted_publication_can_resume_after_dual_control_authorization") is True,
        "authorized resumable publication drift",
        errors,
    )
    for field in (
        "publication_claim_acquired_before_first_external_call",
        "publication_progress_persisted_before_each_external_call",
        "publication_completion_persisted_before_success_return",
        "completed_publication_replay_returns_persisted_result_without_external_calls",
        "interrupted_publication_blocks_blind_retry",
        "outbox_snapshot_failure_is_sticky_with_zero_chain_head",
    ):
        _expect(
            reconciliation_port.get(field) is True,
            f"{field} boundary drift",
            errors,
        )
    _expect(
        domain.get("offline_output", {}).get("zero_activity_counters_exact")
        == EXPECTED_ZERO_ACTIVITY_COUNTERS,
        "offline zero-activity counter contract drift",
        errors,
    )
    _expect(
        orchestrator.get("snapshot_before_chain_verification") is True,
        "outbox snapshot-before-verification boundary missing",
        errors,
    )
    _expect(
        orchestrator.get("anchor_readback_is_separate_operation") is True,
        "separate anchor readback missing",
        errors,
    )
    _expect(
        orchestrator.get("completion_result_fields_exact")
        == [
            "schema_version",
            "status",
            "correlation_id",
            "chain_head_sha256",
            "event_count",
            "broker_ack_count",
            "anchor_ref_sha256",
            "signature_ref_sha256",
            "worm_receipt_ref_sha256",
            "worm_readback_ref_sha256",
            "worm_readback_verified",
            "production_durability_claim",
        ]
        and orchestrator.get("completion_result_binds_chain_head") is True
        and orchestrator.get("completion_result_binds_signature_reference_hash") is True
        and orchestrator.get("completed_result_event_count_equals_current_chain_length")
        is True
        and orchestrator.get("completed_result_broker_ack_count_equals_progress_length")
        is True
        and orchestrator.get("completed_result_progress_head_equals_chain_head") is True
        and orchestrator.get("completed_claim_progress_must_be_worm_readback_complete")
        is True
        and orchestrator.get("authorized_resume_from_persisted_progress_required") is True
        and orchestrator.get("unauthorized_resume_allowed") is False
        and orchestrator.get("all_external_port_exceptions_are_redacted") is True
        and orchestrator.get("external_immutable_evidence_error_is_redacted") is True
        and orchestrator.get("provider_exception_detail_returned_or_persisted") is False
        and orchestrator.get("redacted_external_failure_messages_exact")
        == [
            "evidence publication state is unavailable",
            "evidence publication requires reconciliation",
        ],
        "publication completion/resume/redaction binding drift",
        errors,
    )

    verification_text = json.dumps(verification, sort_keys=True)
    _expect("business-case-type-evidence-dry-run" in verification_text, "central CLI check missing", errors)
    _expect("doctor --profile strict" in verification_text, "strict gate missing", errors)
    return _finish(errors)


def _load(path: Path, errors: list[str]) -> dict[str, object]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        errors.append(f"invalid JSON: {path.relative_to(ROOT)}")
        return {}
    if type(value) is not dict:
        errors.append(f"root must be an object: {path.relative_to(ROOT)}")
        return {}
    return value


def _expect(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def _finish(errors: list[str]) -> int:
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("business-case-type immutable evidence S6: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
