from __future__ import annotations

import ast
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = Path(
    "workflows/contracts/m365-bff-performance-acceptance.contract.json"
)
VERIFICATION = Path(
    "workflows/verification-contracts/"
    "m365-bff-performance-acceptance.verification.json"
)
IMPLEMENTATION = Path("src/nac_bff/azure_performance_acceptance.py")
MONITOR = Path("src/nac_bff/azure_performance_monitor.py")
LEASE = Path("src/nac_bff/azure_performance_lease.py")
CLI = Path("src/nac_cli/cli.py")
WORM_BASELINE = Path("deploy/runtime/azure/immutable-evidence/main.bicep")
COORDINATION = Path("deploy/runtime/azure/nac-bff-performance-coordination/main.bicep")
TESTS = Path("tests/test_nac_bff_azure_performance_acceptance.py")
MONITOR_TESTS = Path("tests/test_nac_bff_azure_performance_monitor.py")
LEASE_TESTS = Path("tests/test_nac_bff_azure_performance_lease.py")
DOC_DE = Path("docs/de/operations/m365-bff-performance-acceptance.md")
DOC_EN = Path("docs/en/operations/m365-bff-performance-acceptance.md")
ISSUE = "https://github.com/notariat8/NaC/issues/735"
ACCEPTANCE_IDS = [f"AC-735-{index:02d}" for index in range(1, 10)]

PHASES = [
    ("cold_epoch_baseline", 1, 0),
    ("cold_epoch_candidate", 1, 0),
    ("interval_10s", 90, 10),
    ("interval_60s", 120, 60),
    ("interval_300s", 288, 300),
]
METRICS = [
    "OnDemandFunctionExecutionUnits",
    "OnDemandFunctionExecutionCount",
    "AlwaysReadyFunctionExecutionUnits",
    "AlwaysReadyUnits",
    "AlwaysReadyFunctionExecutionCount",
]
OWNER_FIELDS = {
    "approved_commit_sha",
    "approved_tree_sha",
    "toolchain_attestations_sha256",
    "activation_evidence_sha256",
    "contract_sha256",
    "phase_plan_sha256",
    "measurement_policy_sha256",
    "monitor_binding_sha256",
    "lease_binding_sha256",
    "target_binding_sha256",
    "worm_baseline_source_sha256",
    "worm_baseline_parameters_sha256",
    "coordination_source_sha256",
    "coordination_parameters_sha256",
    "runtime_composition_sha256",
    "evidence_policy_sha256",
    "infrastructure_binding_sha256",
}
OWNER_STAGES = [
    "unlocked_worm_baseline_deployment",
    "performance_coordination_infrastructure_deployment",
    "runtime_execution",
    "redacted_evidence",
]
PACKAGE_ORDER = [
    "verify_immutable_owner_approval",
    "deploy_unlocked_worm_baseline",
    "read_back_worm_baseline",
    "deploy_performance_coordination_infrastructure",
    "read_back_coordination_infrastructure_and_rbac",
    "bootstrap_dedicated_coordination_blob",
    "acquire_dedicated_blob_lease",
    "execute_exactly_500_synthetic_gets",
    "finalize_azure_monitor_observation",
    "release_dedicated_blob_lease",
    "write_redacted_evidence",
]
ZERO_PR_ACTIONS = {
    "azure_resource_creations_or_changes": 0,
    "blob_or_lease_live_operations": 0,
    "synthetic_target_dispatches": 0,
    "irreversible_worm_policy_locks": 0,
}
LEASE_STATES = [
    "ACQUIRE_INTENT",
    "ACQUIRE_IN_FLIGHT",
    "HELD",
    "RELEASE_INTENT",
    "RELEASED",
]


