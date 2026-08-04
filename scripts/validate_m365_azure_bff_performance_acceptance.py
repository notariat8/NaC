from __future__ import annotations

import ast
import json
from pathlib import Path
import re
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
AUTHORIZATION = Path("src/nac_bff/azure_performance_authorization.py")
MONITOR = Path("src/nac_bff/azure_performance_monitor.py")
LEASE_BROKER = Path("src/nac_bff/azure_performance_lease_broker.py")
LEASE_BROKER_STORAGE = Path(
    "src/nac_bff/azure_performance_lease_broker_storage.py"
)
LEASE_BROKER_AUTH = Path("src/nac_bff/azure_performance_lease_broker_auth.py")
LEASE_BROKER_CLIENT = Path(
    "src/nac_bff/azure_performance_lease_broker_client.py"
)
LEASE_BROKER_COMPOSITION = Path(
    "src/nac_bff/azure_performance_lease_broker_composition.py"
)
BFF_COMPOSITION = Path("src/nac_bff/composition.py")
FASTAPI_ADAPTER = Path("src/nac_bff/fastapi_adapter.py")
RUNTIME = Path("src/nac_bff/azure_performance_runtime.py")
COMPOSITION = Path("src/nac_bff/azure_performance_composition.py")
OWNER_GATE = Path("src/nac_bff/azure_performance_owner_gate.py")
INFRA_SAFETY = Path("src/nac_bff/azure_performance_infrastructure_safety.py")
INFRASTRUCTURE_PORTS = Path(
    "src/nac_bff/azure_performance_infrastructure_ports.py"
)
AZURE_COMMANDS = Path("src/nac_bff/azure_live_commands.py")
CLI = Path("src/nac_cli/cli.py")
INFRA = Path("deploy/runtime/azure/nac-bff-performance-coordination/main.bicep")
INFRA_PARAMETERS = Path(
    "deploy/runtime/azure/nac-bff-performance-coordination/main.example.bicepparam"
)
INFRA_COMPILED = Path(
    "deploy/runtime/azure/nac-bff-performance-coordination/compiled/main.json"
)
INFRA_COMPILED_PARAMETERS = Path(
    "deploy/runtime/azure/nac-bff-performance-coordination/"
    "compiled/main.example.json"
)
WORM_INFRA = Path("deploy/runtime/azure/immutable-evidence/main.bicep")
WORM_INFRA_PARAMETERS = Path(
    "deploy/runtime/azure/immutable-evidence/main.bicepparam"
)
WORM_INFRA_COMPILED = Path(
    "deploy/runtime/azure/immutable-evidence/compiled/main.json"
)
WORM_INFRA_COMPILED_PARAMETERS = Path(
    "deploy/runtime/azure/immutable-evidence/compiled/main.parameters.json"
)
INFRA_ARM_VALIDATOR = Path("scripts/validate_nac_bff_performance_coordination_arm.py")
QUALITY_GATE_WORKFLOW = Path(".github/workflows/quality-gate.yml")
TESTS = Path("tests/test_nac_bff_azure_performance_acceptance.py")
AUTHORIZATION_TESTS = Path("tests/test_nac_bff_azure_performance_authorization.py")
MONITOR_TESTS = Path("tests/test_nac_bff_azure_performance_monitor.py")
LEASE_BROKER_TESTS = Path(
    "tests/test_nac_bff_azure_performance_lease_broker.py"
)
LEASE_BROKER_STORAGE_TESTS = Path(
    "tests/test_nac_bff_azure_performance_lease_broker_storage.py"
)
LEASE_BROKER_AUTH_TESTS = Path(
    "tests/test_nac_bff_azure_performance_lease_broker_auth.py"
)
LEASE_BROKER_CLIENT_TESTS = Path(
    "tests/test_nac_bff_azure_performance_lease_broker_client.py"
)
LEASE_BROKER_COMPOSITION_TESTS = Path(
    "tests/test_nac_bff_azure_performance_lease_broker_composition.py"
)
LEASE_BROKER_FASTAPI_TESTS = Path(
    "tests/test_nac_bff_performance_lease_broker_fastapi.py"
)
RUNTIME_TESTS = Path("tests/test_nac_bff_azure_performance_runtime.py")
COMPOSITION_TESTS = Path("tests/test_nac_bff_azure_performance_composition.py")
OWNER_GATE_TESTS = Path("tests/test_nac_bff_azure_performance_owner_gate.py")
INFRA_SAFETY_TESTS = Path(
    "tests/test_nac_bff_azure_performance_infrastructure_safety.py"
)
INFRASTRUCTURE_PORT_TESTS = Path(
    "tests/test_nac_bff_azure_performance_infrastructure_ports.py"
)
AZURE_COMMAND_TESTS = Path("tests/test_nac_bff_azure_live_commands.py")
INFRA_TESTS = Path("tests/test_nac_bff_performance_coordination_iac.py")
CLI_TESTS = Path("tests/test_nac_cli_bff_performance_acceptance.py")
CONTRACT_INDEX = Path("workflows/contracts/README.md")
DOC_DE = Path("docs/de/operations/m365-bff-performance-acceptance.md")
DOC_EN = Path("docs/en/operations/m365-bff-performance-acceptance.md")
PLAN_DE = Path(
    "docs/de/superpowers/plans/2026-08-03-bff-conservative-measurement-adapters.md"
)
SPEC_DE = Path(
    "docs/de/superpowers/specs/"
    "2026-08-03-bff-conservative-measurement-adapters-design.md"
)
PLAN_EN = Path(
    "docs/en/superpowers/plans/2026-08-03-bff-conservative-measurement-adapters.md"
)
SPEC_EN = Path(
    "docs/en/superpowers/specs/"
    "2026-08-03-bff-conservative-measurement-adapters-design.md"
)
ISSUE = "https://github.com/notariat8/NaC/issues/735"
ACCEPTANCE_IDS = [f"AC-735-{index:02d}" for index in range(1, 10)]

