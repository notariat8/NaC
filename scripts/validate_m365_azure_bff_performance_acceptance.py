from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = Path(
    "workflows/contracts/m365-bff-performance-acceptance.contract.json"
)
VERIFICATION = Path(
    "workflows/verification-contracts/"
    "m365-bff-performance-acceptance.verification.json"
)
IMPLEMENTATION = Path("src/nac_bff/azure_performance_acceptance.py")
ACTIVATION_COMPOSITION = Path("src/nac_bff/azure_activation_composition.py")
FASTAPI_ADAPTER = Path("src/nac_bff/fastapi_adapter.py")
WORKBENCH_PROJECTION = Path("src/nac_bff/workbench_projection.py")
M365_RUNNER = Path("src/nac_m365_graph/mvp_test_environment_deploy.py")
CLI = Path("src/nac_cli/cli.py")
TESTS = Path("tests/test_nac_bff_azure_performance_acceptance.py")
PROJECTION_TESTS = Path("tests/test_nac_bff_workbench_projection.py")
ENDPOINT_TESTS = Path("tests/test_nac_bff_workbench_endpoint.py")
ISSUE = "https://github.com/notariat8/NaC/issues/731"


def _json(path: Path) -> dict[str, object]:
    value = json.loads((REPO_ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain one JSON object")
    return value


def main() -> int:
    errors: list[str] = []
    try:
        contract = _json(CONTRACT)
        verification = _json(VERIFICATION)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1

    texts: dict[Path, str] = {}
    for path in (
        IMPLEMENTATION,
        ACTIVATION_COMPOSITION,
        FASTAPI_ADAPTER,
        WORKBENCH_PROJECTION,
        M365_RUNNER,
        CLI,
        TESTS,
        PROJECTION_TESTS,
        ENDPOINT_TESTS,
    ):
        try:
            texts[path] = (REPO_ROOT / path).read_text(encoding="utf-8")
        except OSError:
            errors.append(f"missing required artifact: {path}")

    if contract.get("leading_issue") != ISSUE:
        errors.append("domain contract must bind Issue #731")
    if contract.get("contract_id") != "m365.bff_performance_acceptance":
        errors.append("domain contract ID must match the runtime contract ID")
    if verification.get("leading_issue") != ISSUE:
        errors.append("verification contract must bind Issue #731")
    dispatch = contract.get("global_dispatch_budget")
    if not isinstance(dispatch, dict) or dispatch.get(
        "target_dispatch_ceiling_exact_inclusive"
    ) != 50_000:
        errors.append("global dispatch ceiling must be exactly 50000")
    capacity = contract.get("tenant_capacity_preflight")
    if not isinstance(capacity, dict) or capacity.get(
        "authoritative_tenant_sharepoint_tier_evidence_required"
    ) is not True:
        errors.append("authoritative SharePoint capacity preflight is required")
    azure = contract.get("azure_execution_preflight")
    if not isinstance(azure, dict) or azure.get(
        "execution_unit_cap_inclusive"
    ) != 120_000:
        errors.append("Azure execution-unit cap must be 120000 GB-s")
    if not isinstance(azure, dict) or azure.get(
        "observed_plus_projected_remaining_execution_units_must_not_exceed_cap"
    ) is not True:
        errors.append("Azure budget must include projected remaining execution units")
    if not isinstance(azure, dict) or azure.get(
        "azure_monitor_evidence_sha256_separate_from_sharepoint_capacity_source"
    ) is not True:
        errors.append("Azure Monitor and SharePoint capacity evidence must be distinct")
    owner_gate = contract.get("activation_and_owner_gate")
    expected_owner_fields = {
        "action",
        "contract_sha256",
        "expected_activation_hash",
        "target_binding_sha256",
        "capacity_preflight_sha256",
        "phase_plan_sha256",
        "correlation_id",
        "required_owner_login",
    }
    if not isinstance(owner_gate, dict) or set(
        owner_gate.get("owner_approval_binding_fields_exact", [])
    ) != expected_owner_fields:
        errors.append("owner approval binding fields are incomplete")
    phases = contract.get("phases")
    expected_phases = [
        ("cold_epoch_baseline", 1),
        ("cold_epoch_candidate", 1),
        ("capacity_bounded_volume", 37_758),
        ("sustained_2h", 10_800),
        ("soak_24h", 1_440),
    ]
    actual_phases = []
    if isinstance(phases, list):
        for phase in phases:
            if isinstance(phase, dict):
                allocation = phase.get(
                    "target_dispatch_allocation_exact",
                    phase.get("target_dispatch_allocation_maximum"),
                )
                actual_phases.append((phase.get("id"), allocation))
    if actual_phases != expected_phases:
        errors.append("phase order and dispatch allocations must total exactly 50000")
    request_policy = contract.get("request_and_response_policy")
    if (
        not isinstance(request_policy, dict)
        or request_policy.get("maximum_wire_bytes") != 128 * 1024
        or request_policy.get("maximum_error_rate") != 0.0
        or request_policy.get("connection_timeout_seconds") != 10
        or request_policy.get("request_timeout_seconds") != 30
        or request_policy.get("timeouts_are_fixed_and_not_runtime_overridable")
        is not True
    ):
        errors.append("response and zero-error boundaries are invalid")
    pass_condition = contract.get("pass_condition")
    if not isinstance(pass_condition, dict) or pass_condition.get(
        "all_response_sizes_at_or_below_128_kib"
    ) is not True:
        errors.append("pass condition must enforce the 128 KiB response ceiling")
    if not isinstance(pass_condition, dict) or pass_condition.get(
        "global_dispatch_count_exactly_50000"
    ) is not True:
        errors.append("PASSED evidence must require exactly 50000 dispatches")

    required_fragments = {
        IMPLEMENTATION: (
            "_GLOBAL_REQUEST_LIMIT = 50_000",
            "_MAX_EXECUTION_UNITS_GB_SECONDS = 120_000.0",
            "PERFORMANCE_CAPACITY_PREFLIGHT_BLOCKED",
            "PerformanceExecutionAuthorization",
            "PERFORMANCE_DURABLE_CHECKPOINT_FAILED",
            "PERFORMANCE_STATE_INVALID",
            "PERFORMANCE_TARGET_BINDING_MISMATCH",
            "PERFORMANCE_EVIDENCE_REDACTION_INVALID",
            'claims.get("aud") != API_APP_URI',
            'CONTRACT_ID = "m365.bff_performance_acceptance"',
            "reserved_attempt_count",
            "owner_approval_body_sha256",
            "approved_capacity_preflight_sha256",
            "final_checkpoint_sha256",
            "fatal_code",
            "_refresh_capacity",
            "PERFORMANCE_ACTIVATION_TARGET_MISMATCH",
            "_PerformancePreDispatchAbort",
            "safety_check_pending",
            "PREDISPATCH_SAFETY_OUTCOME_UNKNOWN",
            "PERFORMANCE_EXECUTION_UNIT_BUDGET_EXHAUSTED",
            "_CONNECT_TIMEOUT_SECONDS = 10.0",
            "_REQUEST_TIMEOUT_SECONDS = 30.0",
            "_validate_evidence_state_binding",
            "nac.performance-checkpoint-commit/v1",
            "_terminalize_interrupted_resume",
            "PERFORMANCE_CONTRACT_BINDING_MISMATCH",
            '"global_dispatch_count"',
            '"phase_aggregate_metrics"',
            "INFLIGHT_DISPATCH_OUTCOME_UNKNOWN",
            "/workbench-snapshot?purpose=",
            '"VERIFIED" if epoch_changed else "INCONCLUSIVE"',
            "INCONCLUSIVE",
        ),
        ACTIVATION_COMPOSITION: (
            "_PERFORMANCE_ACCEPTANCE_COMMENT_RE",
            "verify_performance_owner_comment",
            "issues/731",
        ),
        FASTAPI_ADAPTER: (
            'response.headers["X-NaC-Instance-Epoch"] = _INSTANCE_EPOCH',
            "_should_emit_instance_epoch",
        ),
        WORKBENCH_PROJECTION: (
            "def validate_workbench_projection(",
            "snapshot canonical projection mismatch",
        ),
        M365_RUNNER: (
            '"accesstoken"',
            '_EXPECTED_API_RESOURCE,',
        ),
        CLI: (
            "bff-performance-acceptance-plan",
            "PERFORMANCE_PLAN_BINDING_INVALID",
        ),
        TESTS: (
            "test_inflight_attempt_is_not_replayed_after_crash",
            "test_fatal_checkpoint_is_terminalized_without_redispatch_after_crash",
            "test_capacity_attestation_is_refreshed_and_stale_evidence_blocks_dispatch",
            "test_post_dispatch_monitor_failure_is_terminalized",
            "test_passed_readback_checkpoints_refreshed_capacity_before_evidence",
            "test_passed_evidence_requires_the_exact_50000_request_phase_plan",
            "test_authorization_rejects_activation_for_another_fixed_target",
            "test_capacity_preflight_fails_closed",
            "test_cold_start_is_inconclusive_without_epoch_change",
            "test_activation_receipt_must_bind_actual_committed_artifacts",
            "test_fixed_transport_binding_requires_production_transport_type",
            "test_owner_and_activation_are_verified_before_authorization",
            "test_github_verifier_accepts_only_immutable_issue_731_comment",
            "test_runner_requires_checkpoint_authorization_and_target_binding",
            "test_corrupt_passed_resume_state_is_rejected_before_network",
            "test_persisted_passed_state_must_still_meet_phase_thresholds",
            "test_idle_resume_repeats_full_idle_observation",
            "test_runtime_monitor_failure_blocks_before_transport",
            "test_runtime_execution_unit_cap_blocks_before_transport",
            "test_runtime_execution_unit_budget_includes_remaining_dispatches",
            "test_pending_safety_check_is_restart_terminal_without_dispatch",
            "test_fixed_transport_enforces_connect_and_total_request_deadlines",
            "test_refreshed_capacity_cannot_lower_projected_execution_budget",
            "test_canonical_passed_phase_rejects_false_latency_idle_and_duration",
            "test_checkpoint_commit_pointer_survives_mirror_write_interruption",
            "test_checkpoint_orphan_slot_does_not_replace_committed_state",
            "test_checkpoint_slot_interruption_keeps_previous_commit",
            "test_checkpoint_digest_mirror_interruption_keeps_new_commit",
            "test_authorization_rejects_non_repository_contract_digest",
            "test_artifact_store_rejects_checkpoint_consistent_false_passed_metrics",
            "test_fixed_transport_real_alarm_and_redirect_rejection",
            "test_nested_secret_shaped_error_is_redacted_before_evidence",
            "test_checkpoint_store_detects_state_digest_mismatch",
            "test_delegated_token_must_target_exact_bff_audience",
            "test_cli_emits_offline_plan_without_network",
        ),
        PROJECTION_TESTS: (
            "test_builds_explicit_server_authored_projection",
            "test_wire_validator_rejects_missing_nested_and_unknown_fields",
        ),
        ENDPOINT_TESTS: (
            "test_instance_epoch_is_scoped_to_successful_workbench_response",
        ),
    }
    for path, fragments in required_fragments.items():
        content = texts.get(path, "")
        for fragment in fragments:
            if fragment not in content:
                errors.append(f"{path} missing required fragment: {fragment}")

    checks = verification.get("checks")
    expected_test = (
        "PYTHONPATH=src python3 -m unittest "
        "tests.test_nac_bff_azure_performance_acceptance "
        "tests.test_nac_bff_workbench_projection "
        "tests.test_nac_bff_workbench_endpoint"
    )
    if not isinstance(checks, list) or expected_test not in checks:
        errors.append("verification contract must execute focused runtime tests")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("M365 Azure BFF performance acceptance validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