def _json(path: Path) -> dict[str, Any]:
    value = json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def _mapping(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _exact_string_set(value: object, expected: set[str]) -> bool:
    return (
        isinstance(value, list)
        and len(value) == len(expected)
        and all(isinstance(item, str) for item in value)
        and set(value) == expected
    )


def _contains_strings(value: object, required: set[str]) -> bool:
    return (
        isinstance(value, list)
        and all(isinstance(item, str) for item in value)
        and required.issubset(set(value))
    )


def _read_required(paths: tuple[Path, ...], errors: list[str]) -> dict[Path, str]:
    texts: dict[Path, str] = {}
    for path in paths:
        try:
            texts[path] = (REPO_ROOT / path).read_text(encoding="utf-8")
        except OSError:
            errors.append(f"missing required artifact: {path}")
    return texts


def _require_fragments(
    path: Path,
    content: str,
    fragments: tuple[str, ...] | list[str],
    errors: list[str],
) -> None:
    for fragment in fragments:
        if fragment not in content:
            errors.append(f"{path} missing required fragment: {fragment}")


def _validate_contract(contract: dict[str, Any], errors: list[str]) -> None:
    if contract.get("schema_version") != "nac.m365-bff-performance-acceptance/v0.4":
        errors.append("domain contract schema version must be v0.4")
    if (
        contract.get("status")
        != "offline_bound_live_package_implemented_no_azure_or_load_execution"
    ):
        errors.append("domain contract status must distinguish implementation from execution")
    if contract.get("leading_issue") != ISSUE:
        errors.append("domain contract must bind Issue #735")
    if contract.get("acceptance_ids") != ACCEPTANCE_IDS:
        errors.append("domain contract must bind AC-735-01 through AC-735-09")
    if contract.get("contract_id") != "m365.bff_performance_acceptance":
        errors.append("domain contract ID must match the runtime contract ID")

    scope = _mapping(contract.get("scope"))
    if scope.get("measurement_mode_exact") != (
        "endpoint_scoped_conservative_measurement"
    ):
        errors.append("measurement mode must be endpoint scoped and conservative")
    if scope.get("synthetic_endpoint_measurement_read_only") is not True:
        errors.append("the synthetic endpoint measurement must remain read-only")
    for field in (
        "tenant_wide_sharepoint_baseline_claim_exact",
        "tenant_wide_sharepoint_request_allowance_claim_exact",
        "tenant_wide_sharepoint_resource_unit_allowance_claim_exact",
        "tenant_wide_monetary_baseline_claim_exact",
    ):
        if scope.get(field) != "NOT_CLAIMED":
            errors.append(f"scope {field} must be NOT_CLAIMED")
    for field in (
        "azure_monitor_adapter_implemented_offline",
        "dedicated_blob_lease_adapter_implemented_offline",
        "central_owner_gated_live_cli_implemented_offline",
        "bound_live_orchestration_implemented_offline",
    ):
        if scope.get(field) is not True:
            errors.append(f"scope {field} must be true")
    for field in (
        "azure_resource_creation_or_change_executed_in_this_pr",
        "live_blob_or_lease_access_executed_in_this_pr",
        "live_target_dispatch_executed_in_this_pr",
    ):
        if scope.get(field) is not False:
            errors.append(f"scope {field} must remain false")

    policy = _mapping(contract.get("measurement_policy"))
    if (
        policy.get("measurement_policy_id_exact")
        != "endpoint_scoped_conservative_measurement"
        or policy.get("target_dispatches_exact") != 500
        or policy.get("synthetic_gets_exact") != 500
        or policy.get("maximum_client_concurrency") != 1
        or policy.get("maximum_dispatches_per_minute_inclusive") != 6
        or policy.get("minimum_interval_between_target_dispatches_seconds") != 10
        or policy.get("automatic_retries_allowed") is not False
        or policy.get("catch_up_bursts_allowed") is not False
    ):
        errors.append("measurement policy must enforce 500 GETs, concurrency 1 and <=6/min")

    actual_phases: list[tuple[object, object, object]] = []
    phases = contract.get("phases")
    if isinstance(phases, list):
        for phase in phases:
            item = _mapping(phase)
            actual_phases.append(
                (
                    item.get("id"),
                    item.get("target_dispatch_allocation_exact"),
                    item.get("request_interval_seconds_exact"),
                )
            )
            if item.get("maximum_client_concurrency") != 1:
                errors.append(f"phase {item.get('id')} must use concurrency 1")
    if actual_phases != PHASES:
        errors.append("phase plan must be exactly 1,1,90@10s,120@60s,288@300s")

    order = _mapping(contract.get("phase_order"))
    if (
        order.get("sum_of_all_phase_dispatch_allocations_exact") != 500
        or order.get("phase_allocations_exact") != [1, 1, 90, 120, 288]
        or order.get("phase_intervals_seconds_exact") != [0, 0, 10, 60, 300]
    ):
        errors.append("phase order must bind the exact 500-request schedule")

    sharepoint = _mapping(contract.get("sharepoint_capacity_position"))
    if (
        sharepoint.get("tenant_wide_baseline_status_exact") != "NOT_CLAIMED"
        or sharepoint.get("tenant_tier_attestation_required") is not False
        or sharepoint.get("tenant_request_allowance_attestation_required")
        is not False
        or sharepoint.get("tenant_resource_unit_allowance_attestation_required")
        is not False
        or sharepoint.get("tenant_request_or_resource_unit_headroom_claim_allowed")
        is not False
    ):
        errors.append("tenant-wide SharePoint capacity must be explicitly NOT_CLAIMED")

    monitor = _mapping(contract.get("azure_monitor_policy"))
    if (
        monitor.get("adapter_implemented_offline") is not True
        or monitor.get("live_monitor_read_executed_in_this_pr") is not False
        or monitor.get("metric_names_exact") != METRICS
        or monitor.get("aggregation_exact") != "Total"
        or monitor.get("interval_exact") != "PT1M"
        or monitor.get("dimension_filter_exact") != "Instance eq '*'"
        or monitor.get("instance_series_aggregation_exact")
        != "sum_all_Total_points_across_all_unique_Instance_series"
        or monitor.get("window_duration_seconds_minimum_inclusive") != 60
        or monitor.get("window_duration_seconds_maximum_inclusive") != 86400
        or monitor.get("settlement_delay_seconds_minimum_inclusive") != 300
        or monitor.get("attribution_scope_exact")
        != (
            "app_wide_delta_is_conservative_and_not_attributable_solely_to_"
            "test_traffic"
        )
        or monitor.get("endpoint_attribution_claim_allowed") is not False
    ):
        errors.append("Azure Monitor metrics, windows, settlement or attribution drifted")

    budget = _mapping(contract.get("azure_execution_budget"))
    if (
        budget.get("static_projected_full_measurement_gb_seconds_exact") != 30_000
        or budget.get(
            "observed_app_wide_delta_plus_projected_remaining_cap_gb_seconds_inclusive"
        )
        != 120_000
        or budget.get("projected_remaining_formula_exact")
        != "30000 * remaining_target_dispatches / 500"
        or budget.get("observed_values_are_app_wide_deltas") is not True
        or budget.get("observed_values_are_endpoint_attribution") is not False
    ):
        errors.append("Azure execution budget must be 30000 projected and 120000 capped")

    lease = _mapping(contract.get("exclusive_lease"))
    if (
        lease.get("adapter_implemented_offline") is not True
        or lease.get("live_blob_or_lease_operation_executed_in_this_pr") is not False
        or lease.get("operations_exact")
        != ["acquire(-1)", "assert_held", "release"]
        or lease.get("state_machine_exact") != LEASE_STATES
        or lease.get("automatic_reacquire_allowed") is not False
        or lease.get("break_allowed") is not False
        or lease.get("delete_allowed") is not False
        or lease.get("successful_final_measurement_requires_state_exact")
        != "RELEASED"
    ):
        errors.append("exclusive lease operations, state machine or final gate drifted")

    package = _mapping(contract.get("bound_deployment_package"))
    worm = _mapping(package.get("worm_baseline"))
    coordination = _mapping(package.get("performance_coordination"))
    if (
        package.get("single_package_required") is not True
        or package.get(
            "partial_approval_or_intentional_stage_only_execution_allowed"
        )
        is not False
        or package.get("interrupted_or_partial_deployment_behavior")
        != "BLOCKED_pending_bound_readback_or_reconciliation"
        or package.get("execution_order_exact") != PACKAGE_ORDER
        or _mapping(package.get("pr_execution_counters_exact")) != ZERO_PR_ACTIONS
    ):
        errors.append("bound package order, atomicity or zero PR counters drifted")
    if (
        worm.get("deployment_source_path_exact") != WORM_BASELINE.as_posix()
        or worm.get("source_and_parameters_hash_bound") is not True
        or worm.get("unlocked_immutability_policy_required") is not True
        or worm.get("provider_readback_required_before_coordination_deployment")
        is not True
        or worm.get("irreversible_policy_lock_in_scope") is not False
        or worm.get("irreversible_policy_lock_executed_in_this_pr") is not False
    ):
        errors.append("WORM baseline must be bound, read back, unlocked and unexecuted")
    if (
        coordination.get("deployment_source_path_exact")
        != COORDINATION.as_posix()
        or coordination.get("source_and_parameters_hash_bound") is not True
        or coordination.get(
            "provider_readback_and_rbac_verification_required_before_blob_bootstrap"
        )
        is not True
        or coordination.get("dedicated_from_bff_and_worm_storage_required")
        is not True
    ):
        errors.append("coordination deployment source, readback or isolation drifted")

    owner = _mapping(contract.get("activation_and_owner_gate"))
    if (
        owner.get("owner_approval_action_exact")
        != "EXECUTE_M365_BFF_BOUND_INFRASTRUCTURE_AND_LIVE_ACCEPTANCE_PACKAGE"
        or owner.get("immutable_owner_approval_count_exact") != 1
        or owner.get("immutable_issue_comment_required") is not True
        or owner.get("partial_or_stage_specific_approval_allowed") is not False
        or owner.get("approved_stages_exact") != OWNER_STAGES
        or not _exact_string_set(
            owner.get("owner_approval_binding_fields_exact"), OWNER_FIELDS
        )
        or owner.get("all_binding_fields_must_match_current_pre_first_write_values")
        is not True
        or owner.get("approval_reuse_after_any_binding_drift_allowed") is not False
        or owner.get("invalid_or_mismatched_gate_behavior")
        != "BLOCKED_before_first_write"
    ):
        errors.append("one immutable owner gate must bind every package stage and hash")

    boundary = _mapping(contract.get("live_action_boundary"))
    if (
        boundary.get("central_live_command_exact")
        != "nac m365 teams-sharepoint bff-performance-acceptance"
        or boundary.get("central_live_cli_implemented_offline") is not True
        or boundary.get("owner_gate_verified_before_first_write") is not True
        or boundary.get("caller_supplied_binding_hashes_allowed") is not False
        or boundary.get("azure_resource_creation_or_change_executed_in_this_pr")
        is not False
        or boundary.get("live_blob_or_lease_operation_executed_in_this_pr")
        is not False
        or boundary.get("live_target_dispatch_executed_in_this_pr") is not False
        or boundary.get(
            "future_live_action_requires_the_same_current_immutable_owner_approval"
        )
        is not True
    ):
        errors.append("central live CLI must be implemented offline and unexecuted")

    evidence_policy = _mapping(contract.get("evidence_policy"))
    if (
        not _exact_string_set(
            evidence_policy.get("required_hash_bindings_exact"), OWNER_FIELDS
        )
        or evidence_policy.get("tenant_wide_sharepoint_baseline_claim_exact")
        != "NOT_CLAIMED"
        or evidence_policy.get("tenant_wide_monetary_baseline_claim_exact")
        != "NOT_CLAIMED"
    ):
        errors.append("redacted evidence must carry every owner binding and NOT_CLAIMED")

    prohibited = _mapping(contract.get("prohibited_actions"))
    if (
        prohibited.get("irreversible_worm_policy_lock_allowed") is not False
        or prohibited.get("unbound_permission_or_credential_change_allowed")
        is not False
    ):
        errors.append("WORM lock and unbound permission changes must remain forbidden")

    pr_acceptance = _mapping(contract.get("pr_acceptance_condition"))
    if (
        pr_acceptance.get("offline_monitor_lease_and_central_live_cli_implemented")
        is not True
        or pr_acceptance.get("single_immutable_owner_package_bound") is not True
        or pr_acceptance.get(
            "tenant_wide_sharepoint_and_monetary_baselines_NOT_CLAIMED"
        )
        is not True
        or {
            "azure_resource_creations_or_changes": pr_acceptance.get(
                "azure_resource_creations_or_changes_exact"
            ),
            "blob_or_lease_live_operations": pr_acceptance.get(
                "blob_or_lease_live_operations_exact"
            ),
            "synthetic_target_dispatches": pr_acceptance.get(
                "synthetic_target_dispatches_exact"
            ),
            "irreversible_worm_policy_locks": pr_acceptance.get(
                "irreversible_worm_policy_locks_exact"
            ),
        }
        != ZERO_PR_ACTIONS
    ):
        errors.append("PR acceptance must bind offline implementation and zero live actions")

    passed = _mapping(contract.get("pass_condition"))
    if (
        passed.get("global_target_dispatch_count_exact") != 500
        or passed.get("lease_final_state_exact") != "RELEASED"
        or passed.get("tenant_wide_sharepoint_baseline_claim_exact")
        != "NOT_CLAIMED"
    ):
        errors.append("PASSED must require 500 dispatches, NOT_CLAIMED and RELEASED")


def _validate_verification(
    verification: dict[str, Any], errors: list[str]
) -> None:
    if verification.get("verification_id") != (
        "m365.bff_performance_acceptance.issue_735"
    ):
        errors.append("verification ID must bind Issue #735")
    if verification.get("leading_issue") != ISSUE:
        errors.append("verification contract must bind Issue #735")
    if verification.get("acceptance_ids") != ACCEPTANCE_IDS:
        errors.append("verification contract must bind AC-735-01 through AC-735-09")
    expected_test = (
        "PYTHONPATH=src python3 -m unittest "
        "tests.test_nac_bff_azure_performance_acceptance "
        "tests.test_nac_bff_azure_performance_monitor "
        "tests.test_nac_bff_azure_performance_lease"
    )
    checks = verification.get("checks")
    if not isinstance(checks, list) or expected_test not in checks:
        errors.append("verification contract must execute all focused test modules")

    required_context = verification.get("required_context")
    for path in (CLI, WORM_BASELINE, COORDINATION):
        if not isinstance(required_context, list) or path.as_posix() not in required_context:
            errors.append(f"verification context must include {path}")

    thresholds = _mapping(verification.get("thresholds"))
    if (
        thresholds.get("global_target_dispatches_exact") != 500
        or thresholds.get("phase_dispatch_allocations_exact")
        != [1, 1, 90, 120, 288]
        or thresholds.get("phase_request_intervals_seconds_exact")
        != [0, 0, 10, 60, 300]
        or thresholds.get("client_concurrency_exact") != 1
        or thresholds.get("dispatches_per_minute_maximum_inclusive") != 6
        or thresholds.get("static_projected_full_measurement_gb_seconds_exact")
        != 30_000
        or thresholds.get(
            "observed_app_wide_plus_projected_remaining_gb_seconds_maximum_inclusive"
        )
        != 120_000
        or thresholds.get("pr_azure_resource_creations_or_changes_exact") != 0
        or thresholds.get("pr_blob_or_lease_live_operations_exact") != 0
        or thresholds.get("pr_synthetic_target_dispatches_exact") != 0
        or thresholds.get("pr_irreversible_worm_policy_locks_exact") != 0
        or thresholds.get("immutable_owner_approvals_exact") != 1
    ):
        errors.append("verification thresholds do not match the conservative plan")

    evidence = verification.get("required_evidence")
    if (
        not _contains_strings(evidence, OWNER_FIELDS)
        or "tenant_wide_sharepoint_baseline_NOT_CLAIMED" not in evidence
        or "tenant_wide_monetary_baseline_NOT_CLAIMED" not in evidence
    ):
        errors.append("verification evidence must carry every exact owner binding")

    pass_condition = _mapping(verification.get("pass_condition"))
    for field in (
        "offline_monitor_lease_and_central_live_cli_implemented",
        "single_immutable_owner_package_bound",
        "unlocked_worm_baseline_and_coordination_deployments_bound",
        "pr_live_action_counts_all_zero",
        "irreversible_worm_policy_lock_absent",
    ):
        if pass_condition.get(field) is not True:
            errors.append(f"verification pass_condition.{field} must be true")
    for field in (
        "tenant_wide_sharepoint_baseline_claim_exact",
        "tenant_wide_monetary_baseline_claim_exact",
    ):
        if pass_condition.get(field) != "NOT_CLAIMED":
            errors.append(f"verification pass_condition.{field} must be NOT_CLAIMED")

    failure = _mapping(verification.get("failure_behavior"))
    if (
        failure.get("partial_owner_approval_or_partial_package")
        != "BLOCKED_before_first_write"
        or failure.get("irreversible_worm_policy_lock_requested")
        != "forbidden_outside_scope"
    ):
        errors.append("verification must fail closed on partial approval and WORM lock")


def main() -> int:
    errors: list[str] = []
    try:
        contract = _json(CONTRACT)
        verification = _json(VERIFICATION)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1

    paths = (
        IMPLEMENTATION,
        MONITOR,
        LEASE,
        CLI,
        WORM_BASELINE,
        COORDINATION,
        TESTS,
        MONITOR_TESTS,
        LEASE_TESTS,
        DOC_DE,
        DOC_EN,
    )
    texts = _read_required(paths, errors)
    _validate_contract(contract, errors)
    _validate_verification(verification, errors)

    required_fragments: dict[Path, tuple[str, ...]] = {
        IMPLEMENTATION: (
            'CONTRACT_ID = "m365.bff_performance_acceptance"',
            "PERFORMANCE_DURABLE_CHECKPOINT_FAILED",
            "PERFORMANCE_TARGET_BINDING_MISMATCH",
            "PERFORMANCE_EVIDENCE_REDACTION_INVALID",
            "reserved_attempt_count",
            "final_checkpoint_sha256",
            "_PerformancePreDispatchAbort",
            "INFLIGHT_DISPATCH_OUTCOME_UNKNOWN",
            "/workbench-snapshot?purpose=",
        ),
        MONITOR: (
            'API_VERSION = "2023-10-01"',
            'METRIC_NAMESPACE = "Microsoft.Web/sites"',
            'AGGREGATION = "Total"',
            'INTERVAL = "PT1M"',
            'DIMENSION_NAME = "Instance"',
            "INGESTION_LAG_SECONDS = 300",
            "MIN_WINDOW_SECONDS = 60",
            "MAX_WINDOW_SECONDS = 24 * 60 * 60",
            '"OnDemandFunctionExecutionUnits"',
            '"OnDemandFunctionExecutionCount"',
            '"AlwaysReadyFunctionExecutionUnits"',
            '"AlwaysReadyUnits"',
            '"AlwaysReadyFunctionExecutionCount"',
            "total += series_total",
            "instance_values.add(instance)",
            "PERFORMANCE_MONITOR_WINDOW_NOT_SETTLED",
            "app_wide_delta_is_conservative_and_not_attributable_solely_to_test_traffic",
        ),
        LEASE: (
            '"ACQUIRE_INTENT"',
            '"ACQUIRE_IN_FLIGHT"',
            '"HELD"',
            '"RELEASE_INTENT"',
            '"RELEASED"',
            '"x-ms-lease-action": "acquire"',
            '"x-ms-lease-duration": "-1"',
            '"x-ms-lease-action": "release"',
            "def acquire(",
            "def assert_held(",
            "def release(",
            "AZURE_BLOB_LEASE_REACQUIRE_FORBIDDEN",
        ),
        WORM_BASELINE: (
            "Offline create/update baseline only. Locking is a separate owner-gated S7 action.",
            "baselineImmutabilityPolicy",
            "lockActionStatus",
            "OWNER_GATED_NOT_EXECUTED",
        ),
        COORDINATION: (
            "Dedicated Azure Blob coordination boundary",
            "dedicated-from-bff-and-worm",
            "precreatedLeaseBlobETag",
            "blobCreationIncluded bool = false",
        ),
    }
    for path, fragments in required_fragments.items():
        _require_fragments(path, texts.get(path, ""), fragments, errors)

    try:
        cli_tree = ast.parse(texts.get(CLI, ""), filename=str(CLI))
    except SyntaxError as exc:
        errors.append(f"{CLI} is not valid Python: {exc}")
    else:
        cli_literals = {
            node.value
            for node in ast.walk(cli_tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
        }
        if "bff-performance-acceptance" not in cli_literals:
            errors.append(f"{CLI} must expose the exact central live command token")

    worm_text = texts.get(WORM_BASELINE, "")
    if (
        "immutabilityPolicies/lock/action" in worm_text
        or "lockActionStatus string = 'EXECUTED'" in worm_text
    ):
        errors.append(f"{WORM_BASELINE} must not implement an irreversible lock")

    focused = _mapping(verification.get("focused_test_names"))
    for key, path in (
        ("acceptance", TESTS),
        ("monitor", MONITOR_TESTS),
        ("lease", LEASE_TESTS),
    ):
        names = focused.get(key)
        if (
            not isinstance(names, list)
            or not names
            or not all(isinstance(name, str) for name in names)
        ):
            errors.append(f"verification focused_test_names.{key} must not be empty")
            continue
        _require_fragments(path, texts.get(path, ""), names, errors)

    doc_fragments = (
        "Issue #735",
        "endpoint_scoped_conservative_measurement",
        "NOT_CLAIMED",
        "500",
        "1, 1, 90, 120, 288",
        "10, 60, 300",
        "30,000 GB-s",
        "120,000 GB-s",
        "Instance",
        "ACQUIRE_INTENT",
        "ACQUIRE_IN_FLIGHT",
        "RELEASED",
        "nac m365 teams-sharepoint bff-performance-acceptance",
    )
    for path in (DOC_DE, DOC_EN):
        content = texts.get(path, "")
        _require_fragments(path, content, doc_fragments, errors)
        for stale in (
            "Issue #731",
            "Issue #733",
            "issues/731",
            "issues/733",
            "50,000",
            "50.000",
        ):
            if stale in content:
                errors.append(f"{path} retains a stale issue or 50000 claim: {stale}")

    localized_doc_fragments = {
        DOC_DE: (
            "unveränderliche Owner-Freigabe",
            "irreversibler WORM-Policy-Lock",
            "jeweils exakt `0`",
        ),
        DOC_EN: (
            "immutable owner approval",
            "irreversible WORM policy lock",
            "each exactly `0`",
        ),
    }
    for path, fragments in localized_doc_fragments.items():
        _require_fragments(path, texts.get(path, ""), fragments, errors)

    owned_text = "\n".join(
        (REPO_ROOT / path).read_text(encoding="utf-8")
        for path in (CONTRACT, VERIFICATION, DOC_DE, DOC_EN)
    )
    for stale in (
        "issues/731",
        "issues/733",
        "AC-731-",
        "AC-733-",
        "50000",
        "50,000",
        "50.000",
    ):
        if stale in owned_text:
            errors.append(f"owned contract/docs retain stale claim: {stale}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("M365 Azure BFF performance acceptance validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