PHASES = [
    ("cold_epoch_baseline", 1, 1),
    ("cold_epoch_candidate", 1, 1),
    ("endpoint_scoped_sample", 90, 10),
    ("sustained_2h", 120, 60),
    ("soak_24h", 288, 300),
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
    "contract_sha256",
    "expected_activation_hash",
    "target_binding_sha256",
    "phase_plan_sha256",
    "measurement_policy_sha256",
    "monitor_policy_sha256",
    "lease_policy_sha256",
    "lease_broker_policy_sha256",
    "infrastructure_safety_policy_sha256",
    "infrastructure_source_sha256",
    "infrastructure_parameters_sha256",
    "infrastructure_binding_sha256",
    "worm_baseline_binding_sha256",
    "worm_baseline_compiled_arm_sha256",
    "worm_baseline_parameters_sha256",
    "worm_baseline_source_sha256",
    "deployment_sequence_sha256",
    "correlation_id",
    "monitor_window_anchor_utc",
    "monitor_window_anchor_sha256",
}
COMBINED_OWNER_FIELDS = {
    "approved_commit_sha",
    "approved_tree_sha",
    "toolchain_attestations_sha256",
    "contract_sha256",
    "phase_plan_sha256",
    "measurement_policy_sha256",
    "monitor_policy_sha256",
    "lease_policy_sha256",
    "lease_broker_policy_sha256",
    "infrastructure_safety_policy_sha256",
    "infrastructure_source_sha256",
    "infrastructure_parameters_sha256",
    "infrastructure_binding_sha256",
    "worm_baseline_binding_sha256",
    "worm_baseline_compiled_arm_sha256",
    "worm_baseline_parameters_sha256",
    "worm_baseline_source_sha256",
    "deployment_sequence_sha256",
    "target_binding_sha256",
    "expected_activation_hash",
    "correlation_id",
    "monitor_window_anchor_utc",
    "monitor_window_anchor_sha256",
}
EVIDENCE_BINDING_FIELDS = {
    "approved_commit_sha",
    "approved_tree_sha",
    "toolchain_attestations_sha256",
    "contract_sha256",
    "expected_activation_hash",
    "phase_plan_sha256",
    "measurement_policy_sha256",
    "monitor_policy_sha256",
    "lease_policy_sha256",
    "monitor_binding_sha256",
    "monitor_window_anchor_sha256",
    "lease_binding_sha256",
    "infrastructure_binding_sha256",
    "worm_baseline_binding_sha256",
    "worm_baseline_compiled_arm_sha256",
    "worm_baseline_parameters_sha256",
    "worm_baseline_source_sha256",
    "deployment_sequence_sha256",
    "infrastructure_parameters_sha256",
    "infrastructure_source_sha256",
    "lease_broker_policy_sha256",
    "infrastructure_safety_policy_sha256",
    "infrastructure_safety_evidence_sha256",
    "lease_acquisition_safety_evidence_sha256",
    "owner_approval_body_sha256",
    "target_binding_sha256",
}
INFRASTRUCTURE_PARAMETER_FIELDS = {
    "bffStorageAccountResourceId",
    "brokerCallerServicePrincipalId",
    "brokerFunctionAppResourceId",
    "brokerFunctionPackageSha256",
    "brokerOutboundIpAddresses",
    "brokerPrincipalId",
    "brokerTicketVerificationCertificateSha256",
    "deploymentMode",
    "location",
    "resourceGroupName",
    "storageAccountName",
    "subscriptionId",
    "tags",
    "targetBindingSha256",
    "tenantId",
    "wormStorageAccountResourceId",
}
VERIFICATION_EVIDENCE_BINDING_FIELDS = EVIDENCE_BINDING_FIELDS - {
    "lease_broker_policy_sha256"
}
WORM_BASELINE_PARAMETER_FIELDS = {
    "containerName",
    "deploymentMode",
    "encryptionScopeName",
    "location",
    "resourceGroupName",
    "storageAccountName",
    "subscriptionId",
    "tags",
    "tenantId",
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


def _string_constant(path: Path, name: str) -> str | None:
    try:
        tree = ast.parse((REPO_ROOT / path).read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError):
        return None
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if (
            isinstance(target, ast.Name)
            and target.id == name
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            return node.value.value
    return None


def _validate_not_claimed_renderers(errors: list[str]) -> None:
    try:
        tree = ast.parse(
            (REPO_ROOT / IMPLEMENTATION).read_text(encoding="utf-8")
        )
    except (OSError, SyntaxError, UnicodeError):
        errors.append("performance implementation must be valid Python")
        return
    expected = {
        "tenant_wide_sharepoint_baseline_claim": "NOT_CLAIMED",
        "tenant_wide_sharepoint_request_allowance_claim": "NOT_CLAIMED",
        "tenant_wide_sharepoint_resource_unit_allowance_claim": "NOT_CLAIMED",
        "monetary_cost_claim": "NOT_CLAIMED",
    }
    mapping: dict[str, str] | None = None
    functions: dict[str, ast.FunctionDef] = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            functions[node.name] = node
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not (
            isinstance(target, ast.Name)
            and target.id == "NOT_CLAIMED_ACCEPTANCE_FIELDS"
            and isinstance(node.value, ast.Dict)
        ):
            continue
        if len(node.value.keys) != len(expected) or any(
            key is None
            or not isinstance(key, ast.Constant)
            or not isinstance(key.value, str)
            or not isinstance(value, ast.Constant)
            or not isinstance(value.value, str)
            for key, value in zip(node.value.keys, node.value.values)
        ):
            mapping = None
            continue
        try:
            mapping = {
                key.value: value.value
                for key, value in zip(node.value.keys, node.value.values)
            }
        except (AttributeError, TypeError):
            mapping = None
    if mapping != expected:
        errors.append("canonical NOT_CLAIMED acceptance mapping drifted")
    assignment_names = {
        "build_performance_acceptance_plan": "payload",
        "build_owner_comment": "body",
    }
    for function_name, assignment_name in assignment_names.items():
        function = functions.get(function_name)
        assignments = [] if function is None else [
            node
            for node in function.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == assignment_name
        ]
        spreads = [
            value
            for assignment in assignments
            for node in ast.walk(assignment.value)
            if isinstance(node, ast.Dict)
            for key, value in zip(node.keys, node.values)
            if key is None
            and isinstance(value, ast.Name)
            and value.id == "NOT_CLAIMED_ACCEPTANCE_FIELDS"
        ]
        if len(spreads) != 1:
            errors.append(
                f"{function_name} must include the canonical NOT_CLAIMED mapping once"
            )

    try:
        runtime_tree = ast.parse((REPO_ROOT / RUNTIME).read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeError):
        errors.append("performance runtime must be valid Python")
        return
    final_dicts = []
    for node in ast.walk(runtime_tree):
        if not (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "final"
            and isinstance(node.value, ast.Dict)
        ):
            continue
        literals = {
            key.value: value.value
            for key, value in zip(node.value.keys, node.value.values)
            if isinstance(key, ast.Constant)
            and isinstance(key.value, str)
            and isinstance(value, ast.Constant)
            and isinstance(value.value, str)
        }
        if literals.get("schema_version") == (
            "nac.m365-bff-performance-final-evidence/v1"
        ):
            final_dicts.append(literals)
    if len(final_dicts) != 1 or any(
        final_dicts[0].get(field) != value for field, value in expected.items()
    ):
        errors.append("final JSON renderer must emit all NOT_CLAIMED fields")

    markdown_functions = [
        node
        for node in runtime_tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "_render_final_markdown"
    ]
    markdown_lines: set[str] = set()
    if len(markdown_functions) == 1:
        for node in markdown_functions[0].body:
            if not (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "lines"
                and isinstance(node.value, ast.List)
            ):
                continue
            markdown_lines = {
                item.value
                for item in node.value.elts
                if isinstance(item, ast.Constant)
                and isinstance(item.value, str)
            }
    expected_markdown = {
        "- Tenant-wide SharePoint baseline: `NOT_CLAIMED`",
        "- Tenant-wide SharePoint request allowance: `NOT_CLAIMED`",
        "- Tenant-wide SharePoint resource-unit allowance: `NOT_CLAIMED`",
        "- Monetary cost: `NOT_CLAIMED`",
    }
    if not expected_markdown.issubset(markdown_lines):
        errors.append("final Markdown renderer must emit all NOT_CLAIMED lines")


def _visible_markdown(content: str) -> str:
    return re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)


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
    for field in (
        "tenant_wide_sharepoint_baseline_claim_exact",
        "tenant_wide_sharepoint_request_allowance_claim_exact",
        "tenant_wide_sharepoint_resource_unit_allowance_claim_exact",
    ):
        if scope.get(field) != "NOT_CLAIMED":
            errors.append(f"scope {field} must be NOT_CLAIMED")
    if (
        scope.get("live_cli_implemented_offline") is not True
        or scope.get("live_action_composition_implemented_offline") is not True
    ):
        errors.append("the live CLI and composition must be implemented offline")
    if (
        scope.get("offline_adapters_implemented") is not True
        or scope.get("offline_adapters_are_not_a_live_action") is not True
        or scope.get("azure_resource_creation_or_change_executed_in_this_pr")
        is not False
        or scope.get("live_blob_or_lease_access_executed_in_this_pr") is not False
        or scope.get("live_target_dispatch_executed_in_this_pr") is not False
        or scope.get("tenant_wide_monetary_baseline_claim_exact")
        != "NOT_CLAIMED"
    ):
        errors.append("offline implementation must not claim live execution or cost")

    policy = _mapping(contract.get("measurement_policy"))
    if (
        policy.get("measurement_policy_id_exact")
        != "endpoint_scoped_conservative_measurement"
        or policy.get("target_dispatches_exact") != 500
        or policy.get("synthetic_gets_exact") != 500
        or policy.get("maximum_client_concurrency") != 1
        or policy.get("maximum_dispatches_per_minute_inclusive") != 6
        or policy.get(
            "non_cold_phase_minimum_interval_between_target_dispatches_seconds"
        ) != 10
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
        or order.get("phase_intervals_seconds_exact") != [1, 1, 10, 60, 300]
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
        monitor.get("metric_names_exact") != METRICS
        or monitor.get("aggregation_exact") != "Total"
        or monitor.get("interval_exact") != "PT1M"
        or monitor.get("dimension_filter_exact") is not None
        or monitor.get("rollup_scope_exact") != "app_wide_unfiltered_total"
        or monitor.get("series_shape_exact")
        != "exactly_one_dimensionless_series_per_metric_per_partition"
        or monitor.get("window_duration_seconds_minimum_inclusive") != 60
        or monitor.get("window_duration_seconds_maximum_inclusive") != 86400
        or monitor.get("windows_longer_than_24h_are_partitioned_without_gaps")
        is not True
        or monitor.get("complete_pt1m_grid_required_for_each_returned_series")
        is not True
        or monitor.get("settlement_delay_seconds_minimum_inclusive") != 300
        or monitor.get(
            "successful_final_on_demand_execution_count_minimum_inclusive"
        )
        != 500
        or monitor.get(
            "failed_final_on_demand_execution_count_minimum_equals_completed_network_dispatches"
        )
        is not True
        or monitor.get("completed_network_dispatch_count_evidence_required")
        is not True
        or monitor.get(
            "final_settled_window_must_cover_from_anchor_through_measurement_finished_at_utc"
        )
        is not True
        or monitor.get(
            "final_window_end_utc_must_be_at_or_after_measurement_finished_at_utc"
        )
        is not True
        or monitor.get(
            "final_observation_utc_must_be_at_or_after_final_window_end_plus_settlement_delay"
        )
        is not True
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
        budget.get("monetary_cost_claim_exact") != "NOT_CLAIMED"
        or budget.get("monetary_cost_claim_excludes_exact")
        != [
            "function_execution_count_charges",
            "azure_monitor_query_and_ingestion_charges",
            "blob_storage_and_transaction_charges",
            "network_charges",
            "taxes",
            "credits_free_grants_and_current_pricing",
        ]
        or budget.get("static_projected_full_measurement_gb_seconds_exact") != 30_000
        or budget.get(
            "observed_app_wide_delta_plus_projected_remaining_cap_gb_seconds_inclusive"
        )
        != 120_000
        or budget.get("projected_remaining_formula_exact")
        != (
            "30000 * min(500, remaining_target_dispatches + "
            "min(dispatched_target_attempts, 30)) / 500"
        )
        or budget.get("unsettled_dispatch_reserve_exact") != 30
        or budget.get("observed_values_are_app_wide_deltas") is not True
        or budget.get("observed_values_are_endpoint_attribution") is not False
        or budget.get("final_projected_remaining_gb_seconds_exact") != 0
        or budget.get(
            "projected_remaining_gb_seconds_evidence_required_for_every_safety_observation"
        )
        is not True
    ):
        errors.append("Azure execution budget must be 30000 projected and 120000 capped")

    lease = _mapping(contract.get("exclusive_lease"))
    if (
        lease.get("architecture_exact") != "owner_ticketed_bff_broker_uami"
        or lease.get("local_adapter_path_exact") != str(LEASE_BROKER_CLIENT)
        or lease.get("broker_path_exact") != str(LEASE_BROKER)
        or lease.get("broker_storage_path_exact") != str(LEASE_BROKER_STORAGE)
        or lease.get("local_auth_path_exact") != str(LEASE_BROKER_AUTH)
        or lease.get("broker_composition_path_exact")
        != str(LEASE_BROKER_COMPOSITION)
        or lease.get("broker_test_path_exact") != str(LEASE_BROKER_TESTS)
        or lease.get("broker_storage_test_path_exact")
        != str(LEASE_BROKER_STORAGE_TESTS)
        or lease.get("local_auth_test_path_exact") != str(LEASE_BROKER_AUTH_TESTS)
        or lease.get("local_client_test_path_exact")
        != str(LEASE_BROKER_CLIENT_TESTS)
        or lease.get("broker_composition_test_path_exact")
        != str(LEASE_BROKER_COMPOSITION_TESTS)
        or lease.get("broker_fastapi_test_path_exact")
        != str(LEASE_BROKER_FASTAPI_TESTS)
        or lease.get("broker_routes_exact")
        != [
            "POST /v1/internal/performance-lease/acquire",
            "POST /v1/internal/performance-lease/assert",
            "POST /v1/internal/performance-lease/release",
        ]
        or lease.get("broker_operations_exact")
        != ["acquire", "assert_held", "release"]
        or lease.get("state_machine_exact") != LEASE_STATES
        or lease.get("automatic_reacquire_allowed") is not False
        or lease.get("break_exposed_by_broker_or_local_api") is not False
        or lease.get("azure_rbac_write_data_action_can_break_or_overwrite")
        is not True
        or lease.get("delete_allowed") is not False
        or lease.get("private_lease_id_is_generated_and_persisted_only_inside_broker")
        is not True
        or lease.get("local_runner_lease_id_is_fence_only_and_never_sent")
        is not True
        or lease.get("storage_token_holder_exact") != "broker_uami_only"
        or lease.get("broker_storage_token_scope_exact")
        != "https://storage.azure.com/.default"
        or lease.get("local_runner_storage_token_allowed") is not False
        or lease.get("local_runner_token_scope_exact")
        != "api://funktion8.de/nac-bff/.default"
        or lease.get("local_runner_token_audience_exact")
        != "api://funktion8.de/nac-bff"
        or lease.get("local_runner_may_request_any_other_token_scope") is not False
        or lease.get("local_runner_storage_data_actions_exact") != []
        or lease.get("local_runner_storage_url_header_method_or_lease_id_surface_allowed")
        is not False
        or lease.get("broker_app_role_exact") != "Performance.Lease"
        or lease.get("broker_ticket_scope_exact") != "nac.performance.lease"
        or lease.get("ticket_schema_exact")
        != "nac.azure-performance-lease-activation-ticket/v1"
        or lease.get("receipt_schema_exact")
        != "nac.azure-performance-lease-broker-receipt/v1"
        or lease.get("ticket_signature_algorithm_exact") != "RS256"
        or lease.get("ticket_lifetime_seconds_maximum") != 60
        or lease.get("ticket_actions_count_exact") != 1
        or lease.get("ticket_operation_must_equal_requested_broker_route")
        is not True
        or lease.get("ticket_future_skew_seconds_maximum") != 5
        or lease.get("successful_final_measurement_requires_state_exact")
        != "RELEASED"
        or lease.get("release_receipt_state_exact") != "RELEASED"
        or lease.get("release_receipt_lifecycle_state_field_exact")
        != "lifecycle_state"
        or lease.get("completion_evidence_release_state_field_exact")
        != "lease_release_lifecycle_state"
        or lease.get("release_state_evidence_sha256_required") is not True
        or lease.get(
            "release_receipt_target_binding_sha256_must_match_measurement"
        )
        is not True
        or lease.get(
            "release_lifecycle_state_hash_without_exact_released_state_is_sufficient"
        )
        is not False
        or lease.get("broker_receipt_binding_fingerprint_must_match_owner_bound_broker")
        is not True
        or lease.get("broker_never_receipts_private_lease_id_storage_url_token_or_raw_ticket")
        is not True
    ):
        errors.append("brokered exclusive lease boundary or final gate drifted")

    broker_boundary = _mapping(contract.get("lease_broker_boundary"))
    if (
        broker_boundary.get("credential_boundary_exact") != "BFF_BROKER_UAMI_ONLY"
        or broker_boundary.get("broker_principal_parameter_exact")
        != "brokerPrincipalId"
        or broker_boundary.get("broker_caller_service_principal_parameter_exact")
        != "brokerCallerServicePrincipalId"
        or broker_boundary.get("broker_caller_and_broker_principals_must_be_distinct")
        is not True
        or broker_boundary.get("broker_function_app_resource_id_parameter_exact")
        != "brokerFunctionAppResourceId"
        or broker_boundary.get("broker_function_package_sha256_parameter_exact")
        != "brokerFunctionPackageSha256"
        or broker_boundary.get("broker_ticket_certificate_sha256_parameter_exact")
        != "brokerTicketVerificationCertificateSha256"
        or broker_boundary.get("broker_outbound_ip_addresses_parameter_exact")
        != "brokerOutboundIpAddresses"
        or broker_boundary.get("broker_allowed_data_actions_exact")
        != [
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/read",
            "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/write",
        ]
        or broker_boundary.get("local_runner_storage_data_actions_exact") != []
        or broker_boundary.get("local_runner_storage_token_or_certificate_allowed")
        is not False
        or broker_boundary.get("local_runner_bff_app_token_scope_exact")
        != "api://funktion8.de/nac-bff/.default"
        or broker_boundary.get(
            "local_runner_bff_app_token_is_certificate_authenticated"
        )
        is not True
        or broker_boundary.get(
            "local_runner_signs_one_operation_ticket_with_60_second_lifetime"
        )
        is not True
        or broker_boundary.get("put_precondition_exact") != "If-None-Match:*"
        or broker_boundary.get("content_length_exact") != 0
        or broker_boundary.get("strong_etag_readback_required") is not True
        or broker_boundary.get("delete_or_break_operation_exposed") is not False
        or broker_boundary.get("lease_broker_policy_sha256_required") is not True
        or broker_boundary.get(
            "server_side_state_machine_is_atomic_durable_idempotent_and_restart_reconcilable"
        )
        is not True
    ):
        errors.append("BFF broker UAMI and local-runner isolation policy drifted")

    owner = _mapping(contract.get("activation_and_owner_gate"))
    if set(owner.get("owner_approval_binding_fields_exact", [])) != OWNER_FIELDS:
        errors.append("runtime owner gate must bind its exact activation and policy inputs")
    if set(owner.get("verified_activation_receipt_binding_fields_exact", [])) != {
        "approved_commit_sha",
        "approved_tree_sha",
        "toolchain_attestations_sha256",
        "target_binding_sha256",
    }:
        errors.append("activation receipt binding fields drifted")
    if (
        owner.get("owner_approval_action_exact")
        != "CREATE_UNLOCKED_WORM_BASELINE_PROVISION_AND_EXECUTE_M365_BFF_ENDPOINT_SCOPED_CONSERVATIVE_MEASUREMENT"
        or owner.get("runtime_owner_gate_is_combined_infrastructure_gate")
        is not True
        or owner.get(
            "offline_gate_returns_owner_execution_bindings_not_runtime_bindings"
        )
        is not True
        or owner.get(
            "runtime_owner_and_infrastructure_preflight_must_return_and_match_all_execution_bindings"
        )
        is not True
        or owner.get(
            "runtime_execution_bindings_require_infrastructure_safety_evidence_sha256"
        )
        is not True
    ):
        errors.append("runtime owner action must match the implementation")

    combined_owner = _mapping(
        contract.get("combined_infrastructure_and_live_owner_gate")
    )
    if (
        combined_owner.get("action_exact")
        != "CREATE_UNLOCKED_WORM_BASELINE_PROVISION_AND_EXECUTE_M365_BFF_ENDPOINT_SCOPED_CONSERVATIVE_MEASUREMENT"
        or set(combined_owner.get("binding_fields_exact", []))
        != COMBINED_OWNER_FIELDS
        or combined_owner.get("approval_count_exact") != 1
        or combined_owner.get("network_accessed_during_generation") is not False
        or set(combined_owner.get("worm_baseline_parameter_fields_exact", []))
        != WORM_BASELINE_PARAMETER_FIELDS
        or combined_owner.get("worm_baseline_compiled_arm_path_exact")
        != str(WORM_INFRA_COMPILED)
        or combined_owner.get("worm_baseline_compiled_parameters_path_exact")
        != str(WORM_INFRA_COMPILED_PARAMETERS)
        or combined_owner.get("worm_baseline_irreversible_policy_lock_allowed")
        is not False
        or combined_owner.get("deployment_sequence_exact")
        != [
            "deploy_unlocked_worm_baseline",
            "verify_worm_baseline_readback",
            "deploy_performance_coordination",
            "verify_coordination_and_effective_rbac",
            "acquire_owner_ticketed_broker_lease",
            "execute_endpoint_scoped_conservative_measurement",
            "release_lease_and_finalize_redacted_evidence",
        ]
    ):
        errors.append("combined infrastructure/live owner gate drifted")
    deployment_scope = _mapping(combined_owner.get("deployment_scope_exact"))
    if (
        set(combined_owner.get("infrastructure_parameter_fields_exact", []))
        != INFRASTRUCTURE_PARAMETER_FIELDS
        or deployment_scope.get("tenant_id")
        != "870c862b-56f7-4c9b-b0d9-f1f7d32c835c"
        or deployment_scope.get("subscription_id")
        != "37cd9645-6cb9-4278-88ee-e80377cd951c"
        or deployment_scope.get("resource_group_name")
        != "rg-nac-bff-test"
        or deployment_scope.get("location") != "germanywestcentral"
        or deployment_scope.get("deployment_mode") != "Incremental"
        or deployment_scope.get("nonempty_tags_required") is not True
    ):
        errors.append("combined owner gate must bind the exact Azure deployment scope")

    infrastructure_safety = _mapping(contract.get("infrastructure_safety"))
    restart_reconciliation = _mapping(
        infrastructure_safety.get("restart_reconciliation_exact")
    )
    if (
        infrastructure_safety.get("implementation_path_exact")
        != str(INFRA_SAFETY)
        or infrastructure_safety.get("test_path_exact")
        != str(INFRA_SAFETY_TESTS)
        or infrastructure_safety.get("arm_validator_path_exact")
        != str(INFRA_ARM_VALIDATOR)
        or infrastructure_safety.get(
            "coordination_storage_account_name_policy_exact"
        )
        != "immutable-original-available-or-read-only-exact-success-reconciliation"
        or infrastructure_safety.get(
            "postdeployment_coordination_storage_configuration_readback_required"
        )
        is not True
        or infrastructure_safety.get("readback_freshness_seconds_exact")
        != {
            "predeployment_maximum": 1800,
            "postdeployment_maximum": 300,
            "future_skew_maximum": 30,
        }
        or infrastructure_safety.get(
            "readback_toolchain_session_and_command_binding_required"
        )
        is not True
        or infrastructure_safety.get("readback_trusted_clock_generated_internally")
        is not True
        or infrastructure_safety.get(
            "readback_owner_bound_one_use_nonce_required"
        )
        is not True
        or infrastructure_safety.get("readback_nonce_replay_behavior")
        != "reject_before_lease_acquire"
        or infrastructure_safety.get(
            "readback_actual_sealed_executable_argv_and_session_attestation_required"
        )
        is not True
        or infrastructure_safety.get(
            "sealed_readback_adapter_executes_fixed_commands_internally"
        )
        is not True
        or infrastructure_safety.get(
            "sealed_readback_subprocess_environment_is_sanitized_and_bound"
        )
        is not True
        or infrastructure_safety.get(
            "sealed_executable_remeasured_immediately_before_subprocess"
        )
        is not True
        or infrastructure_safety.get(
            "public_readback_adapter_produces_verifier_ready_arm_graph_and_effective_rbac_envelopes"
        )
        is not True
        or infrastructure_safety.get(
            "serialized_safety_evidence_authorizes_after_process_restart"
        )
        is not False
        or infrastructure_safety.get(
            "process_restart_requires_fresh_read_only_infrastructure_reattestation"
        )
        is not True
        or infrastructure_safety.get(
            "exact_readback_argv_api_resource_and_response_digest_required"
        )
        is not True
        or infrastructure_safety.get(
            "helper_fabricated_readback_envelopes_allowed"
        )
        is not False
        or infrastructure_safety.get(
            "immutable_original_name_available_receipt_persisted_before_deployment_required"
        )
        is not True
        or infrastructure_safety.get(
            "immutable_exact_successful_deployment_receipt_persisted_after_deployment_required"
        )
        is not True
        or restart_reconciliation
        != {
            "complete_receipt_pair_required": True,
            "fresh_get_same_deterministic_successful_deployment_required": True,
            "matching_owner_target_source_parameters_and_hashes_required": True,
            "name_availability_probe_count_exact": 0,
            "deployment_create_count_exact": 0,
            "fresh_postdeployment_safety_readbacks_required": True,
            "running_failed_missing_replaced_or_mismatch_behavior": (
                "block_before_provider_mutation"
            ),
            "name_only_retry_requires_new_current_name_available_true": True,
            "name_only_retry_name_unavailable_behavior": (
                "block_without_deployment_create"
            ),
            "historical_name_receipt_alone_authorizes_redeployment": False,
            "temporal_relation_exact": (
                "original_observed_lt_started_lte_completed_lt_current_reconciliation_observed"
            ),
        }
        or infrastructure_safety.get(
            "deployment_receipt_owner_nonce_and_timestamp_continuity_required"
        )
        is not True
        or infrastructure_safety.get(
            "owner_bound_tenant_subscription_resource_group_storage_broker_and_caller_principals_function_package_certificate_outbound_ips_location_tags_and_network_required"
        )
        is not True
        or infrastructure_safety.get(
            "broker_caller_service_principal_has_no_storage_data_action"
        )
        is not True
        or infrastructure_safety.get(
            "broker_function_app_resource_id_and_uami_assignment_readback_required"
        )
        is not True
        or infrastructure_safety.get(
            "broker_function_package_and_ticket_certificate_hashes_readback_required"
        )
        is not True
        or infrastructure_safety.get(
            "broker_outbound_ip_readback_must_exactly_match_storage_firewall_rules"
        )
        is not True
        or infrastructure_safety.get(
            "local_runner_has_no_storage_token_certificate_or_data_action"
        )
        is not True
        or infrastructure_safety.get(
            "authoritative_bff_and_worm_storage_resource_ids_required"
        )
        is not True
        or infrastructure_safety.get(
            "coordination_bff_and_worm_storage_accounts_must_be_distinct"
        )
        is not True
        or infrastructure_safety.get(
            "effective_tags_are_canonical_union_and_owner_bound"
        )
        is not True
        or infrastructure_safety.get(
            "postdeployment_storage_and_network_configuration_exact"
        )
        != {
            "public_network_access": "Enabled",
            "default_action": "Deny",
            "bypass": "None",
            "allowed_ip_rules_exactly_equal_bound_broker_outbound_ip_addresses": True,
            "virtual_network_rule_count_exact": 0,
            "resource_access_rule_count_exact": 0,
            "shared_key_access_allowed": False,
            "blob_public_access_allowed": False,
            "minimum_tls_version": "TLS1_2",
            "https_only": True,
            "blob_service_versioning_enabled": False,
            "blob_delete_retention_enabled": False,
            "container_delete_retention_enabled": False,
            "lease_container_public_access_exact": "None",
            "lease_container_metadata_exact": {
                "nac_schema_version": "nac.azure-bff-performance-coordination/v1",
                "data_classification": "synthetic-only",
                "lease_blob_path": "locks/<target_binding_sha256>.lock",
                "lease_blob_type": "BlockBlob",
                "lease_blob_content_length": "0",
                "lease_blob_bootstrap": "broker-internal-put-if-absent-before-acquire",
                "broker_authorization": "non-exportable-managed-identity-read-write-no-delete",
                "azure_blob_write_authorization": "broker-uami-write-includes-create-overwrite-lease-and-break",
                "operation_restriction_boundary": "owner-ticketed-fixed-function-route",
                "local_runner_storage_authorization": "none",
                "brokerFunctionPackageSha256": "<owner_bound_sha256>",
                "brokerTicketVerificationCertificateSha256": "<owner_bound_sha256>",
            },
        }
        or infrastructure_safety.get(
            "effective_role_assignment_ancestor_scopes_exact"
        )
        != [
            "tenant_root",
            "management_group_chain",
            "subscription",
            "resource_group",
            "storage_account",
            "blob_service",
            "container",
        ]
        or infrastructure_safety.get(
            "broader_effective_data_assignment_allowed"
        )
        is not False
        or infrastructure_safety.get(
            "tenant_root_management_group_must_match_owner_tenant"
        )
        is not True
        or infrastructure_safety.get(
            "subscription_management_group_ancestry_must_be_authoritative_and_ordered"
        )
        is not True
        or infrastructure_safety.get(
            "management_group_parent_child_relationships_and_subscription_attachment_required"
        )
        is not True
        or infrastructure_safety.get(
            "owner_binding_sha256_must_match_current_approval"
        )
        is not True
        or infrastructure_safety.get(
            "safety_evidence_maximum_age_seconds_at_broker_acquire"
        )
        != 300
        or infrastructure_safety.get("effective_control_plane_assignment_allowed")
        is not False
        or infrastructure_safety.get(
            "expected_effective_broker_assignment_count_exact"
        )
        != 1
        or infrastructure_safety.get("condition_version_exact") != "2.0"
        or infrastructure_safety.get("bicep_compile_required_in_ci") is not True
        or infrastructure_safety.get("pinned_bicep_version_exact")
        != "0.45.15.27210"
        or infrastructure_safety.get("canonical_compiled_arm_path_exact")
        != str(INFRA_COMPILED)
        or infrastructure_safety.get(
            "canonical_compiled_parameters_path_exact"
        )
        != str(INFRA_COMPILED_PARAMETERS)
        or infrastructure_safety.get(
            "compiled_artifacts_must_be_byte_reproducible_in_ci"
        )
        is not True
        or infrastructure_safety.get("live_readback_required_before_measurement")
        is not True
        or infrastructure_safety.get(
            "live_readback_must_validate_safe_before_lease_acquire"
        )
        is not True
        or infrastructure_safety.get(
            "closing_clean_git_snapshot_required_after_all_gate_measurements"
        )
        is not True
        or infrastructure_safety.get(
            "closing_git_snapshot_commit_and_tree_carried_to_lease_boundary"
        )
        is not True
        or infrastructure_safety.get(
            "infrastructure_safety_evidence_schema_exact"
        )
        != _string_constant(
            INFRA_SAFETY,
            "INFRASTRUCTURE_SAFETY_EVIDENCE_SCHEMA",
        )
        or infrastructure_safety.get(
            "infrastructure_safety_evidence_sha256_required"
        )
        is not True
    ):
        errors.append("coordination infrastructure safety contract drifted")

    boundary = _mapping(contract.get("live_action_boundary"))
    if (
        boundary.get("live_cli_exposed_offline") is not True
        or boundary.get("live_cli_command_exact")
        != "nac m365 teams-sharepoint bff-performance-acceptance"
        or boundary.get("live_cli_gate_flags_exact")
        != ["--owner-approved", "--execute-live-acceptance"]
        or boundary.get("live_cli_requires_each_gate_flag_exactly_once") is not True
        or boundary.get("live_cli_requires_immutable_owner_gate") is not True
        or boundary.get("live_action_composition_implemented_offline") is not True
        or boundary.get("contract_slice_executes_live_action") is not False
        or boundary.get("live_execution_requires_fresh_hash_bound_owner_approval")
        is not True
    ):
        errors.append(
            "live CLI must remain behind both flags and a fresh immutable owner gate"
        )
    if any(
        boundary.get(field) is not False
        for field in (
            "live_azure_cli_invocation_allowed_by_this_contract_slice",
            "live_blob_or_lease_operation_allowed_by_this_contract_slice",
            "live_target_dispatch_allowed_by_this_contract_slice",
        )
    ):
        errors.append("contract slice must perform no live action")
    if (
        boundary.get("azure_command_adapter_path_exact") != str(AZURE_COMMANDS)
        or boundary.get("azure_command_adapter_test_path_exact")
        != str(AZURE_COMMAND_TESTS)
        or boundary.get("monitor_read_command_requires_exact_canonical_url_shape")
        is not True
        or boundary.get("generic_azure_cli_run_rejects_monitor_metrics_url")
        is not True
        or boundary.get("monitor_read_command_allows_request_body") is not False
        or boundary.get(
            "monitor_read_requires_exact_owner_bound_action_and_policy_binding"
        )
        is not True
        or boundary.get("monitor_read_capability_uses_maximum_inclusive") != 2048
        or boundary.get("monitor_read_capability_consumed_before_token_or_network")
        is not True
        or boundary.get(
            "monitor_read_capability_usage_is_separate_from_target_get_ledger"
        )
        is not True
        or boundary.get(
            "composition_requires_verified_owner_and_infrastructure_capability"
        )
        is not True
        or boundary.get("infrastructure_provenance_requires_sealed_readback_capability")
        is not True
        or boundary.get(
            "every_broker_monitor_and_target_call_requires_exact_action_target_and_binding"
        )
        is not True
        or boundary.get("live_action_capability_use_is_bounded_and_non_replayable")
        is not True
        or boundary.get(
            "broker_ticket_and_broker_api_capability_consumed_before_broker_state_or_storage_token"
        )
        is not True
        or boundary.get("broker_routes_exact")
        != [
            "/v1/internal/performance-lease/acquire",
            "/v1/internal/performance-lease/assert",
            "/v1/internal/performance-lease/release",
        ]
        or boundary.get(
            "local_runner_may_call_only_fixed_broker_routes_for_lease_lifecycle"
        )
        is not True
        or boundary.get("local_runner_broker_token_scope_exact")
        != "api://funktion8.de/nac-bff/.default"
        or boundary.get("local_runner_ticket_lifetime_seconds_exact") != 60
        or boundary.get("local_runner_ticket_actions_count_exact") != 1
        or boundary.get(
            "local_runner_storage_token_url_headers_data_actions_or_private_lease_id_allowed"
        )
        is not False
        or boundary.get(
            "m365_delegated_token_requires_cryptographic_entra_rs256_validation"
        )
        is not True
        or boundary.get(
            "m365_delegated_token_attestation_binds_resource_and_scopes"
        )
        is not True
        or boundary.get(
            "direct_broker_or_local_adapter_invocation_without_authority_behavior"
        )
        != "BLOCKED_before_token_network_or_state"
    ):
        errors.append("verified live-action capability boundary drifted")

    resumable = _mapping(contract.get("resumable_state"))
    if (
        resumable.get("complete_process_lifecycle_fenced_by_nonblocking_local_lock")
        is not True
        or resumable.get(
            "authoritative_reads_use_nofollow_and_same_descriptor_fstat"
        )
        is not True
        or resumable.get(
            "private_paths_reject_symlink_in_every_ancestor_component"
        )
        is not True
        or resumable.get(
            "atomic_replacements_use_validated_directory_descriptor"
        )
        is not True
        or resumable.get("unsafe_or_foreign_checkpoint_parent_behavior")
        != "BLOCKED"
        or resumable.get("concurrent_same_state_path_behavior")
        != "BLOCKED_before_owner_or_network"
        or resumable.get(
            "same_broker_operation_nonce_ticket_target_and_lease_binding_required_on_resume"
        )
        is not True
        or resumable.get(
            "broker_private_lease_id_is_server_side_and_not_reconstructed_by_local_runner"
        )
        is not True
        or resumable.get(
            "process_restart_requires_fresh_read_only_infrastructure_reattestation"
        )
        is not True
        or resumable.get(
            "fresh_reattestation_must_preserve_owner_tenant_broker_principal_function_package_certificate_outbound_ips_target_and_lease_binding"
        )
        is not True
        or resumable.get(
            "stale_pre_restart_safety_evidence_cannot_authorize_new_mutation"
        )
        is not True
        or resumable.get("terminal_measurement_schema_exact")
        != "nac.m365-bff-performance-terminal-measurement/v1"
        or resumable.get("terminal_measurement_persisted_before_final_monitor_read")
        is not True
        or resumable.get("final_monitor_failure_retains_terminal_measurement_and_held_lease")
        is not True
        or resumable.get("terminal_measurement_resume_may_repeat_only_final_monitor_read")
        is not True
        or resumable.get("pending_finalization_schema_exact")
        != "nac.m365-bff-performance-pending-finalization/v1"
        or resumable.get("post_release_crash_recovery_reuses_pending_finalization")
        is not True
        or resumable.get("post_release_crash_recovery_may_reacquire_or_reread_monitor")
        is not False
        or resumable.get(
            "early_failed_measurement_must_finalize_release_and_persist_failed_evidence"
        )
        is not True
        or resumable.get("durable_transport_boundary_persisted_before_http_dispatch")
        is not True
        or resumable.get("pre_http_failure_completed_without_network_dispatch")
        is not True
        or resumable.get("crash_after_transport_boundary_counts_toward_monitor_floor")
        is not True
        or resumable.get(
            "clean_checkpoint_exception_must_resume_or_terminalize_before_release"
        )
        is not True
        or resumable.get(
            "every_redacted_terminal_measurement_evidence_must_persist_pending_finalization_before_release"
        )
        is not True
        or resumable.get(
            "same_broker_operation_id_release_reconciliation_after_crash_allowed"
        )
        is not True
        or resumable.get(
            "pending_finalization_cleared_only_after_json_and_markdown_are_durable"
        )
        is not True
        or resumable.get("completion_manifest_schema_exact")
        != "nac.m365-bff-performance-completion-manifest/v1"
        or resumable.get("completion_manifest_written_after_json_and_markdown")
        is not True
        or resumable.get(
            "completion_manifest_binds_exact_json_markdown_and_final_evidence_hashes"
        )
        is not True
        or resumable.get(
            "json_or_markdown_without_valid_completion_manifest_is_not_final"
        )
        is not True
        or resumable.get(
            "completed_final_evidence_requires_fresh_owner_and_safety_preflight_before_read_without_lease_monitor_or_target_network"
        )
        is not True
    ):
        errors.append("post-release finalization recovery contract drifted")

    evidence_policy = _mapping(contract.get("evidence_policy"))
    if (
        evidence_policy.get(
            "final_monitor_attestation_and_execution_cap_are_revalidated_and_bound"
        )
        is not True
        or evidence_policy.get(
            "failed_final_monitor_minimum_is_revalidated_against_nested_completed_network_dispatch_count"
        )
        is not True
        or evidence_policy.get(
            "final_evidence_json_and_markdown_are_atomically_persisted_after_release"
        )
        is not True
        or evidence_policy.get("formats_required") != ["json", "markdown"]
        or any(
            evidence_policy.get(field) != "NOT_CLAIMED"
            for field in (
                "tenant_wide_sharepoint_baseline_claim_exact",
                "tenant_wide_sharepoint_request_allowance_claim_exact",
                "tenant_wide_sharepoint_resource_unit_allowance_claim_exact",
                "monetary_cost_claim_exact",
            )
        )
        or set(evidence_policy.get("required_hash_bindings_exact", []))
        != EVIDENCE_BINDING_FIELDS
        or evidence_policy.get(
            "final_monitor_attestation_covers_measurement_finished_at_after_settlement"
        )
        is not True
        or evidence_policy.get(
            "successful_terminal_measurement_evidence_projected_remaining_gb_seconds_exactly_zero"
        )
        is not True
        or evidence_policy.get(
            "final_release_receipt_proves_exact_released_state_target_and_lease_binding"
        )
        is not True
        or evidence_policy.get(
            "final_monitor_on_demand_execution_count_minimum_inclusive"
        )
        != 500
        or evidence_policy.get("final_completion_manifest_is_the_commit_point")
        is not True
    ):
        errors.append("final monitor/cap or JSON/Markdown evidence contract drifted")

    passed = _mapping(contract.get("pass_condition"))
    if (
        passed.get("global_target_dispatch_count_exact") != 500
        or passed.get("lease_final_state_exact") != "RELEASED"
        or any(
            passed.get(field) != "NOT_CLAIMED"
            for field in (
                "tenant_wide_sharepoint_baseline_claim_exact",
                "tenant_wide_sharepoint_request_allowance_claim_exact",
                "tenant_wide_sharepoint_resource_unit_allowance_claim_exact",
                "monetary_cost_claim_exact",
            )
        )
        or passed.get("final_on_demand_execution_count_at_least_500") is not True
    ):
        errors.append("PASSED must require 500 dispatches, NOT_CLAIMED and RELEASED")


def _validate_verification(
    verification: dict[str, Any], errors: list[str]
) -> None:
    if verification.get("leading_issue") != ISSUE:
        errors.append("verification contract must bind Issue #735")
    if verification.get("acceptance_ids") != ACCEPTANCE_IDS:
        errors.append("verification contract must bind AC-735-01 through AC-735-09")
    verification_passed = _mapping(verification.get("pass_condition"))
    for field in (
        "tenant_wide_sharepoint_baseline_claim_exact",
        "tenant_wide_sharepoint_request_allowance_claim_exact",
        "tenant_wide_sharepoint_resource_unit_allowance_claim_exact",
        "monetary_cost_claim_exact",
    ):
        if verification_passed.get(field) != "NOT_CLAIMED":
            errors.append(f"verification pass condition {field} must be NOT_CLAIMED")
    checks = verification.get("checks")
    expected_cli_test = (
        "PYTHONPATH=src python3 -m unittest "
        "tests.test_nac_cli_bff_performance_acceptance"
    )
    if not isinstance(checks, list) or expected_cli_test not in checks:
        errors.append("verification contract must execute the focused CLI test module")
    required_iac_checks = {
        "az bicep build --file deploy/runtime/azure/nac-bff-performance-coordination/main.bicep --stdout > /tmp/nac-bff-performance-coordination-main.json",
        "az bicep build-params --file deploy/runtime/azure/nac-bff-performance-coordination/main.example.bicepparam --stdout > /tmp/nac-bff-performance-coordination-main-params.json",
        "cmp /tmp/nac-bff-performance-coordination-main.json deploy/runtime/azure/nac-bff-performance-coordination/compiled/main.json",
        "cmp /tmp/nac-bff-performance-coordination-main-params.json deploy/runtime/azure/nac-bff-performance-coordination/compiled/main.example.json",
        "python3 scripts/validate_nac_bff_performance_coordination_arm.py /tmp/nac-bff-performance-coordination-main.json /tmp/nac-bff-performance-coordination-main-params.json",
        "python3 scripts/validate_business_case_type_azure_blob_worm.py",
    }
    if not isinstance(checks, list) or not required_iac_checks.issubset(checks):
        errors.append(
            "verification contract must compile, byte-compare and validate both IaC artifacts"
        )
    required_context = verification.get("required_context")
    for required_path in (
        AUTHORIZATION,
        AUTHORIZATION_TESTS,
        AZURE_COMMANDS,
        AZURE_COMMAND_TESTS,
        CLI,
        CLI_TESTS,
        CONTRACT_INDEX,
        INFRA_SAFETY,
        INFRA_SAFETY_TESTS,
        INFRA_ARM_VALIDATOR,
        INFRA_PARAMETERS,
        INFRA_COMPILED,
        INFRA_COMPILED_PARAMETERS,
        COMPOSITION,
        COMPOSITION_TESTS,
        WORM_INFRA,
        WORM_INFRA_PARAMETERS,
        WORM_INFRA_COMPILED,
        WORM_INFRA_COMPILED_PARAMETERS,
        QUALITY_GATE_WORKFLOW,
    ):
        if not isinstance(required_context, list) or str(required_path) not in required_context:
            errors.append(
                f"verification required_context must include {required_path}"
            )

    thresholds = _mapping(verification.get("thresholds"))
    if (
        thresholds.get("global_target_dispatches_exact") != 500
        or thresholds.get("phase_dispatch_allocations_exact")
        != [1, 1, 90, 120, 288]
        or thresholds.get("phase_request_intervals_seconds_exact")
        != [1, 1, 10, 60, 300]
        or thresholds.get("client_concurrency_exact") != 1
        or thresholds.get("dispatches_per_minute_maximum_inclusive") != 6
        or thresholds.get("monitor_read_capability_uses_maximum_inclusive")
        != 2048
        or thresholds.get("static_projected_full_measurement_gb_seconds_exact")
        != 30_000
        or thresholds.get(
            "observed_app_wide_plus_projected_remaining_gb_seconds_maximum_inclusive"
        )
        != 120_000
    ):
        errors.append("verification thresholds do not match the conservative plan")

    evidence = verification.get("required_evidence")
    if not isinstance(evidence, list) or not VERIFICATION_EVIDENCE_BINDING_FIELDS.issubset(
        evidence
    ):
        errors.append("verification evidence must carry every exact owner binding")
    elif not {
        "final_measurement_attestation_sha256",
        "final_monitor_cap_binding",
        "final_on_demand_execution_count_minimum_500",
        "completion_manifest_json_markdown_and_evidence_hashes",
        "effective_rbac_abac_readback",
        "pending_finalization_recovery_without_network",
        "tenant_wide_sharepoint_request_allowance_NOT_CLAIMED",
        "tenant_wide_sharepoint_resource_unit_allowance_NOT_CLAIMED",
        "monetary_cost_NOT_CLAIMED",
    }.issubset(evidence):
        errors.append("verification evidence must cover final monitor and recovery")


def main() -> int:
    errors: list[str] = []
    try:
        contract = _json(CONTRACT)
        verification = _json(VERIFICATION)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1

    paths = (
        AUTHORIZATION,
        IMPLEMENTATION,
        MONITOR,
        LEASE_BROKER,
        LEASE_BROKER_STORAGE,
        LEASE_BROKER_AUTH,
        LEASE_BROKER_CLIENT,
        LEASE_BROKER_COMPOSITION,
        BFF_COMPOSITION,
        FASTAPI_ADAPTER,
        RUNTIME,
        COMPOSITION,
        OWNER_GATE,
        INFRA_SAFETY,
        INFRASTRUCTURE_PORTS,
        AZURE_COMMANDS,
        CLI,
        INFRA,
        WORM_INFRA,
        WORM_INFRA_PARAMETERS,
        WORM_INFRA_COMPILED,
        WORM_INFRA_COMPILED_PARAMETERS,
        INFRA_ARM_VALIDATOR,
        QUALITY_GATE_WORKFLOW,
        TESTS,
        AUTHORIZATION_TESTS,
        MONITOR_TESTS,
        LEASE_BROKER_TESTS,
        LEASE_BROKER_STORAGE_TESTS,
        LEASE_BROKER_AUTH_TESTS,
        LEASE_BROKER_CLIENT_TESTS,
        LEASE_BROKER_COMPOSITION_TESTS,
        LEASE_BROKER_FASTAPI_TESTS,
        RUNTIME_TESTS,
        COMPOSITION_TESTS,
        OWNER_GATE_TESTS,
        INFRA_SAFETY_TESTS,
        INFRASTRUCTURE_PORT_TESTS,
        AZURE_COMMAND_TESTS,
        INFRA_TESTS,
        CLI_TESTS,
        CONTRACT_INDEX,
        DOC_DE,
        DOC_EN,
        PLAN_DE,
        SPEC_DE,
        PLAN_EN,
        SPEC_EN,
    )
    texts = _read_required(paths, errors)
    _validate_contract(contract, errors)
    _validate_verification(verification, errors)
    _validate_not_claimed_renderers(errors)

    required_fragments: dict[Path, tuple[str, ...]] = {
        AUTHORIZATION: (
            "class VerifiedLiveActionCapability",
            "class VerifiedPerformanceAuthority",
            "class VerifiedInfrastructureSafetySource",
            "AzurePerformanceInfrastructureSafetyVerification",
            "AzurePerformanceInfrastructureReadbackCapability",
            "PERFORMANCE_LIVE_CAPABILITY_REQUIRED",
            "PERFORMANCE_LIVE_CAPABILITY_BINDING_MISMATCH",
            "PERFORMANCE_LIVE_CAPABILITY_EXHAUSTED",
            "_open_root_anchored_private_parent",
            "O_NOFOLLOW",
        ),
        IMPLEMENTATION: (
            'CONTRACT_ID = "m365.bff_performance_acceptance"',
            "PERFORMANCE_DURABLE_CHECKPOINT_FAILED",
            "PERFORMANCE_TARGET_BINDING_MISMATCH",
            "PERFORMANCE_EVIDENCE_REDACTION_INVALID",
            "reserved_attempt_count",
            "final_checkpoint_sha256",
            "_PerformancePreDispatchAbort",
            "INFLIGHT_DISPATCH_OUTCOME_UNKNOWN",
            "self._verify_bound_endpoint(endpoint)",
            "/workbench-snapshot?purpose=",
            "class CryptographicM365TokenAttestor",
            "class AttestedM365AccessToken",
            '"tenant_wide_sharepoint_request_allowance_claim"',
            '"tenant_wide_sharepoint_resource_unit_allowance_claim"',
            '"monetary_cost_claim"',
        ),
        MONITOR: (
            'API_VERSION = "2023-10-01"',
            'METRIC_NAMESPACE = "Microsoft.Web/sites"',
            'AGGREGATION = "Total"',
            'INTERVAL = "PT1M"',
            'ROLLUP_SCOPE = "app_wide_unfiltered_total"',
            'ROLLUP_SERIES_SHAPE = "exactly_one_dimensionless_series_per_metric_per_partition"',
            "INGESTION_LAG_SECONDS = 300",
            "MIN_WINDOW_SECONDS = 60",
            "MAX_WINDOW_SECONDS = 24 * 60 * 60",
            '"OnDemandFunctionExecutionUnits"',
            '"OnDemandFunctionExecutionCount"',
            '"AlwaysReadyFunctionExecutionUnits"',
            '"AlwaysReadyUnits"',
            '"AlwaysReadyFunctionExecutionCount"',
            "if metadata != []:",
            "len(series_items) != 1",
            "PERFORMANCE_MONITOR_WINDOW_NOT_SETTLED",
            "app_wide_delta_is_conservative_and_not_attributable_solely_to_test_traffic",
        ),
        LEASE_BROKER: (
            'TICKET_VERSION = "nac.azure-performance-lease-activation-ticket/v1"',
            'RECEIPT_VERSION = "nac.azure-performance-lease-broker-receipt/v1"',
            "MAX_TICKET_LIFETIME_SECONDS = 60",
            "MAX_FUTURE_SKEW_SECONDS = 5",
            "class RsaCertificateTicketSignatureVerifier",
            "class AttestedStorageBinding",
            "class BrokerRoleScopeClaims",
            "class AtomicLeaseStateMachinePort",
            "class AzurePerformanceLeaseBroker",
            '"function_package_sha256"',
            '"owner_binding_sha256"',
            '"target_binding_sha256"',
            "def acquire(",
            "def assert_held(",
            "def release(",
        ),
        LEASE_BROKER_STORAGE: (
            'AZURE_STORAGE_SCOPE = "https://storage.azure.com/.default"',
            "class AzureBlobAtomicLeaseStateMachine",
            '_ACQUIRE_INTENT = "ACQUIRE_INTENT"',
            '_ACQUIRE_IN_FLIGHT = "ACQUIRE_IN_FLIGHT"',
            '_HELD = "HELD"',
            '_RELEASE_INTENT = "RELEASE_INTENT"',
            '_RELEASED = "RELEASED"',
            '"x-ms-lease-action": action',
            'if action == "acquire":',
            'headers["x-ms-lease-duration"] = "-1"',
            'elif action == "release":',
            '"If-None-Match": "*"',
            "def _reconcile_acquire(",
            "def _set_metadata(",
        ),
        LEASE_BROKER_AUTH: (
            'BFF_API_AUDIENCE = "api://funktion8.de/nac-bff"',
            'BFF_APP_TOKEN_SCOPE = f"{BFF_API_AUDIENCE}/.default"',
            "class CertificateBffAppTokenProvider",
            "class RsaActivationTicketSigner",
            "credential.get_token(BFF_APP_TOKEN_SCOPE).token",
            'if operation not in {"acquire", "assert", "release"}:',
            "actions=(operation,)",
            "expires_at=now + MAX_TICKET_LIFETIME_SECONDS",
        ),
        LEASE_BROKER_CLIENT: (
            "class BrokeredAzureBlobLeaseAdapter",
            'frozenset({"acquire", "assert", "release"})',
            'f"{self._base_url}/v1/internal/performance-lease/{operation}"',
            'body = _canonical_json({"ticket": ticket})',
            'method="POST"',
            "def execution_fence(",
            "broker_receipt_sha256",
        ),
        LEASE_BROKER_COMPOSITION: (
            'PERFORMANCE_LEASE_APP_ROLE = "Performance.Lease"',
            'PERFORMANCE_LEASE_TICKET_SCOPE = "nac.performance.lease"',
            "class PerformanceLeaseBrokerSettings",
            "def build_performance_lease_broker(",
            "ManagedIdentityCredential",
            'managed_identity_client_id=_required(values, "AZURE_CLIENT_ID")',
            "RsaCertificateTicketSignatureVerifier",
            "AzureBlobAtomicLeaseStateMachine",
        ),
        BFF_COMPOSITION: (
            "build_performance_lease_broker",
            'values.get("NAC_BFF_PERFORMANCE_LEASE_ENABLED") == "true"',
            "required_roles={PERFORMANCE_LEASE_APP_ROLE}",
            "performance_lease_claims_dependency",
        ),
        FASTAPI_ADAPTER: (
            'if operation not in {"acquire", "assert", "release"}:',
            '"assert": "assert_held"',
            '"/v1/internal/performance-lease/{operation}"',
            'methods=["POST"]',
            "include_in_schema=False",
        ),
        RUNTIME: (
            "class AzurePerformanceRuntimeAdapter",
            "class LeaseBoundPerformanceAcceptance",
            "class PerformanceFinalEvidenceStore",
            "authorization_verifier",
            "BoundPerformanceAuthorizationVerifier",
            "tenant_wide_sharepoint_capacity_claim",
            "lease_binding_sha256",
            "monitor_evidence_sha256",
            "monitor_window_anchor_sha256",
            "nac.m365-bff-performance-pending-finalization/v1",
            "nac.m365-bff-performance-terminal-measurement/v1",
            "load_terminal_measurement",
            "load_final_evidence",
            "get_validated_final_attestation",
            '"measurement_finished_at_utc"',
            '"monitor_window_end_utc"',
            '"lease_release_lifecycle_state"',
            '"lease_release_state_evidence_sha256"',
            '"on_demand_execution_count"',
            '"minimum_on_demand_execution_count"',
            '"nac.m365-bff-performance-completion-manifest/v1"',
            '"final_evidence_json_sha256"',
            '"final_evidence_markdown_sha256"',
            "_render_final_markdown",
            '"tenant_wide_sharepoint_request_allowance_claim"',
            '"tenant_wide_sharepoint_resource_unit_allowance_claim"',
            '"monetary_cost_claim"',
            '"tenant_wide_sharepoint_baseline_claim"',
            '"- Tenant-wide SharePoint baseline: `NOT_CLAIMED`"',
            '"- Tenant-wide SharePoint request allowance: `NOT_CLAIMED`"',
            '"- Tenant-wide SharePoint resource-unit allowance: `NOT_CLAIMED`"',
            '"- Monetary cost: `NOT_CLAIMED`"',
        ),
        COMPOSITION: (
            "validate_azure_performance_composition_readiness",
            "run_azure_performance_acceptance_live",
            '"production_composition_constructed": True',
            "missing_ports",
            '"network_calls": 0',
            '"azure_calls": 0',
            '"tenant_writes": 0',
            "_prepare_performance_infrastructure",
            "reconcile_successful_deployment",
            "persist_original_name_available",
            "persist_successful_deployment",
        ),
        OWNER_GATE: (
            "ACTION = OWNER_ACTION",
            "approved_commit_sha",
            "approved_tree_sha",
            "toolchain_attestations_sha256",
            "calculate_toolchain_attestations_sha256",
            "measure_performance_infrastructure_approval",
            "infrastructure_binding_sha256",
            "infrastructure_safety_policy_sha256",
            "worm_baseline_binding_sha256",
            "worm_baseline_compiled_arm_sha256",
            "worm_baseline_parameters_sha256",
            "worm_baseline_source_sha256",
            "deployment_sequence_sha256",
            '"bffStorageAccountResourceId"',
            '"wormStorageAccountResourceId"',
            '"resourceGroupName"',
            '"deploymentMode"',
            '"tags"',
            "build_activation_attestation_plan",
            "network_accessed",
        ),
        INFRASTRUCTURE_PORTS: (
            "class OwnerBoundInfrastructureDeploymentAuthority",
            "class UnlockedWormBaselineDeploymentPort",
            "class UnlockedWormBaselineReadbackPort",
            "class PerformanceCoordinationDeploymentPort",
            "class AzureCliPerformanceInfrastructureCommandExecutor",
            "RESTART_RECONCILIATION_SEQUENCE",
        ),
        INFRA_SAFETY: (
            "def infrastructure_safety_policy_sha256(",
            "def validate_infrastructure_safety_evidence(",
            "infrastructure_safety_evidence_sha256",
            "immutable-original-available-or-read-only-exact-success-reconciliation",
            "class AzurePerformanceInfrastructureRestartReceiptStore",
            "original_observed_lt_started_lte_completed_lt_reconciliation_observed",
            "postdeployment_coordination_resource_readback_required",
            "BROADER_EFFECTIVE_CONTROL_PLANE_ASSIGNMENT_PRESENT",
            "canonical_observation_command_sha256",
            "authoritative_bff_storage_account_resource_id",
            "effective_role_assignments",
            "broader_effective_data_assignment_allowed",
            "EXPECTED_EFFECTIVE_ASSIGNMENT_NOT_UNIQUE",
        ),
        AZURE_COMMANDS: (
            "from nac_bff.azure_performance_monitor import is_metrics_url",
            "is_metrics_url(options[\"--url\"][0])",
            "is_metrics_url(values[0])",
            "def run_monitor_metrics(",
            "_MONITOR_EXECUTION_AUTHORITY",
        ),
        INFRA: (
            "defaultAction: 'Deny'",
            "allowSharedKeyAccess: false",
            "param tenantId string",
            "param subscriptionId string",
            "param resourceGroupName string",
            "param brokerPrincipalId string",
            "param brokerCallerServicePrincipalId string",
            "param brokerFunctionAppResourceId string",
            "param brokerFunctionPackageSha256 string",
            "param brokerTicketVerificationCertificateSha256 string",
            "param brokerOutboundIpAddresses array",
            "toLower(brokerPrincipalId) != toLower(brokerCallerServicePrincipalId)",
            "output brokerCallerServicePrincipalIdBinding string",
            "output localRunnerStorageDataActions array = []",
            "output credentialBoundaryMode string = 'BFF_BROKER_UAMI_ONLY'",
            "containers/blobs:path] StringEquals",
            "blobBootstrapRequired bool = true",
            "param bffStorageAccountResourceId string",
            "param wormStorageAccountResourceId string",
            "validatedBffStorageAccountResourceId",
            "validatedWormStorageAccountResourceId",
        ),
        WORM_INFRA: (
            "param tenantId string",
            "param subscriptionId string",
            "param resourceGroupName string",
            "param deploymentMode string",
            "param storageAccountName string",
            "param containerName string",
            "param encryptionScopeName string",
            "output lockActionStatus string = 'OWNER_GATED_NOT_EXECUTED'",
        ),
        INFRA_ARM_VALIDATOR: (
            '"bffStorageAccountResourceId"',
            '"wormStorageAccountResourceId"',
            "EXPECTED_RESOURCE_TYPES",
            "validate_template",
        ),
        QUALITY_GATE_WORKFLOW: (
            "az bicep install --version v0.45.15",
            '"$HOME/.azure/bin/bicep" build',
            "DOTNET_BUNDLE_EXTRACT_BASE_DIR",
            "nac-bff-performance-coordination/main.bicep",
            "validate_nac_bff_performance_coordination_arm.py",
        ),
    }
    for path, fragments in required_fragments.items():
        _require_fragments(path, texts.get(path, ""), fragments, errors)

    focused = _mapping(verification.get("focused_test_names"))
    for key, path in (
        ("authorization", AUTHORIZATION_TESTS),
        ("acceptance", TESTS),
        ("monitor", MONITOR_TESTS),
        ("runtime", RUNTIME_TESTS),
        ("composition", COMPOSITION_TESTS),
        ("owner_gate", OWNER_GATE_TESTS),
        ("infrastructure_safety", INFRA_SAFETY_TESTS),
        ("infrastructure_ports", INFRASTRUCTURE_PORT_TESTS),
        ("command_boundary", AZURE_COMMAND_TESTS),
        ("cli", CLI_TESTS),
    ):
        names = focused.get(key)
        if not isinstance(names, list) or not names:
            errors.append(f"verification focused_test_names.{key} must not be empty")
            continue
        _require_fragments(path, texts.get(path, ""), names, errors)

    broker_focused_tests = {
        LEASE_BROKER_TESTS: (
            "test_valid_ticket_is_verified_over_canonical_payload",
            "test_owner_role_and_scope_are_bound_on_server_and_in_trusted_claims",
            "test_request_facing_methods_have_no_storage_or_http_controls",
            "test_crash_and_retry_outcomes_have_explicit_directives",
            "test_concurrent_replay_creates_exactly_one_lease",
        ),
        LEASE_BROKER_STORAGE_TESTS: (
            "test_adapter_implements_port_and_exposes_only_broker_commands",
            "test_acquire_persists_exact_intent_before_one_lease_acquire",
            "test_acquire_crash_points_are_conservative_and_reconcilable",
            "test_release_crash_points_reconcile_without_unknown_lease_ids",
            "test_token_scope_is_fixed_and_failures_are_redacted",
        ),
        LEASE_BROKER_AUTH_TESTS: (
            "test_token_provider_requests_only_fixed_bff_scope",
            "test_local_credential_validation_is_redacted",
            "test_private_key_must_not_be_group_or_world_readable",
            "test_ticket_is_single_operation_short_lived_and_verifiable",
            "test_ticket_tampering_breaks_signature",
        ),
        LEASE_BROKER_CLIENT_TESTS: (
            "test_only_fixed_broker_routes_are_called_and_local_id_is_not_sent",
            "test_request_surface_has_no_storage_controls",
            "test_execution_fence_rejects_concurrent_local_runs",
            "test_configuration_is_https_fixed_root_and_digest_bound",
        ),
        LEASE_BROKER_COMPOSITION_TESTS: (
            "test_settings_and_composition_bind_exact_server_side_boundary",
            "test_disabled_missing_and_noncanonical_values_fail_generically",
        ),
        LEASE_BROKER_FASTAPI_TESTS: (
            "test_fixed_routes_accept_only_exact_ticket_envelope",
            "test_invalid_shapes_and_provider_errors_are_generic",
            "test_unknown_operation_and_oversized_body_are_rejected",
        ),
        INFRA_TESTS: (
            "test_source_binds_non_exportable_broker_identity_and_package",
            "test_source_role_is_exclusive_to_the_broker_uami",
            "test_source_assignment_binds_only_broker_uami_to_exact_path",
            "test_compiled_parameter_contract_binds_broker_boundary",
            "test_compiled_outputs_are_unambiguous_for_broker_boundary",
        ),
    }
    for path, names in broker_focused_tests.items():
        _require_fragments(path, texts.get(path, ""), names, errors)

    local_auth = texts.get(LEASE_BROKER_AUTH, "")
    local_client = texts.get(LEASE_BROKER_CLIENT, "")
    for forbidden in (
        "https://storage.azure.com/.default",
        "Microsoft.Storage/storageAccounts/blobServices/containers/blobs/",
    ):
        if forbidden in local_auth or forbidden in local_client:
            errors.append(
                "local broker auth/client must contain no Storage scope or DataAction"
            )

    doc_fragments = (
        "Issue #735",
        "endpoint_scoped_conservative_measurement",
        "NOT_CLAIMED",
        "500",
        "1, 1, 90, 120, 288",
        "10, 60, 300",
        "30,000 GB-s",
        "120,000 GB-s",
        "2048",
        "monitor_window_anchor",
        "ACQUIRE_INTENT",
        "ACQUIRE_IN_FLIGHT",
        "RELEASED",
        "rg-nac-bff-test",
        "Incremental",
        "pending-finalization",
        "measurement_finished_at_utc",
        "projected_remaining_execution_units_gb_seconds",
        "exact `RELEASED`",
        "target binding",
        "TOCTOU",
        "terminal",
        "Markdown",
        "completion-manifest",
        "nameAvailable=true",
        "Succeeded",
        "original observed < started <= completed < current reconciliation observed",
    )
    for path in (DOC_DE, DOC_EN):
        content = texts.get(path, "")
        _require_fragments(path, content, doc_fragments, errors)
        _require_fragments(
            path,
            content,
            (
                "app-weite",
                "Resource-IDs",
                "effektive RBAC",
                "versiegeltes Ergebnis",
                "monetary cost: NOT_CLAIMED",
            )
            if path == DOC_DE
            else (
                "app-wide",
                "resource IDs",
                "Effective RBAC",
                "sealed result",
                "monetary cost: NOT_CLAIMED",
            ),
            errors,
        )
        for stale in ("Issue #731", "issues/731", "50,000", "50.000"):
            if stale in content:
                errors.append(f"{path} retains stale #731/50000 claim: {stale}")

    _require_fragments(
        CONTRACT_INDEX,
        texts.get(CONTRACT_INDEX, ""),
        (
            "exakt 500 synthetische",
            "Resource-Unit-Allowance jeweils `NOT_CLAIMED`",
        ),
        errors,
    )

    design_doc_fragments = (
        "500",
        "NOT_CLAIMED",
        "tenant_wide_sharepoint_baseline_claim: NOT_CLAIMED",
        "tenant_wide_sharepoint_request_allowance_claim: NOT_CLAIMED",
        "tenant_wide_sharepoint_resource_unit_allowance_claim: NOT_CLAIMED",
        "monetary_cost_claim: NOT_CLAIMED",
        "RELEASED",
        "target_binding_sha256",
        "projected",
        "settlement",
        "TOCTOU",
        "pending-finalization",
    )
    for path in (PLAN_DE, SPEC_DE, PLAN_EN, SPEC_EN):
        visible = _visible_markdown(texts.get(path, ""))
        _require_fragments(path, visible, design_doc_fragments, errors)
        _require_fragments(
            path,
            visible,
            ("Manifest", "Resource")
            if path in (PLAN_DE, SPEC_DE)
            else ("manifest", "resource"),
            errors,
        )

    owned_text = "\n".join(
        (REPO_ROOT / path).read_text(encoding="utf-8")
        for path in (
            CONTRACT,
            VERIFICATION,
            CONTRACT_INDEX,
            DOC_DE,
            DOC_EN,
            PLAN_DE,
            SPEC_DE,
            PLAN_EN,
            SPEC_EN,
        )
    )
    for stale in ("issues/731", "AC-731-", "50000", "50,000", "50.000"):
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
