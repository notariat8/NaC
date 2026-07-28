from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DOMAIN_PATH = Path("workflows/contracts/m365-azure-bff-live-activation.contract.json")
VERIFICATION_PATH = Path(
    "workflows/verification-contracts/"
    "m365-azure-bff-live-activation.verification.contract.yaml"
)
ACTIVATION_PLAN_PATH = Path("src/nac_bff/azure_activation.py")
RUNNER_PATH = Path("src/nac_bff/azure_activation_runner.py")
COMPOSITION_PATH = Path("src/nac_bff/azure_activation_composition.py")
GRAPH_ACTIVATION_PATH = Path("src/nac_bff/graph_activation.py")
GRAPH_ACTIVATION_TEST_PATH = Path("tests/test_nac_bff_graph_activation.py")
ATTESTATION_PATH = Path("src/nac_bff/azure_activation_attestations.py")
APPROVAL_PATH = Path("src/nac_bff/azure_activation_approval.py")
OWNER_GATE_PATH = Path("src/nac_bff/azure_activation_owner_gate.py")
PROVISIONER_BOOTSTRAP_PATH = Path(
    "src/nac_bff/azure_activation_provisioner_bootstrap.py"
)
PROVISIONER_ENV_BOOTSTRAP_PATH = Path(
    "src/nac_m365_graph/provisioner_env_bootstrap.py"
)
PROVISIONER_BOOTSTRAP_TEST_PATH = Path(
    "tests/test_nac_bff_azure_activation_provisioner_bootstrap.py"
)
CLI_PATH = Path("src/nac_cli/cli.py")
M365_RUNNER_PATH = Path("src/nac_m365_graph/mvp_test_environment_deploy.py")
SEALED_TOOLCHAIN_PATH = Path("src/nac_m365_graph/sealed_toolchain.py")
NODE_RUNTIME_INTEGRITY_PATH = Path(
    "src/nac_m365_graph/node_runtime_integrity.py"
)
AZURE_CLI_SEALED_RUNTIME_PATH = Path(
    "src/nac_bff/azure_cli_sealed_runtime.py"
)
AZURE_LIVE_COMMANDS_PATH = Path("src/nac_bff/azure_live_commands.py")
BFF_TEST_ENVIRONMENT_PATH = Path("src/nac_bff/test_environment.py")
README_PATH = Path("workflows/contracts/README.md")
QUALITY_GATE_PATH = Path("scripts/quality_gate.py")

LEADING_ISSUE = "https://github.com/notariat8/NaC/issues/632"
PARENT_ISSUE = "https://github.com/notariat8/NaC/issues/620"
PROVISIONER_BOOTSTRAP_ISSUE = "https://github.com/notariat8/NaC/issues/666"
SITE_PERMISSION_BOUNDARY_ISSUE = "https://github.com/notariat8/NaC/issues/671"
SITE_PERMISSION_BOUNDARY_ACCEPTANCE_IDS = [
    f"AC-{index:03d}" for index in range(1, 7)
]
PROVISIONER_GRAPH_APPLICATION_ROLES = [
    "Application.Read.All",
    "Application.ReadWrite.OwnedBy",
    "AppRoleAssignment.ReadWrite.All",
    "Team.Create",
    "Sites.Manage.All",
    "Sites.FullControl.All",
]
PROVISIONER_GRAPH_APPLICATION_ROLE_INVENTORY = {
    "application_client_id_exact": "6845f6c3-896c-4e44-a50f-2a5086a13fac",
    "roles_exact": PROVISIONER_GRAPH_APPLICATION_ROLES,
    "phase_exact": "after_target_site_identity_check_before_any_provider_write",
    "provider_writes_before_inventory_exact": 0,
    "missing_or_broader_or_duplicate_behavior_exact": (
        "PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH"
    ),
    "raw_graph_identifiers_emitted_allowed": False,
}
SITE_PERMISSION_ADMINISTRATION = {
    "provisioner_display_name_exact": "NaC M365 Provisioning",
    "required_application_permission_exact": "Sites.FullControl.All",
    "graph_methods_exact": ["GET", "POST"],
    "graph_path_template_exact": "/sites/{siteId}/permissions",
    "owner_gate_required": True,
    "runtime_identity_allowed": False,
    "missing_permission_behavior": "stop_before_live_retry",
}
SITE_PERMISSION_ADMIN_CAPABILITY = {
    "identity_exact": "NaC M365 Provisioning",
    "operation_exact": "GET /sites/{siteId}/permissions",
    "site_id_exact": (
        "funktion8.sharepoint.com,31324d31-3074-4f1c-ba45-3b3fd5f5ce97,"
        "56fc9349-e123-4252-ae2a-05d5d61c9b38"
    ),
    "phase_exact": "after_target_site_identity_check_before_any_provider_write",
    "provider_writes_before_probe_exact": 0,
    "required_result_exact": "available",
    "failure_code_exact": "SITE_PERMISSION_ADMIN_CAPABILITY_UNAVAILABLE",
    "raw_graph_error_or_identifier_emission_allowed": False,
}
PROVISIONER_BOOTSTRAP_ACCEPTANCE_IDS = [
    f"AC-666-{index:02d}" for index in range(1, 7)
]
SAFETY_REWORK_ISSUE = "https://github.com/notariat8/NaC/issues/658"
AZURE_INVENTORY_SAFETY_REWORK_ISSUE = "https://github.com/notariat8/NaC/issues/662"
OWNER_GATE_SAFETY_REWORK_ISSUE = "https://github.com/notariat8/NaC/issues/664"
OWNER_GATE_SAFETY_REWORK_ACCEPTANCE_IDS = [
    f"AC-664-{index:02d}" for index in range(1, 7)
]
PROVISIONER_BOOTSTRAP_VERIFICATION = {
    "owner_gate_flags_exact": [
        "--bff-provisioner-state",
        "--bff-attestation-provisioner-certificate",
        "--bff-provisioner-private-key",
    ],
    "live_flags_exact": [
        "--provisioner-bootstrap-binding-sha256",
        "--provisioner-state",
        "--provisioner-certificate-path",
        "--provisioner-private-key-path",
    ],
    "recovery_flags_exact": [
        "--provisioner-bootstrap-binding-sha256",
    ],
    "all_paths_absolute_and_metadata_trusted": True,
    "state_tenant_and_provisioner_app_binding_exact": True,
    "state_site_permission_assignment_exact": {
        "permission": "Sites.FullControl.All",
        "status_values_allowed": ["created", "existing"],
        "assignment_count_exact": 1,
        "missing_behavior": (
            "PROVISIONER_SITE_PERMISSION_GRAPH_ROLE_MISSING_before_live_"
            "factory_provider_access_or_tenant_write"
        ),
        "all_provisioner_permissions_exact": PROVISIONER_GRAPH_APPLICATION_ROLES,
        "all_assignment_status_values_allowed": ["created", "existing"],
        "all_assignment_count_exact": 6,
        "broader_or_duplicate_behavior": (
            "PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH_before_live_factory_"
            "provider_access_or_tenant_write"
        ),
    },
    "binding_field_exact": "provisioner_bootstrap_binding_sha256",
    "binding_pattern": "^[0-9a-f]{64}$",
    "state_read_mode_exact": (
        "single_O_NOFOLLOW_CLOEXEC_descriptor_with_pre_open_and_"
        "post_read_fstat_snapshot"
    ),
    "state_maximum_bytes_exact": 131072,
    "binding_inputs_exact": [
        "state_sha256_from_atomically_read_bytes",
        "state_path_sha256",
        "certificate_path_sha256",
        "private_key_path_sha256",
        "tenant_id",
        "provisioner_client_id",
        "graph_base_url",
    ],
    "owner_payload_live_and_recovery_value_must_match_exactly": True,
    "owner_gate_live_cli_arguments_flag_exact": (
        "--provisioner-bootstrap-binding-sha256"
    ),
    "binding_mismatch_behavior_exact": (
        "PROVISIONER_BOOTSTRAP_BINDING_MISMATCH_before_live_factory_"
        "provider_access_or_tenant_write"
    ),
    "graph_v1_only": True,
    "certificate_mode_only": True,
    "private_key_content_reads_exact": 0,
    "provider_requests_before_bootstrap_pass_exact": 0,
    "tenant_writes_before_bootstrap_pass_exact": 0,
    "global_process_environment_mutation_allowed": False,
    "effective_environment_passed_explicitly_to_live_factory": True,
    "readiness_redacted_fields_exact": [
        "tenant_id_emitted",
        "client_id_emitted",
        "credential_paths_emitted",
        "credential_values_emitted",
    ],
    "readiness_redacted_field_values_exact": False,
    "blocked_error_prefix_exact": "PROVISIONER_",
}
AZURE_APPLICATION_INSIGHTS_COMPANION_POLICY = {
    "safety_rework_issue": AZURE_INVENTORY_SAFETY_REWORK_ISSUE,
    "type_case_insensitive": "Microsoft.Insights/ActionGroups",
    "name_exact": "Application Insights Smart Detection",
    "location_case_insensitive": "Global",
    "group_short_name_exact": "SmartDetect",
    "enabled_exact": True,
    "arm_role_receivers_count_exact": 2,
    "arm_role_receivers_exact": [
        {
            "name": "Monitoring Contributor",
            "roleId": "749f88d5-cbae-40b8-bcfc-e573ddc772fa",
            "useCommonAlertSchema": True,
        },
        {
            "name": "Monitoring Reader",
            "roleId": "43d0d8ad-25c7-4714-9337-8ba259a9fe05",
            "useCommonAlertSchema": True,
        },
    ],
    "all_other_receiver_counts_exact": 0,
    "detail_read_mode": "exact_argument_bound_azure_resource_show",
    "detail_read_api_version_exact": "2021-09-01",
    "subscription_id_exact": "37cd9645-6cb9-4278-88ee-e80377cd951c",
    "resource_group_exact": "rg-nac-bff-test",
    "arm_resource_id_exact": (
        "/subscriptions/37cd9645-6cb9-4278-88ee-e80377cd951c/"
        "resourceGroups/rg-nac-bff-test/providers/Microsoft.Insights/"
        "actionGroups/Application Insights Smart Detection"
    ),
    "identity_list_reads_when_present_exact": 2,
    "detail_reads_when_present_exact": 1,
    "identity_stability_required": True,
    "inventory_change_error_exact": (
        "AZURE_RESOURCE_INVENTORY_CHANGED_DURING_READBACK"
    ),
    "adapter_failure_error_exact": "AZURE_SMART_DETECTION_READBACK_FAILED",
    "arbitrary_action_groups_allowed": False,
    "property_drift_behavior": "stop_before_first_write",
}
SMART_DETECTION_PREWRITE_AST_SHA256 = (
    "e93de690c423333f0ca41a12906cb02f43974999f33f7db3ca80dfeb9bb982ac"
)
AZURE_COMMAND_SCHEMAS_AST_SHA256 = (
    "6744d3273b552c19a04c6f2999f3b7f990d8b44e4df303747692f598b8af1b30"
)
SMART_DETECTION_FUNCTION_AST_SHA256 = {
    "_validate_smart_detection_action_group_identity": (
        "437a9a23c85e2a451d6e86f7fe52518eb2ec421cfb7b864276a12ce0fe8b5c32"
    ),
    "_validate_smart_detection_action_group": (
        "adcbc7718151e08fdce6f05f862f377e01614999d107687f3b4b55423ae3960b"
    ),
}
SAFETY_REWORK_ACCEPTANCE_IDS = [f"AC-{index:03d}" for index in range(1, 7)]
AZURE_CLI_SEALED_RUNTIME_SOURCE_SHA256 = (
    "675b346d76b6554d8887a6182cb7ae6b0bc5b99e147f29c5a96ced69ccd988ae"
)
AZURE_CLI_SEALED_BOOTSTRAP_SOURCE_SHA256 = (
    "f524792afe964a24669e34c08fd741e5e6ee783834cf8b6b81dc38b724981f59"
)
AZURE_CLI_SEALED_CHILD_STREAM_PREFIX_AST_SHA256 = (
    "0b08d14a37c20fb2253638d4b4be017d58bf35fd61065b704e465b8a47ea66a1"
)
ACCEPTANCE_IDS = [f"AC-632-{index:02d}" for index in range(1, 9)]
TOP_LEVEL_FIELDS = [
    "schema_version", "status", "started_at_utc", "finished_at_utc",
    "activation_hash", "approved_commit_sha", "approved_tree_sha",
    "approval_reference_sha256", "provisioner_bootstrap_binding_sha256",
    "toolchain_attestations_sha256",
    "target_binding_sha256",
    "permission_boundary_sha256", "ledger_head_sha256", "step_results", "summary",
]
APPROVAL_FIELDS = [
    "owner-approved", "expected_activation_sha256",
    "approved_commit_sha", "approved_tree_sha",
    "provisioner_bootstrap_binding_sha256",
    "target_binding_sha256", "permission_boundary_sha256",
    "step_sequence_sha256", "toolchain_attestations_sha256",
    "no_automatic_rollback_or_deletion",
]
LIVE_REQUIRED_ARGUMENTS = [
    "--owner-approved",
    "--execute-live-activation",
    "--expected-activation-hash <64-lowercase-hex>",
    "--approval-reference <immutable-github-issue-comment-url>",
    "--approval-body-sha256 <64-lowercase-hex>",
    "--approved-commit <40-lowercase-hex>",
    "--approved-tree <40-lowercase-hex>",
    "--azure-cli-toolchain-sha256 <64-lowercase-hex>",
    "--m365-cli-sha256 <64-lowercase-hex>",
    "--m365-node-sha256 <64-lowercase-hex>",
    "--build-python-sha256 <64-lowercase-hex>",
    "--build-node-sha256 <64-lowercase-hex>",
    "--build-npm-cli-sha256 <64-lowercase-hex>",
    "--gh-cli-sha256 <64-lowercase-hex>",
    "--provisioner-certificate-sha256 <64-lowercase-hex>",
    "--provisioner-bootstrap-binding-sha256 <64-lowercase-hex>",
    "--provisioner-state <absolute-state-path>",
    "--provisioner-certificate-path <absolute-public-certificate-path>",
    "--provisioner-private-key-path <absolute-private-key-path>",
    "--reason <non-empty-owner-reason>",
    "--correlation-id <safe-correlation-id>",
]
OWNER_ASSOCIATIONS = ["OWNER", "MEMBER"]
PROVIDER_READBACK_POLICY = {
    "attempts": 5,
    "delay_seconds": 12.0,
    "maximum_elapsed_seconds": 60.0,
    "operation": "provider show",
    "deadline_clock": "time.monotonic",
    "per_call_timeout": "remaining_deadline_seconds",
    "allowed_states": ["Registered", "Registering", "NotRegistered"],
    "register_on_states": ["NotRegistered"],
    "poll_without_register_on_states": ["Registering"],
    "success_state": "Registered",
    "timeout_error": "AZURE_PROVIDER_NOT_REGISTERED",
    "ambiguous_state_error": "AZURE_PROVIDER_STATE_AMBIGUOUS",
    "maximum_register_writes_per_namespace": 1,
}
DEPLOYMENT_RECONCILIATION_POLICY = {
    "trigger_error_exact": "AZURE_CLI_TIMEOUT",
    "read_only_operation_exact": "deployment group show",
    "attempts": 5,
    "delay_seconds": 2.0,
    "same_deployment_correlation_id_rejected_as_stale": True,
    "terminal_success_error": (
        "AZURE_BASELINE_DEPLOYMENT_SUCCEEDED_REQUIRES_NEW_RUN"
    ),
    "terminal_failure_error": "AZURE_BASELINE_DEPLOYMENT_FAILED",
    "terminal_canceled_error": "AZURE_BASELINE_DEPLOYMENT_CANCELED",
    "unresolved_error": "AZURE_DEPLOYMENT_STATE_AMBIGUOUS",
    "unresolved_target_lock_retained": True,
    "cross_version_legacy_lock_namespace_held": True,
    "legacy_host_lock_namespace_held": True,
    "readback_failures_map_to_ambiguous": True,
    "legacy_lock_hash_ledger_bound": True,
    "reconciled_template_hash_must_equal_prepared_owner_bound_template": True,
    "continue_original_run_allowed": False,
    "automatic_replay_allowed": False,
    "automatic_rollback_or_deletion_allowed": False,
}

FAILED_BASELINE_ACCEPTANCE_POLICY = {
    "entra_binding_resolved_before_azure_read": True,
    "missing_entra_binding_rejected": True,
    "parameter_binding_exact": True,
    "readback_wrapper_shapes_allowed_exact": [
        "value_only",
        "azure_type_and_value",
    ],
    "azure_parameter_types_exact": {
        "location": "String",
        "environmentName": "String",
        "m365TenantId": "String",
        "bffApiAudience": "String",
        "bffRequiredDelegatedScope": "String",
        "functionAppName": "String",
        "maximumInstanceCount": "Int",
        "httpPerInstanceConcurrency": "Int",
        "tags": "Object",
    },
    "canonical_comparison_shape": "value_only",
    "canonical_hash_shape": "value_only",
    "unknown_wrapper_fields_rejected": True,
    "parameter_value_types_exact": True,
    "current_owner_bound_template_hash_allowed": True,
    "approved_legacy_template_hashes": ["14963684813925800234"],
}

HOST_STATE_RELATIVE_PATH = ".local/state/nac/m365-bff-live-activation"
LEGACY_HOST_STATE_RELATIVE_PATH = "nac-m365-bff-live-activation-locks"
EXCLUSIVE_LOCK_PERSISTENCE_POLICY = {
    "path_template": (
        "<effective-os-user-home>/.local/state/nac/"
        "m365-bff-live-activation/<target-binding-sha256>.lock"
    ),
    "legacy_compatibility_path_template": (
        "<effective-os-user-home>/.local/state/nac/"
        "m365-bff-live-activation/<legacy-target-binding-sha256>.lock"
    ),
    "effective_user_home_resolution_exact": (
        "pwd.getpwuid(os.geteuid()).pw_dir"
    ),
    "reboot_persistent": True,
    "temporary_primary_state_allowed": False,
    "legacy_host_namespace_path_template": (
        "<temporary-directory>/nac-m365-bff-live-activation-locks/"
        "<legacy-target-binding-sha256>.lock"
    ),
    "legacy_host_namespace_migration_lock_required": True,
    "legacy_host_namespace_temporary_migration_only": True,
    "legacy_runner_execution_after_upgrade_allowed": False,
    "both_namespaces_held_for_new_runs": True,
    "ambiguous_arm_state_retains_both_persistent_locks": True,
    "ambiguous_arm_state_retains_legacy_host_migration_lock": True,
    "acquisition": "append_only_canonical_json_lines_journal_and_nonblocking_flock",
    "marker_journal_format_exact": "canonical_compact_json_lines_one_fsynced_HELD_or_RELEASED_transition_per_record",
    "incomplete_trailing_entry_behavior": "ignore_only_when_prior_complete_valid_record_exists_then_truncate_under_flock_before_append",
    "existing_empty_or_invalid_journal_behavior": "block_fail_closed",
    "release_positions_exact": ["primary", "legacy", "legacy_host"],
    "marker_states_exact": ["HELD", "RELEASED"],
    "marker_activation_hash_bound": True,
    "persistent_lockfiles_not_unlinked": True,
    "ownership_via_flock_only": True,
    "held_marker_blocks_unattended_reacquisition": True,
    "recovery_requires_all_three_lock_markers": True,
    "committed_mixed_marker_recovery_allowed": True,
    "recovery_marker_retained_until_all_released_readback": True,
    "read_only_recovery_creates_directories": False,
    "marker_release_fault_injection_required": True,
    "recovery_release_retryable_after_partial_append": True,
    "legacy_single_object_newline_marker_recovery_supported": True,
    "legacy_held_marker_unattended_reacquisition_allowed": False,
    "terminal_failed_partial_release_marker_required": True,
    "torn_terminal_release_owner_bound_recovery_supported": True,
    "torn_terminal_release_result_exact": "TERMINAL_LOCK_RELEASE_RECOVERY_REQUIRED",
}

TOOLCHAIN_ATTESTATION_FIELDS = [
    "azure_cli_toolchain_sha256", "m365_cli_sha256",
    "m365_node_sha256", "build_python_sha256", "build_node_sha256",
    "build_npm_cli_sha256",
    "gh_cli_sha256", "provisioner_certificate_sha256",
]
STEP_FIELDS = [
    "order", "id", "status", "attempt", "classification", "http_status",
    "stable_error_code", "request_sha256", "response_sha256",
    "resource_reference_sha256",
]
SUMMARY_FIELDS = [
    "required_step_count", "passed_step_count", "failed_step_count",
    "duplicate_count", "broader_permission_count", "automatic_rollback_count",
    "automatic_deletion_count", "writes_started", "ledger_hash_chain_valid",
    "prebuilt_inputs_verified", "healthz_before_auth_passed",
    "authenticated_read_passed", "readyz_after_authenticated_read_passed",
    "synthetic_state_restored", "assigned_access_passed",
    "deputy_access_passed", "denied_access_passed",
    "tampered_access_passed", "tampered_workspace_passed",
    "tampered_matter_passed", "tampered_purpose_passed",
    "tampered_filter_passed", "resume_enabled",
]
SUMMARY_COUNT_FIELDS = [
    "required_step_count", "passed_step_count", "failed_step_count",
    "duplicate_count", "broader_permission_count", "automatic_rollback_count",
    "automatic_deletion_count",
]
PREPARED_INPUT_FIELDS = [
    "schema_version", "approved_commit_sha", "approved_tree_sha", "activation_hash",
    "approved_tree_snapshot_sha256", "bicep_snapshot_sha256", "bicep_parameters_snapshot_sha256",
    "function_package_sha256", "spfx_package_sha256", "prepared_inputs_sha256",
]
STEP_IDS = [
    "register_azure_providers", "ensure_resource_group",
    "ensure_entra_api_application", "deploy_bicep_baseline",
    "assign_sites_selected", "grant_target_site_read",
    "deploy_function_package", "build_and_deploy_spfx",
    "approve_spfx_bff_scope", "seed_synthetic_workspace",
    "run_access_and_readback_smokes", "run_idempotency_and_evidence",
]
NEGATIVE_TEST_IDS = [
    "wrong_hash", "wrong_owner_login", "wrong_owner_association",
    "toolchain_attestation_tamper",
    "dirty_tree", "wrong_target", "duplicates",
    "azure_smart_detection_companion_drift", "broader_permissions",
    "race", "secret_sentinel", "prepared_input_drift",
    "health_auth_ready_order", "synthetic_restoration_failure",
    "first_error_after_write", "arm_deployment_timeout_reconciliation",
    "function_deployment_timeout_quarantine",
    "lock_journal_torn_release",
    "lock_recovery_retry_after_torn_release",
    "invalid_existing_lock_journal", "recovery_marker_completeness",
    "provisioner_bootstrap_source_drift",
    "legacy_newline_lock_recovery",
    "terminal_failed_partial_torn_release", "resume_disabled",
]
THRESHOLDS = {
    "owner_gate_count": 1,
    "activation_hash_recomputations": 2,
    "required_steps": 12,
    "allowed_failed_steps_for_pass": 0,
    "allowed_skipped_steps_for_pass": 0,
    "allowed_concurrent_lock_holders": 1,
    "allowed_graph_application_roles": 1,
    "allowed_target_site_roles": 1,
    "allowed_duplicate_exact_resources": 0,
    "allowed_automatic_rollbacks": 0,
    "allowed_automatic_deletions": 0,
    "allowed_unknown_evidence_fields": 0,
    "allowed_secret_sentinel_matches": 0,
    "allowed_resume_requests_reaching_lock_or_provider": 0,
    "required_static_inputs_before_first_write": 3,
    "required_resolved_inputs_before_bicep_write": 4,
    "required_summary_fields": len(SUMMARY_FIELDS),
}
EXACT_BINDINGS = {
    "tenant_id": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c",
    "subscription_id": "37cd9645-6cb9-4278-88ee-e80377cd951c",
    "workspace_id": "notary_team_01",
    "site_url": "https://funktion8.sharepoint.com/sites/NaC-Notar-01",
    "site_id": (
        "funktion8.sharepoint.com,31324d31-3074-4f1c-ba45-3b3fd5f5ce97,"
        "56fc9349-e123-4252-ae2a-05d5d61c9b38"
    ),
    "team_id": "124f1b11-207d-4307-bfd1-ac0fd73aa90a",
}
EXACT_LIST_IDS = {
    "Akten": "588d4a41-f538-4f37-acfb-63ff283e0910",
    "AufgabenFristen": "720ef1d4-8496-4ecb-aa1f-5fa4568343f2",
    "Vertretungsfreigaben": "ec12d339-d9b7-45e9-be45-38dadd917746",
    "AuditJournalLite": "327181c2-e402-48e9-bcfa-1f5081b45d9c",
}
NEGATIVE_ASSERTIONS: dict[str, dict[str, Any]] = {
    "wrong_hash": {"stable_error_code": "ACTIVATION_HASH_MISMATCH"},
    "wrong_owner_login": {"stable_error_code": "APPROVAL_OWNER_MISMATCH"},
    "wrong_owner_association": {
        "stable_error_code": "APPROVAL_OWNER_MISMATCH"
    },
    "dirty_tree": {"stable_error_code": "GIT_WORKTREE_NOT_CLEAN"},
    "wrong_target": {"stable_error_code": "TARGET_BINDING_MISMATCH"},
    "duplicates": {
        "stable_error_codes": [
            "API_APPLICATION_DUPLICATE",
            "API_SERVICE_PRINCIPAL_DUPLICATE",
            "UAMI_SERVICE_PRINCIPAL_DUPLICATE",
            "GRAPH_ROLE_ASSIGNMENT_DUPLICATE",
            "SITE_PERMISSION_DUPLICATE",
            "AZURE_RESOURCE_INVENTORY_DUPLICATE",
            "TEAMS_CATALOG_APP_DUPLICATE",
            "TEAMS_INSTALLATION_DUPLICATE",
            "SPFX_BFF_PERMISSION_STATE_DUPLICATE",
            "SPFX_TARGET_PAGE_DUPLICATE",
            "SPFX_PAGE_WEBPART_DUPLICATE",
            "SYNTHETIC_DUPLICATE_BLOCKED",
        ]
    },
    "azure_smart_detection_companion_drift": {
        "stable_error_codes": [
            "AZURE_RESOURCE_INVENTORY_UNEXPECTED",
            "AZURE_RESOURCE_PROPERTY_DRIFT",
            "AZURE_SMART_DETECTION_READBACK_FAILED",
            "AZURE_RESOURCE_INVENTORY_CHANGED_DURING_READBACK",
        ]
    },
    "broader_permissions": {
        "stable_error_codes": [
            "GRAPH_ROLE_ASSIGNMENT_BROADER",
            "SITE_PERMISSION_BROADER",
            "SPFX_BFF_GRANT_BROADER_OR_DUPLICATE",
            "SPFX_BFF_PERMISSION_REQUEST_UNEXPECTED",
        ]
    },
    "race": {"second_runner_error_code": "ACTIVATION_LOCK_HELD"},
    "secret_sentinel": {"stable_error_code": "SENSITIVE_VALUE_REJECTED"},
    "prepared_input_drift": {
        "stable_error_codes": [
            "STATIC_PREPARED_INPUTS_MISMATCH",
            "PREPARED_ARTIFACT_HASH_MISMATCH",
            "PREPARED_INPUTS_MANIFEST_MISMATCH",
            "AZURE_DEPLOYMENT_INPUT_DRIFT",
        ]
    },
    "health_auth_ready_order": {
        "ordered_probe_sequence_exact": [
            "assigned",
            "deputy",
            "denied",
            "assigned_immediately_before_tamper",
            "tampered_workspace",
            "tampered_matter",
            "tampered_purpose",
            "tampered_filter",
            "restore_assigned",
            "final_assigned_read",
            "readyz",
        ]
    },
    "synthetic_restoration_failure": {
        "stable_error_code": "SYNTHETIC_STATE_RESTORATION_FAILED"
    },
    "arm_deployment_timeout_reconciliation": {
        "unresolved_target_lock_retained": True,
        "cross_version_legacy_lock_namespace_held": True,
        "legacy_lock_hash_ledger_bound": True,
        "reconciled_template_hash_exact": True,
        "failed_baseline_missing_entra_rejected": True,
        "failed_baseline_entra_and_parameters_exact": True,
        "arm_value_only_wrapper_accepted": True,
        "arm_type_and_value_wrapper_accepted": True,
        "arm_parameter_types_exact": True,
        "arm_parameter_value_types_exact": True,
        "arm_unknown_wrapper_fields_rejected": True,
        "canonical_parameter_comparison_value_only": True,
        "canonical_parameter_hash_value_only": True,
        "failed_baseline_template_hash_owner_bound": True,
        "stable_error_codes": [
            "AZURE_BASELINE_DEPLOYMENT_SUCCEEDED_REQUIRES_NEW_RUN",
            "AZURE_BASELINE_DEPLOYMENT_FAILED",
            "AZURE_BASELINE_DEPLOYMENT_CANCELED",
            "AZURE_DEPLOYMENT_STATE_AMBIGUOUS",
        ]
    },
    "function_deployment_timeout_quarantine": {
        "state": "FAILED_PARTIAL",
        "later_steps_run": False,
        "stable_error_code": "AZURE_FUNCTION_DEPLOYMENT_STATE_AMBIGUOUS",
        "cli_success_payload_exact": "Deployment was successful.",
        "health_readback_calls_exact": 0,
        "unresolved_target_lock_retained": True,
        "cross_version_legacy_lock_namespace_held": True,
        "legacy_host_lock_namespace_held": True,
        "automatic_rollbacks_exact": 0,
        "automatic_deletions_exact": 0,
    },
    "toolchain_attestation_tamper": {
        "stable_error_codes": [
            "TOOLCHAIN_ATTESTATION_INVALID",
            "APPROVAL_PAYLOAD_MISMATCH",
        ]
    },
    "lock_journal_torn_release": {
        "release_positions_exact": ["primary", "legacy", "legacy_host"],
        "state": "FAILED_PARTIAL",
        "stable_error_code": "FINALIZATION_LOCK_RELEASE_FAILED",
        "committed_state_and_success_receipt_retained": True,
        "recovery_marker_retained": True,
        "confirmed_recovery_result": "FINALIZATION_LOCK_RECONCILED",
    },
    "lock_recovery_retry_after_torn_release": {
        "first_recovery_error_code": "FINALIZATION_LOCK_RELEASE_FAILED",
        "reconcile_marker_retained": True,
        "second_recovery_result": "FINALIZATION_LOCK_RECONCILED",
        "all_three_markers_released": True,
    },
    "invalid_existing_lock_journal": {
        "acquisition_succeeds": False,
        "existing_bytes_changed": False,
        "provider_read_calls_exact": 0,
        "provider_write_calls_exact": 0,
    },
    "recovery_marker_completeness": {
        "all_three_markers_required": True,
        "missing_directories_created": False,
        "provider_read_calls_exact": 0,
        "provider_write_calls_exact": 0,
    },
    "provisioner_bootstrap_source_drift": {
        "source_paths_exact": [
            "src/nac_bff/azure_activation_provisioner_bootstrap.py",
            "src/nac_m365_graph/provisioner_env_bootstrap.py",
        ],
        "activation_hash_changes_for_each_source": True,
        "provider_write_calls_exact": 0,
    },
    "legacy_newline_lock_recovery": {
        "legacy_marker_shape_exact": "canonical_single_activation_hash_object_with_trailing_newline",
        "unattended_reacquisition_allowed": False,
        "confirmed_recovery_result": "FINALIZATION_LOCK_RECONCILED",
        "all_three_markers_released": True,
    },
    "terminal_failed_partial_torn_release": {
        "state": "FAILED_PARTIAL",
        "stable_error_code": "TERMINAL_LOCK_RELEASE_RECOVERY_REQUIRED",
        "recovery_marker_status_exact": "TERMINAL_RELEASE_IN_PROGRESS",
        "ambiguous_provider_state_allowed": False,
        "confirmed_recovery_result": "FINALIZATION_LOCK_RECONCILED",
        "all_three_markers_released": True,
    },
    "resume_disabled": {"stable_error_code": "RESUME_DISABLED_FOR_MVP"},
}
SOURCE_MARKERS: dict[Path, tuple[str, ...]] = {
    ACTIVATION_PLAN_PATH: (
        "src/nac_bff/azure_activation_approval.py",
        "src/nac_bff/azure_activation_attestations.py",
        "src/nac_bff/azure_activation_owner_gate.py",
        "src/nac_bff/azure_activation_provisioner_bootstrap.py",
        "src/nac_m365_graph/provisioner_env_bootstrap.py",
        "activation_step_ids",
    ),
    RUNNER_PATH: (
        "_EVIDENCE_KEYS", "_STEP_EVIDENCE_KEYS", "_SUMMARY_EVIDENCE_KEYS",
        "toolchain_attestations_sha256", "TOOLCHAIN_ATTESTATION_INVALID",
        "provisioner_bootstrap_binding_sha256",
        "RESUME_DISABLED_FOR_MVP", "reconcile_azure_bff_live_activation_lock",
        "FINALIZATION_LOCK_RECONCILED",
        "LEGACY_ACTIVATION_LOCK_HELD",
        "AZURE_FUNCTION_DEPLOYMENT_STATE_AMBIGUOUS",
        "AZURE_DEPLOYMENT_STATE_AMBIGUOUS",
        "preserve_quarantine", "legacy_target_binding_sha256",
        "_HOST_STATE_RELATIVE_PATH", "_LEGACY_HOST_LOCK_ROOT",
        "_LEGACY_HOST_STATE_RELATIVE_PATH",
        "LEGACY_HOST_ACTIVATION_LOCK_HELD",
        "pwd.getpwuid(os.geteuid()).pw_dir",
    ),
    COMPOSITION_PATH: (
        "prepared-inputs.redacted.json", "bicep_parameters_snapshot_sha256",
        "inspect_uami_sites_selected", "inspect_site_read_permission",
        "inspect_provisioner_application_roles",
        "inspect_site_permission_administration",
        "SITE_PERMISSION_ADMIN_CAPABILITY_UNAVAILABLE",
        "/healthz", "/readyz", "restore_assigned",
        "toolchain_attestations_sha256", "sealed_toolchain",
        "_APPROVED_OWNER_ASSOCIATIONS",
        "not isinstance(author_association, str)",
        "build_node_runtime_integrity_payloads",
        "_PROVIDER_READBACK_ATTEMPTS", "_PROVIDER_READBACK_DELAY_SECONDS",
        "_PROVIDER_READBACK_MAX_SECONDS", "_poll_provider_registration",
        "_azure_json_with_timeout", "time.monotonic",
        "_SAFE_PROVIDER_STATES", "_PROVIDER_REGISTER_STATES",
        "_PROVIDER_POLL_WITHOUT_REGISTER_STATES", "_PROVIDER_SUCCESS_STATE",
        "_PROVIDER_TIMEOUT_ERROR", "_PROVIDER_AMBIGUOUS_STATE_ERROR",
        "_PROVIDER_MAX_REGISTER_WRITES_PER_NAMESPACE",
        "_reconcile_timed_out_deployment",
        "_APPROVED_FAILED_BASELINE_TEMPLATE_HASHES",
        "_approved_failed_baseline_template_hashes",
        "AZURE_FAILED_BASELINE_TEMPLATE_NOT_APPROVED",
        "AZURE_FAILED_BASELINE_ENTRA_BINDING_MISSING",
        "_bicep_template_hash",
        "AZURE_BASELINE_DEPLOYMENT_SUCCEEDED_REQUIRES_NEW_RUN",
        "AZURE_BASELINE_DEPLOYMENT_FAILED",
        "AZURE_BASELINE_DEPLOYMENT_CANCELED",
        "AZURE_DEPLOYMENT_STATE_AMBIGUOUS",
        "_SMART_DETECTION_ACTION_GROUP_NAME",
        "_SMART_DETECTION_ARM_ROLE_RECEIVERS",
        "_FUNCTION_DEPLOYMENT_SUCCESS",
        "_FUNCTION_DEPLOYMENT_AMBIGUOUS_ERROR",
        "_azure_function_deploy_bound",
        "AZURE_SMART_DETECTION_READBACK_FAILED",
        "build_owner_approval_payload",
        "canonical_owner_comment_body",
        "environ: Mapping[str, str] | None = None",
        "os.environ if environ is None else environ",
    ),
    PROVISIONER_BOOTSTRAP_PATH: (
        "nac.m365-azure-bff-provisioner-bootstrap/v1",
        "build_activation_provisioner_bootstrap",
        "PROVISIONER_SECRET_KEYS",
        "_trusted_regular_file_metadata",
        "_trusted_parent_chain",
        "tenant_id_emitted",
        "client_id_emitted",
        "credential_paths_emitted",
        "credential_values_emitted",
        "provider_requests_made",
        "private_key_read",
        "tenant_writes_started",
        "_MAX_STATE_BYTES = 128 * 1024",
        "os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC",
        "_bootstrap_binding_sha256",
        "state_sha256",
        "state_path_sha256",
        "certificate_path_sha256",
        "private_key_path_sha256",
    ),
    GRAPH_ACTIVATION_PATH: (
        "inspect_provisioner_application_roles",
        "PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH",
        "inspect_site_permission_administration",
        "SITE_PERMISSION_ADMIN_CAPABILITY_UNAVAILABLE",
    ),
    PROVISIONER_ENV_BOOTSTRAP_PATH: (
        "build_provisioner_env_bootstrap",
        "os.environ if env is None else env",
        "M365_PROVISIONER_CLIENT_CERTIFICATE_PATH",
        "M365_PROVISIONER_CLIENT_KEY_PATH",
    ),
    ATTESTATION_PATH: (
        "build_activation_attestation_plan",
        "TOOLCHAIN_ATTESTATION_FIELDS",
        "LIVE_CLI_ARGUMENT_BY_ATTESTATION",
        "calculate_toolchain_attestations_sha256",
        "toolchain_attestations_sha256",
        "reads_private_key",
        "executes_provider_requests",
    ),
    APPROVAL_PATH: (
        "approval_binding_sha256",
        "provisioner_bootstrap_binding_sha256",
        "build_owner_approval_payload",
        "canonical_owner_comment_body",
        "owner_comment_body_sha256",
    ),
    OWNER_GATE_PATH: (
        "build_activation_owner_gate",
        "SOURCE_TREE_CHANGED_DURING_GATE_BUILD",
        "owner_comment_body_sha256",
        "provider_requests_made",
        "private_key_read",
        "provisioner_bootstrap",
        "build_activation_provisioner_bootstrap",
        "provisioner_bootstrap_binding_sha256",
        "--provisioner-bootstrap-binding-sha256",
    ),
    CLI_PATH: (
        "bff-azure-activate-live", "bff-azure-activation-attestations",
        "bff-azure-activation-owner-gate",
        "bff-azure-activation-recovery", "--confirm-unlock",
        "--owner-approved", "--execute-live-activation",
        "--azure-cli-toolchain-sha256", "--m365-cli-sha256",
        "--m365-node-sha256", "--build-python-sha256",
        "--build-node-sha256",
        "--build-npm-cli-sha256", "--gh-cli-sha256",
        "--provisioner-certificate-sha256",
        "--provisioner-bootstrap-binding-sha256",
        "--bff-provisioner-state", "--bff-provisioner-private-key",
        "--provisioner-state", "--provisioner-certificate-path",
        "--provisioner-private-key-path",
        "effective_env = dict(os.environ)",
        "effective_env.update(bootstrap.env_overlay)",
        "environ=effective_env",
        "PROVISIONER_BOOTSTRAP_BINDING_MISMATCH",
    ),
    M365_RUNNER_PATH: (
        "_safe_bff_http_denial", "Request failed with status code 403",
        '"code": "ACCESS_DENIED"', "sealed_toolchain",
        "build_node_runtime_integrity_payloads", "pass_fds",
    ),
    SEALED_TOOLCHAIN_PATH: (
        "O_NOFOLLOW", "F_ADD_SEALS", "F_SEAL_WRITE",
        "verified_tool_bytes", "pass_fds",
    ),
    NODE_RUNTIME_INTEGRITY_PATH: (
        "build_node_runtime_manifest", "build_node_runtime_integrity_payloads",
        "NODE_RUNTIME_MODULE_SHA256_MISMATCH",
        "NODE_RUNTIME_MODULE_NOT_ALLOWED", "NODE_RUNTIME_NATIVE_ADDON_REJECTED",
        "NODE_RUNTIME_CHILD_LOADER_BINDING_MISSING",
        "NODE_RUNTIME_NODE_SUBPROCESS_REJECTED", "integrityPromisesReadFile",
        "integrityCreateReadStream", "NAC_NODE_RUNTIME_PRELOADER",
        "NAC_NODE_RUNTIME_ESM_LOADER",
        "O_NOFOLLOW", "commonjs_preloader", "esm_loader",
    ),
    AZURE_CLI_SEALED_RUNTIME_PATH: (
        "nac-azure-cli-sealed-runtime-v1", "F_ADD_SEALS", "F_SEAL_WRITE",
        "clone_newuser", "clone_newns", "ms_remount", "ms_rdonly",
        "copy_private_azure_config", "install_private_azure_cloud_config",
        "verify_write_account_binding", "WRITE_COMMAND_PREFIXES",
        "ACCOUNT_ASSERTION_FIELDS", "MAX_ACCOUNT_ASSERTION_BYTES = 16384",
        "ACCOUNT_ASSERTION_TIMEOUT_SECONDS = 30.0",
        "close_inherited_descriptors", "wait_child_exit_without_reap",
        "select.select",
        "os.pipe2(os.O_CLOEXEC)", "os.setsid()",
        "kill_account_process_group", "terminate_account_child",
        "config_file_digest", "cloud_selection_sha256",
        "MAX_CLOUD_SELECTION_BYTES = 4096",
        'if (destination / "clouds.config").exists()',
        "clouds.config", "AZURE_CONFIG_DIR",
        "AZURE_CLI_RUNTIME_ISOLATION_UNAVAILABLE",
    ),
    AZURE_LIVE_COMMANDS_PATH: (
        "_exact_default_cloud_selection_digest", "_MAX_CLOUD_SELECTION_BYTES",
        "_SMART_DETECTION_ACTION_GROUP_NAME",
        '("resource", "show")',
        "ConfigParser", "O_NONBLOCK", "run_with_timeout",
        "AZURE_CLI_CUSTOM_CLOUD_CONFIG_REJECTED",
        "AZURE_CLI_SUBSCRIPTION_STATE_INVALID",
    ),
    BFF_TEST_ENVIRONMENT_PATH: (
        '"status": status_code', '"error": {"code": code}',
    ),
    QUALITY_GATE_PATH: (
        "m365_azure_bff_live_activation",
        "scripts/validate_m365_azure_bff_live_activation.py",
    ),
    README_PATH: (
        "m365-azure-bff-live-activation.contract.json",
        "validate_m365_azure_bff_live_activation.py",
    ),
    Path("tests/test_nac_bff_azure_live_commands.py"): (
        "test_sealed_bootstrap_asserts_account_once_before_each_write",
        "test_unauthenticated_cli_state_fails_closed_without_output",
        "test_sealed_bootstrap_account_assertion_fails_closed",
        "test_sealed_bootstrap_account_child_closes_fds_and_times_out",
        "test_blocked_argv_never_reaches_subprocess",
    ),
    Path("tests/test_nac_bff_azure_activation.py"): (
        "test_current_repository_produces_hash_bound_ready_plan",
        "src/nac_bff/azure_activation_approval.py",
        "src/nac_bff/azure_activation_attestations.py",
        "src/nac_bff/azure_activation_owner_gate.py",
        "src/nac_bff/azure_activation_provisioner_bootstrap.py",
        "src/nac_m365_graph/provisioner_env_bootstrap.py",
        "test_provisioner_bootstrap_source_drift_changes_activation_hash",
    ),
    PROVISIONER_BOOTSTRAP_TEST_PATH: (
        "test_valid_inputs_build_redacted_certificate_overlay",
        "test_explicit_empty_env_does_not_inherit_secret_process_env",
        "test_each_explicit_environment_binding_must_match_exactly",
        "test_wrong_state_bindings_are_blocked_and_redacted",
        "test_secret_or_non_v1_graph_modes_are_blocked",
        "test_missing_untrusted_or_symlink_inputs_are_blocked",
        "test_each_symlink_input_is_rejected",
        "test_private_key_content_is_never_read",
        "test_broader_provisioner_role_is_blocked_before_provider_access",
    ),
    GRAPH_ACTIVATION_TEST_PATH: (
        "test_provisioner_application_roles_are_exact_and_read_only",
        "test_provisioner_application_roles_block_broader_assignment",
        "test_site_permission_admin_capability_maps_request_failure",
        "test_site_permission_admin_capability_maps_invalid_shape",
        "test_site_permission_admin_capability_maps_invalid_paging",
    ),
    Path("tests/test_nac_bff_azure_activation_owner_gate.py"): (
        "test_binding_hash_has_no_toolchain_trailing_newline",
        "test_binding_or_permission_mutation_changes_approval_body_hash",
        "test_binding_hash_rejects_nonstandard_json_numbers",
        "test_builder_rejects_noncanonical_step_sequence",
        "test_builder_rejects_inconsistent_attestations_and_live_arguments",
        "test_builder_redacts_repo_path_resolution_failure",
        "test_builder_rejects_dirty_or_changed_tree_without_partial_gate",
        "test_builder_redacts_unexpected_exception_details",
        "test_builder_propagates_attestation_not_ready_without_private_key",
        "test_cli_requires_all_provisioner_bootstrap_inputs",
    ),
    Path("tests/test_nac_bff_azure_activation_composition.py"): (
        "test_noncanonical_equivalent_body_is_rejected",
        "test_provider_registration_requires_registered_readback",
        "test_provider_registration_polls_readback_without_repeating_write",
        "test_provider_registration_poll_rejects_unknown_state",
        "test_provider_registration_reuses_inflight_registration_without_write",
        "test_bicep_timeout_reconciles_terminal_failure_without_replay",
        "test_bicep_timeout_reconciled_success_requires_new_run",
        "test_bicep_timeout_rejects_stale_success_as_ambiguous",
        "test_bicep_timeout_keeps_nonterminal_state_ambiguous",
        "test_bicep_timeout_rejects_foreign_template_hash_as_ambiguous",
        "test_bicep_timeout_rejects_malformed_template_hash_as_ambiguous",
        "test_bicep_timeout_maps_malformed_succeeded_outputs_to_ambiguous",
        "test_function_deploy_timeout_is_ambiguous_and_skips_health",
        "test_function_deploy_rejects_unexpected_success_shape",
        "test_bicep_timeout_maps_readback_adapter_exception_to_ambiguous",
        "test_prewrite_accepts_exact_failed_incremental_baseline_for_new_run",
        "test_prewrite_accepts_current_owner_bound_failed_baseline",
        "test_prewrite_accepts_arm_parameter_metadata_for_failed_baseline",
        "test_prewrite_accepts_arm_parameter_metadata_for_succeeded_baseline",
        "test_prewrite_rejects_foreign_arm_parameter_type",
        "test_prewrite_rejects_arm_parameter_value_type_mismatch",
        "test_prewrite_rejects_extra_arm_parameter_metadata",
        "test_deployment_hash_accepts_value_only_create_typed_readback",
        "test_all_twelve_handlers_accept_typed_create_value_only_readback",
        "test_prewrite_rejects_failed_baseline_without_entra_binding",
        "test_prewrite_rejects_unapproved_failed_baseline_template",
        "test_prewrite_rejects_failed_baseline_with_foreign_api_audience",
        "test_provider_registration_poll_propagates_cli_failure",
        "test_provider_registration_maps_cli_timeout_to_readback_timeout",
        "test_provider_registration_rejects_readback_after_deadline",
        "test_prewrite_rejects_foreign_smart_detection_summary_before_detail_read",
        "test_prewrite_rejects_foreign_smart_detection_detail_identity",
        "test_prewrite_rejects_inventory_change_during_companion_readback",
        "test_prewrite_maps_smart_detection_adapter_exception",
        "test_prewrite_maps_second_inventory_adapter_exception",
        "test_prewrite_maps_second_inventory_failure_result",
        "test_prewrite_maps_malformed_second_inventory_result",
    ),
    Path("tests/test_nac_bff_azure_activation_runner.py"): (
        "test_legacy_binding_lock_blocks_new_hash_namespace",
        "test_old_host_lock_namespace_blocks_new_runner",
        "test_ambiguous_arm_state_retains_cross_version_quarantine",
        "test_default_host_state_root_is_persistent_user_state",
        "test_ambiguous_function_state_retains_cross_version_quarantine",
        "test_persistent_lock_markers_are_released_after_verified_receipt",
        "test_released_marker_accepts_new_activation_and_held_blocks",
        "test_prewrite_failure_releases_markers_and_new_approval_hash_can_retry",
        "test_failure_after_write_is_failed_partial_and_stops",
        "test_hard_crash_during_write_retains_all_markers_and_blocks_retry",
        "test_partial_release_marker_writes_are_committed_and_recoverable",
        "test_torn_release_journal_appends_are_recoverable",
        "test_recovery_release_is_retryable_after_torn_append",
        "test_terminal_failed_partial_torn_release_is_recoverable",
        "test_canonical_newline_legacy_lock_is_reconciled",
        "test_existing_empty_or_invalid_lock_journal_blocks_acquisition",
        "test_recovery_requires_legacy_markers_and_never_creates_roots",
        "test_explicit_reconcile_is_read_only_until_confirmed",
    ),
}
TEST_PATHS = (
    Path("tests/test_nac_m365_sealed_toolchain.py"),
    Path("tests/test_nac_m365_node_runtime_integrity.py"),
    Path("tests/test_nac_bff_azure_activation.py"),
    Path("tests/test_nac_bff_azure_activation_attestations.py"),
    PROVISIONER_BOOTSTRAP_TEST_PATH,
    Path("tests/test_nac_bff_azure_activation_owner_gate.py"),
    Path("tests/test_nac_bff_azure_activation_runner.py"),
    Path("tests/test_nac_bff_azure_activation_cli.py"),
    Path("tests/test_nac_bff_azure_activation_composition.py"),
    Path("tests/test_nac_bff_azure_live_commands.py"),
    Path("tests/test_nac_bff_graph_activation.py"),
    Path("tests/test_nac_bff_live_synthetic_workspace.py"),
    Path("tests/test_m365_spfx_site_deployment.py"),
    Path("tests/test_m365_mvp_test_environment_deploy.py"),
    Path("tests/test_nac_bff_azure_function_host.py"),
    Path("tests/test_m365_azure_bff_live_activation_negative_paths.py"),
)


BEHAVIOR_TEST_MODULES = (
    "tests.test_nac_m365_sealed_toolchain",
    "tests.test_nac_m365_node_runtime_integrity",
    "tests.test_nac_bff_azure_activation",
    "tests.test_nac_bff_azure_activation_attestations",
    "tests.test_nac_bff_azure_activation_provisioner_bootstrap",
    "tests.test_nac_bff_azure_activation_owner_gate",
    "tests.test_nac_bff_azure_activation_runner",
    "tests.test_nac_bff_azure_activation_composition",
    "tests.test_nac_bff_graph_activation",
    "tests.test_nac_bff_azure_live_commands",
    "tests.test_nac_bff_live_synthetic_workspace",
    "tests.test_nac_bff_azure_activation_cli",
    "tests.test_m365_spfx_site_deployment",
    "tests.test_m365_mvp_test_environment_deploy",
    "tests.test_m365_azure_bff_live_activation_negative_paths",
)


def main() -> int:
    errors = validate(REPO_ROOT)
    if not errors:
        errors.extend(_run_behavioral_tests(REPO_ROOT))
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print(
        "OK: M365 Azure BFF live activation contracts, implementation and "
        "behavioral verification suite agree."
    )
    return 0


def _run_behavioral_tests(repo_root: Path) -> list[str]:
    temporary = tempfile.TemporaryDirectory(prefix="nac-bff-validator-")
    test_home = Path(temporary.name)
    env = dict(os.environ)
    env["HOME"] = str(test_home)
    env["AZURE_CONFIG_DIR"] = str(test_home / ".azure")
    src = str((repo_root / "src").resolve())
    current = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src if not current else os.pathsep.join((src, current))
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "unittest", *BEHAVIOR_TEST_MODULES],
            cwd=repo_root,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except (OSError, subprocess.SubprocessError):
        return ["behavioral verification suite could not execute"]
    finally:
        temporary.cleanup()
    if completed.returncode != 0:
        return [
            "behavioral verification suite failed; run the exact listed unittest "
            "modules for local diagnostics"
        ]
    return []


def validate(repo_root: Path) -> list[str]:
    errors: list[str] = []
    domain = _read_json(repo_root / DOMAIN_PATH, "domain contract", errors)
    verification = _read_yaml(
        repo_root / VERIFICATION_PATH, "verification contract", errors
    )
    if domain:
        _validate_domain(domain, errors)
    if verification:
        _validate_verification(verification, errors)
    if domain and verification:
        _validate_cross_contract(domain, verification, errors)
    _validate_runner(repo_root / RUNNER_PATH, errors)
    _validate_source_and_test_markers(repo_root, errors)
    return errors


def _read_json(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing {label}: {path}")
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid {label} JSON: {type(exc).__name__}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{label} must be an object")
        return {}
    return payload


def _read_yaml(path: Path, label: str, errors: list[str]) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append(f"missing {label}: {path}")
        return {}
    except (OSError, yaml.YAMLError) as exc:
        errors.append(f"invalid {label} YAML: {type(exc).__name__}")
        return {}
    if not isinstance(payload, dict):
        errors.append(f"{label} must be a mapping")
        return {}
    return payload


def _validate_domain(domain: dict[str, Any], errors: list[str]) -> None:
    _require_values(
        domain,
        {
            "schema_version": "nac.m365-azure-bff-live-activation/v1",
            "contract_id": "m365.azure_bff_live_activation",
            "leading_issue": LEADING_ISSUE,
            "parent_issue": PARENT_ISSUE,
            "provisioner_bootstrap_issue": PROVISIONER_BOOTSTRAP_ISSUE,
            "provisioner_bootstrap_acceptance_ids": (
                PROVISIONER_BOOTSTRAP_ACCEPTANCE_IDS
            ),
            "site_permission_boundary_issue": SITE_PERMISSION_BOUNDARY_ISSUE,
            "site_permission_boundary_acceptance_ids": (
                SITE_PERMISSION_BOUNDARY_ACCEPTANCE_IDS
            ),
            "safety_rework_issue": SAFETY_REWORK_ISSUE,
            "safety_rework_acceptance_ids": SAFETY_REWORK_ACCEPTANCE_IDS,
            "owner_gate_safety_rework_issue": OWNER_GATE_SAFETY_REWORK_ISSUE,
            "owner_gate_safety_rework_acceptance_ids": (
                OWNER_GATE_SAFETY_REWORK_ACCEPTANCE_IDS
            ),
            "acceptance_ids": ACCEPTANCE_IDS,
            "verification_contract": VERIFICATION_PATH.as_posix(),
        },
        "domain",
        errors,
    )
    steps = domain.get("steps")
    actual_steps = [
        (step.get("order"), step.get("id"))
        for step in steps
        if isinstance(step, dict)
    ] if isinstance(steps, list) else []
    if actual_steps != list(enumerate(STEP_IDS, start=1)) or len(actual_steps) != 12:
        errors.append("domain steps must contain the exact ordered twelve-step sequence")
    provider_step = steps[0] if isinstance(steps, list) and steps else None
    if not isinstance(provider_step, dict) or provider_step.get(
        "readback_policy"
    ) != PROVIDER_READBACK_POLICY:
        errors.append("domain provider readback policy differs")
    deployment_step = steps[3] if isinstance(steps, list) and len(steps) > 3 else None
    if not isinstance(deployment_step, dict) or deployment_step.get(
        "timeout_reconciliation"
    ) != DEPLOYMENT_RECONCILIATION_POLICY:
        errors.append("domain ARM deployment timeout reconciliation policy differs")

    if not isinstance(deployment_step, dict) or deployment_step.get(
        "failed_baseline_acceptance"
    ) != FAILED_BASELINE_ACCEPTANCE_POLICY:
        errors.append("domain ARM failed-baseline acceptance policy differs")

    inventory = domain.get("prewrite_inventory")
    if not isinstance(inventory, dict):
        errors.append("domain prewrite_inventory must be an object")
    else:
        if inventory.get(
            "azure_application_insights_companion_exact"
        ) != AZURE_APPLICATION_INSIGHTS_COMPANION_POLICY:
            errors.append(
                "domain Azure Application Insights companion policy differs"
            )
        if inventory.get(
            "azure_application_insights_companion_count_allowed"
        ) != [0, 1]:
            errors.append(
                "domain Azure Application Insights companion cardinality differs"
            )
        if inventory.get(
            "single_logical_read_only_snapshot_required"
        ) is not True:
            errors.append(
                "domain Azure inventory logical snapshot requirement differs"
            )
        if inventory.get(
            "site_permission_administration_capability_probe_exact"
        ) != SITE_PERMISSION_ADMIN_CAPABILITY:
            errors.append(
                "domain site-permission administration capability probe differs"
            )
        if inventory.get(
            "provisioner_graph_application_role_inventory_exact"
        ) != PROVISIONER_GRAPH_APPLICATION_ROLE_INVENTORY:
            errors.append(
                "domain provisioner Graph application-role inventory differs"
            )

    exclusive_lock = domain.get("exclusive_lock")
    if not isinstance(exclusive_lock, dict) or any(
        exclusive_lock.get(key) != value
        for key, value in EXCLUSIVE_LOCK_PERSISTENCE_POLICY.items()
    ):
        errors.append("domain persistent host lock policy differs")

    gate = domain.get("consolidated_owner_gate")
    if not isinstance(gate, dict):
        errors.append("domain consolidated_owner_gate must be an object")
    else:
        approval_reference = gate.get("immutable_approval_reference")
        if not isinstance(approval_reference, dict):
            errors.append(
                "domain immutable_approval_reference must be an object"
            )
        else:
            _require_values(
                approval_reference,
                {
                    "owner_author_login_exact": "ofunk",
                    "owner_author_associations_exact": OWNER_ASSOCIATIONS,
                    "missing_or_malformed_author_association_behavior": (
                        "reject_with_APPROVAL_OWNER_MISMATCH"
                    ),
                },
                "domain immutable approval reference",
                errors,
            )
        _require_list(
            gate, "approval_payload_fields_exact", APPROVAL_FIELDS,
            "domain approval payload fields", errors,
        )
        toolchain = gate.get("toolchain_attestation_binding")
        if not isinstance(toolchain, dict):
            errors.append(
                "domain toolchain_attestation_binding must be an object"
            )
        else:
            _require_list(
                toolchain, "input_fields_exact", TOOLCHAIN_ATTESTATION_FIELDS,
                "domain toolchain attestation fields", errors,
            )
            expected_runtime_binding = {
                "runtime_executable_bytes_mode": (
                    "digest_verified_single_read_sealed_memfd"
                ),
                "node_runtime_bundle_digest_fields": [
                    "m365_cli_sha256",
                    "build_npm_cli_sha256",
                ],
                "runtime_node_module_bytes_mode": (
                    "owner_bound_full_tree_manifest_and_per_load_sha256_"
                    "verified_exact_bytes"
                ),
                "runtime_unmanifested_or_changed_module_execution_allowed": False,
                "runtime_native_node_addons_allowed": False,
                "runtime_module_symlinks_allowed": False,
                "linux_memfd_and_proc_fd_required": True,
                "azure_cli_runtime_bundle_digest_field": (
                    "azure_cli_toolchain_sha256"
                ),
                "azure_cli_runtime_bytes_mode": (
                    "sealed_interpreter_bootstrap_manifest_plus_verified_"
                    "private_readonly_mount_namespace_copy"
                ),
                "azure_cli_original_wrapper_execution_allowed": False,
                "azure_cli_private_user_and_mount_namespace_required": True,
                "azure_cli_namespace_unavailable_behavior": (
                    "fail_closed_before_provider_request"
                ),
                "azure_cli_extension_loading_allowed": False,
                "azure_cli_extensions_mode": (
                    "empty_readonly_private_roots_and_dynamic_install_disabled"
                ),
                "azure_cli_cloud_name_exact": "AzureCloud",
                "azure_cli_custom_cloud_config_allowed": False,
                "azure_cli_default_cloud_selection_metadata_mode": (
                    "exact_AzureCloud_subscription_only_preflight_then_omitted"
                ),
                "azure_cli_default_cloud_selection_binding_mode": (
                    "stable_preflight_sha256_sealed_manifest_revalidated_"
                    "before_omission"
                ),
                "azure_cli_default_cloud_selection_max_bytes": 4096,
                "azure_cli_config_mode": (
                    "stable_nofollow_opaque_cli_state_private_mount_namespace_"
                    "tmpfs_plus_generated_exact_AzureCloud_config_and_same_"
                    "snapshot_per_write_account_assertion"
                ),
                "azure_cli_profile_schema_dependency_allowed": False,
                "azure_cli_profile_state_opaque_to_nac": True,
                "azure_cli_authenticated_account_state_required": True,
                "azure_cli_installation_id_only_profile_behavior": (
                    "fail_closed_as_unauthenticated_before_write"
                ),
                "azure_cli_private_cloud_config_mode": (
                    "generated_exact_AzureCloud_in_private_snapshot"
                ),
                "azure_cli_account_assertions_per_write_exact": 1,
                "azure_cli_account_assertion_fields_exact": [
                    "id",
                    "tenantId",
                    "environmentName",
                    "state",
                ],
                "azure_cli_account_assertion_state_exact": "Enabled",
                "azure_cli_account_assertion_max_bytes": 16384,
                "azure_cli_account_assertion_timeout_seconds": 30.0,
                "azure_cli_function_deployment_cli_timeout_seconds_exact": 900,
                "azure_cli_function_deployment_process_timeout_seconds_exact": 1020,
                "azure_cli_function_deployment_timeout_relation": (
                    "process_timeout_gt_cli_timeout"
                ),
                "azure_cli_function_deployment_timeout_behavior": (
                    "fail_closed_without_health_or_later_steps"
                ),
                "azure_cli_function_deployment_success_payload_exact": (
                    "Deployment was successful."
                ),
                "azure_cli_function_deployment_ambiguous_error_exact": (
                    "AZURE_FUNCTION_DEPLOYMENT_STATE_AMBIGUOUS"
                ),
                "azure_cli_function_deployment_ambiguous_quarantine_retained": True,
                "azure_cli_account_assertion_duplicate_keys_allowed": False,
                "azure_cli_account_assertion_stdout_evidence_allowed": False,
                "azure_cli_account_assertion_stderr_mode": "discard_to_devnull",
                "azure_cli_account_assertion_parent_death_signal_required": True,
                "azure_cli_account_assertion_inherited_fd_mode": (
                    "cloexec_pipe_close_all_non_stdio_before_azure_cli_import"
                ),
                "azure_cli_account_assertion_process_group_mode": (
                    "dedicated_session_kill_group_and_reap_on_failure_or_completion"
                ),
                "azure_cli_account_assertion_failure_behavior": (
                    "terminate_and_reap_child_then_fail_closed_before_target_write"
                ),
                "azure_cli_account_assertion_same_private_config_snapshot_required": True,
                "azure_cli_write_prefixes_exact": [
                    ["provider", "register"],
                    ["group", "create"],
                    ["deployment", "group", "create"],
                    ["functionapp", "deployment", "source", "config-zip"],
                ],
                "azure_deployment_template_mode": (
                    "repo_compiled_reproducible_hash_bound_arm_json"
                ),
                "azure_bicep_runtime_compilation_allowed": False,
                "node_child_process_loader_mode": (
                    "fork_only_immutable_preload_bound_node_manifest_node_"
                    "options_parent_pid_pinned_sealed_memfd_paths_with_execpath_"
                    "and_clean_execargv_all_public_and_low_level_spawn_"
                    "exec_execfile_commonjs_esm_prototype_and_process_binding_"
                    "variants_rejected"
                ),
                "spfx_build_dependency_digest_mode": (
                    "post_npm_ci_full_input_tree_manifest_excluding_declared_"
                    "fresh_generated_outputs_verified_before_between_and_after_"
                    "direct_heft_steps"
                ),
                "runtime_manifest_asset_read_mode": (
                    "manifest_bound_sync_callback_promise_read_stream_and_"
                    "open_as_blob_assets_per_read_nofollow_fstat_captured_"
                    "primordials_and_callback_stream_delivery_sha256_external_"
                    "alias_realpath_inode_"
                    "classification_descriptor_apis_fail_closed_and_esm_"
                    "loader_uses_verified_byte_read"
                ),
                "node_runtime_extension_mode": (
                    "pinned_commonjs_load_cache_extensions_resolver_prototype_"
                    "container_load_require_compile_with_preexecution_module_"
                    "instance_require_null_prototype_cache_container_pending_active_"
                    "completed_cache_identity_"
                    "provenance_canonical_node_builtin_ids_manifest_verified_"
                    "pirates_only_js_transform_nonreplaceable_cjs_json_"
                    "native_terminals_and_captured_set_candidate_iteration_"
                    "stream_listener_push_emit"
                ),
                "node_worker_loader_mode": (
                    "manifest_allowlisted_worker_entry_with_explicit_parent_"
                    "pid_pinned_sealed_loader_execargv"
                ),
                "spfx_native_resolver_mode": (
                    "exact_pinned_wasm32_wasi_with_force_wasi_and_manifest_"
                    "verified_wasm_bytes"
                ),
                "spfx_generated_output_read_mode": (
                    "fresh_isolated_clean_declared_outputs_stable_nofollow_"
                    "reads_symlink_safe_atomic_verified_runtime_asset_copy_"
                    "native_addons_blocked_and_final_package_sha256"
                ),
                "provider_artifact_binding_mode": (
                    "expected_sha256_pre_and_post_verified_private_readonly_by_default_"
                    "filename_preserving_snapshot_via_inherited_directory_fd_"
                    "attested_provider_same_account_attacker_excluded"
                ),
                "spfx_package_reproducibility_mode": (
                    "two_independent_builds_sorted_zip_fixed_metadata_and_solution_"
                    "uuid5_normalized_generated_xml_ids"
                ),
                "teams_package_binding_mode": (
                    "stable_single_descriptor_bytes_canonical_root_only_zip_exact_"
                    "capability_free_manifest_allowlist_png_validation_and_post_"
                    "download_sha256_provider_binding"
                ),
            }
            if any(
                toolchain.get(key) != value
                for key, value in expected_runtime_binding.items()
            ):
                errors.append(
                    "domain sealed toolchain runtime binding differs"
                )

    function_deploy_step = next(
        (
            item for item in domain.get("steps", [])
            if isinstance(item, dict)
            and item.get("id") == "deploy_function_package"
        ),
        {},
    )
    if (
        function_deploy_step.get("deployment_cli_timeout_seconds_exact") != 900
        or function_deploy_step.get("provider_process_timeout_seconds_exact")
        != 1020
        or function_deploy_step.get("timeout_behavior")
        != "fail_closed_without_health_or_later_steps"
        or function_deploy_step.get("cli_success_payload_exact")
        != "Deployment was successful."
        or function_deploy_step.get("ambiguous_error_exact")
        != "AZURE_FUNCTION_DEPLOYMENT_STATE_AMBIGUOUS"
        or function_deploy_step.get("ambiguous_target_lock_retained") is not True
        or function_deploy_step.get(
            "ambiguous_cross_version_legacy_lock_namespace_held"
        )
        is not True
        or function_deploy_step.get("ambiguous_legacy_host_lock_namespace_held")
        is not True
        or domain.get("failure_behavior", {}).get("first_error_after_any_write")
        != (
            "append_FAILED_event_set_FAILED_PARTIAL_mark_lock_RELEASED_and_stop_"
            "except_when_finalization_integrity_cannot_be_proved_or_ARM_or_"
            "Function_deployment_state_is_ambiguous"
        )
        or function_deploy_step.get("health_readback_may_reconcile_timeout")
        is not False
    ):
        errors.append("domain Step 7 deployment timeout boundary differs")

    access_step = next(
        (
            item for item in domain.get("steps", [])
            if isinstance(item, dict)
            and item.get("id") == "run_access_and_readback_smokes"
        ),
        {},
    )
    expected_denial = {"status": 403, "error": {"code": "ACCESS_DENIED"}}
    if (
        access_step.get("authenticated_denial_response_exact") != expected_denial
        or access_step.get(
            "denial_response_same_for_unauthorized_and_manipulated_input"
        ) is not True
        or access_step.get("raw_nonzero_stdout_stderr_or_response_body_forwarded")
        is not False
    ):
        errors.append("domain Step 11 generic denial boundary differs")

    evidence = domain.get("evidence_policy")
    if not isinstance(evidence, dict):
        errors.append("domain evidence_policy must be an object")
    else:
        _require_list(evidence, "strict_top_level_allowlist", TOP_LEVEL_FIELDS,
                      "domain evidence top-level allowlist", errors)
        _require_list(evidence, "step_result_allowlist", STEP_FIELDS,
                      "domain evidence step allowlist", errors)
        _require_list(evidence, "summary_field_allowlist_exact", SUMMARY_FIELDS,
                      "domain evidence summary allowlist", errors)
        boundary = evidence.get("local_trust_boundary")
        expected_boundary = {
            "tamper_evident_against_accidental_or_cross_process_mutation": True,
            "cryptographically_authentic_against_same_os_account": False,
            "formal_legal_audit_claimed": False,
            "formal_audit_requires": "external_immutable_or_signature_lane",
            "formal_audit_lane_status": "DEFERRED_OUTSIDE_SYNTHETIC_MVP",
        }
        if boundary != expected_boundary:
            errors.append("domain evidence local trust boundary differs")

    prepared = domain.get("prebuilt_deployment_inputs")
    if not isinstance(prepared, dict):
        errors.append("domain prebuilt_deployment_inputs must be an object")
    else:
        _require_list(prepared, "manifest_fields_exact", PREPARED_INPUT_FIELDS,
                      "domain prepared-input manifest fields", errors)
        if len(prepared.get("artifacts_exact", [])) != 4:
            errors.append("domain must bind exactly four prebuilt deployment inputs")
        if prepared.get("snapshot_copy_mode") != (
            "exclusive_destination_plus_source_nofollow_stable_fstat_and_"
            "expected_sha256"
        ):
            errors.append("domain prepared-input snapshot copy mode differs")
        if prepared.get("source_materialization_mode") != (
            "trusted_git_archive_from_exact_approved_commit_tree_with_ls_tree_"
            "blob_mode_blob_id_and_per_file_sha256_verification_symlink_gitlink_"
            "and_traversal_rejected"
        ):
            errors.append("domain approved-tree materialization mode differs")
        if prepared.get("provider_artifact_handoff_mode") != (
            "private_readonly_by_default_filename_preserving_expected_sha256_"
            "pre_and_post_verified_snapshot_no_mutable_source_path_attested_"
            "provider_same_account_attacker_excluded"
        ):
            errors.append("domain provider artifact handoff mode differs")

    permission_boundary = domain.get("permission_boundary")
    if not isinstance(permission_boundary, dict):
        errors.append("domain permission_boundary must be an object")
    else:
        if permission_boundary.get(
            "provisioner_site_permission_administration"
        ) != SITE_PERMISSION_ADMINISTRATION:
            errors.append(
                "domain provisioner site-permission administration boundary differs"
            )
        if permission_boundary.get(
            "provisioner_graph_application_roles_exact"
        ) != PROVISIONER_GRAPH_APPLICATION_ROLES:
            errors.append(
                "domain provisioner Graph application roles must match the exact allowlist"
            )
        if permission_boundary.get(
            "provisioner_additional_graph_roles_allowed"
        ) is not False:
            errors.append(
                "domain provisioner additional Graph roles must remain blocked"
            )
        if permission_boundary.get(
            "managed_identity_graph_application_roles_exact"
        ) != ["Sites.Selected"]:
            errors.append(
                "domain managed identity Graph role must remain exactly Sites.Selected"
            )
        if permission_boundary.get(
            "managed_identity_additional_graph_roles_allowed"
        ) is not False:
            errors.append(
                "domain managed identity additional Graph roles must remain blocked"
            )
        if permission_boundary.get("site_permission_roles_exact") != ["read"]:
            errors.append("domain managed identity site role must remain exactly read")

    target = domain.get("exact_target")
    if not isinstance(target, dict):
        errors.append("domain exact_target must be an object")
    else:
        azure = target.get("azure", {})
        workspace = target.get("workspace", {})
        actual_bindings = {
            "tenant_id": azure.get("tenant_id"),
            "subscription_id": azure.get("subscription_id"),
            "workspace_id": workspace.get("workspace_id"),
            "site_url": workspace.get("site_url"),
            "site_id": workspace.get("site_id"),
            "team_id": workspace.get("team_id"),
        }
        if actual_bindings != EXACT_BINDINGS:
            errors.append("domain exact tenant/subscription/workspace/site/team bindings differ")
        if target.get("lists") != EXACT_LIST_IDS:
            errors.append("domain exact list IDs differ")

    runner_interface = domain.get("runner_interface", {})
    if not isinstance(runner_interface, dict):
        errors.append("domain runner_interface must be an object")
    else:
        _require_list(
            runner_interface,
            "required_arguments",
            LIVE_REQUIRED_ARGUMENTS,
            "domain live runner required arguments",
            errors,
        )

    owner_gate = domain.get("runner_interface", {}).get("owner_gate_preparation")
    expected_owner_gate = {
        "command": (
            "nac m365 teams-sharepoint bff-azure-activation-owner-gate "
            "--bff-attestation-provisioner-certificate "
            "<absolute-public-certificate-path> "
            "--bff-provisioner-state <absolute-state-path> "
            "--bff-provisioner-private-key <absolute-private-key-path> "
            "--format json"
        ),
        "offline_only": True,
        "provider_requests_exact": 0,
        "private_key_reads_exact": 0,
        "clean_commit_and_tree_checked_before_and_after": True,
        "output_status_required": "READY",
        "output_fields_required": [
            "approved_commit",
            "approved_tree",
            "activation_hash",
            "toolchain_attestations_sha256",
            "owner_approval_payload",
            "owner_comment_body",
            "owner_comment_body_sha256",
            "live_cli_arguments",
            "provisioner_bootstrap_binding_sha256",
            "provisioner_bootstrap",
        ],
    }
    if owner_gate != expected_owner_gate:
        errors.append("domain owner gate preparation interface differs")

    bootstrap = domain.get("provisioner_bootstrap")
    if not isinstance(bootstrap, dict):
        errors.append("domain provisioner_bootstrap must be an object")
    else:
        _require_values(
            bootstrap,
            {
                "schema_version_exact": (
                    "nac.m365-azure-bff-provisioner-bootstrap/v1"
                ),
                "execution_phase_exact": (
                    "before_live_factory_and_before_any_provider_access"
                ),
                "graph_base_url_exact": "https://graph.microsoft.com/v1.0",
                "certificate_authentication_only": True,
                "secret_or_access_token_environment_allowed": False,
                "failure_behavior": (
                    "stable_PROVISIONER_error_before_live_factory_"
                    "provider_access_or_tenant_write"
                ),
            },
            "domain provisioner bootstrap",
            errors,
        )
        _require_list(
            bootstrap,
            "owner_gate_inputs_exact",
            [
                "--bff-provisioner-state <absolute-state-path>",
                "--bff-attestation-provisioner-certificate "
                "<absolute-public-certificate-path>",
                "--bff-provisioner-private-key <absolute-private-key-path>",
            ],
            "domain provisioner owner-gate inputs",
            errors,
        )
        _require_list(
            bootstrap,
            "live_inputs_exact",
            [
                "--provisioner-bootstrap-binding-sha256 <64-lowercase-hex>",
                "--provisioner-state <absolute-state-path>",
                "--provisioner-certificate-path "
                "<absolute-public-certificate-path>",
                "--provisioner-private-key-path <absolute-private-key-path>",
            ],
            "domain provisioner live inputs",
            errors,
        )
        if bootstrap.get("state_binding_exact") != {
            "status": "PASSED",
            "tenant_id": "870c862b-56f7-4c9b-b0d9-f1f7d32c835c",
            "application_display_name": "NaC M365 Provisioning",
            "application_client_id": "6845f6c3-896c-4e44-a50f-2a5086a13fac",
        }:
            errors.append("domain provisioner state binding differs")
        expected_state_site_permission_assignment = {
            "permission": "Sites.FullControl.All",
            "status_values_allowed": ["created", "existing"],
            "assignment_count_exact": 1,
            "missing_behavior": (
                "PROVISIONER_SITE_PERMISSION_GRAPH_ROLE_MISSING_before_live_"
                "factory_provider_access_or_tenant_write"
            ),
            "all_provisioner_permissions_exact": PROVISIONER_GRAPH_APPLICATION_ROLES,
            "all_assignment_status_values_allowed": ["created", "existing"],
            "all_assignment_count_exact": 6,
            "broader_or_duplicate_behavior": (
                "PROVISIONER_GRAPH_ROLE_BOUNDARY_MISMATCH_before_live_factory_"
                "provider_access_or_tenant_write"
            ),
        }
        if bootstrap.get("state_site_permission_assignment_exact") != (
            expected_state_site_permission_assignment
        ):
            errors.append(
                "domain provisioner site-permission assignment binding differs"
            )
        expected_binding_policy = {
            "field_exact": "provisioner_bootstrap_binding_sha256",
            "pattern": "^[0-9a-f]{64}$",
            "state_read_mode_exact": (
                "single_O_NOFOLLOW_CLOEXEC_descriptor_with_pre_open_and_"
                "post_read_fstat_snapshot"
            ),
            "state_maximum_bytes_exact": 131072,
            "canonical_encoding_exact": (
                "sorted_compact_json_utf8_without_trailing_newline"
            ),
            "inputs_exact": [
                "state_sha256_from_atomically_read_bytes",
                "state_path_sha256",
                "certificate_path_sha256",
                "private_key_path_sha256",
                "tenant_id",
                "provisioner_client_id",
                "graph_base_url",
            ],
            "raw_state_bytes_or_paths_emitted_allowed": False,
            "owner_payload_live_and_recovery_value_must_match_exactly": True,
            "owner_gate_live_cli_arguments_flag_exact": (
                "--provisioner-bootstrap-binding-sha256"
            ),
            "mismatch_behavior": (
                "stop_before_live_factory_provider_access_or_tenant_write_"
                "with_PROVISIONER_BOOTSTRAP_BINDING_MISMATCH"
            ),
        }
        if bootstrap.get("binding_policy") != expected_binding_policy:
            errors.append("domain provisioner bootstrap binding policy differs")
        expected_input_policy = {
            "absolute_paths_required": True,
            "regular_non_symlink_files_required": True,
            "trusted_parent_chain_required": True,
            "state_and_certificate_group_or_other_writable_allowed": False,
            "private_key_owner_uid_exact": "effective_os_user",
            "private_key_modes_exact": ["0400", "0600"],
            "private_key_content_reads_exact": 0,
            "private_key_digest_allowed": False,
        }
        if bootstrap.get("input_file_policy") != expected_input_policy:
            errors.append("domain provisioner input file policy differs")
        expected_environment_policy = {
            "global_process_environment_mutation_allowed": False,
            "effective_environment_mode": (
                "copy_current_environment_then_apply_non_secret_bootstrap_overlay"
            ),
            "factory_receives_effective_environment_explicitly": True,
            "overlay_variable_names_only_in_readiness": True,
            "environment_values_in_readiness_or_evidence_allowed": False,
        }
        if bootstrap.get("environment_policy") != expected_environment_policy:
            errors.append("domain provisioner environment policy differs")
        expected_readiness = {
            "status_values_exact": ["PASSED", "BLOCKED"],
            "provider_requests_made_exact": 0,
            "tenant_writes_started_exact": False,
            "private_key_read_exact": False,
            "tenant_id_emitted_exact": False,
            "client_id_emitted_exact": False,
            "credential_paths_emitted_exact": False,
            "credential_values_emitted_exact": False,
        }
        if bootstrap.get("redacted_readiness") != expected_readiness:
            errors.append("domain provisioner redacted readiness differs")

    consolidated_gate = domain.get("consolidated_owner_gate", {})
    expected_canonical_gate = {
        "binding_hash_canonical_payload": (
            "UTF-8 JSON value with sorted keys, compact separators and no "
            "trailing newline"
        ),
        "owner_comment_body_canonical_payload": (
            "exact compact sorted-key JSON approval object with no leading "
            "or trailing whitespace"
        ),
        "semantically_equivalent_noncanonical_body_allowed": False,
    }
    if not isinstance(consolidated_gate, dict) or any(
        consolidated_gate.get(key) != value
        for key, value in expected_canonical_gate.items()
    ):
        errors.append("domain owner gate canonical payload policy differs")

    recovery = domain.get("runner_interface", {}).get("finalization_recovery")
    expected_recovery = {
        "command": "nac m365 teams-sharepoint bff-azure-activation-recovery",
        "same_owner_binding_arguments_as_live_runner_required": True,
        "provisioner_bootstrap_binding_sha256_required": True,
        "owner_approved_required": True,
        "read_only_inspection_default": True,
        "unlock_argument_exact": "--confirm-unlock",
        "provider_requests_exact": 0,
        "resume_enabled": False,
        "automatic_unlock_allowed": False,
        "output_fields_allowlisted": True,
    }
    if recovery != expected_recovery:
        errors.append("domain finalization recovery interface differs")

    resume = domain.get("execution", {}).get("resume", {})
    if resume.get("mvp_enabled") is not False or resume.get("request_behavior") != (
        "reject_before_lock_or_provider_access_with_RESUME_DISABLED_FOR_MVP"
    ):
        errors.append("domain resume must fail with RESUME_DISABLED_FOR_MVP before access")


def _validate_verification(verification: dict[str, Any], errors: list[str]) -> None:
    _require_values(
        verification,
        {
            "schema_version": "nac.verification-contract/v0.1",
            "contract_id": "verification.m365_azure_bff_live_activation",
            "domain_contract_id": "m365.azure_bff_live_activation",
            "leading_issue": LEADING_ISSUE,
            "parent_issue": PARENT_ISSUE,
            "provisioner_bootstrap_issue": PROVISIONER_BOOTSTRAP_ISSUE,
            "provisioner_bootstrap_acceptance_ids": (
                PROVISIONER_BOOTSTRAP_ACCEPTANCE_IDS
            ),
            "site_permission_boundary_issue": SITE_PERMISSION_BOUNDARY_ISSUE,
            "site_permission_boundary_acceptance_ids": (
                SITE_PERMISSION_BOUNDARY_ACCEPTANCE_IDS
            ),
            "safety_rework_issue": SAFETY_REWORK_ISSUE,
            "azure_inventory_safety_rework_issue": (
                AZURE_INVENTORY_SAFETY_REWORK_ISSUE
            ),
            "owner_gate_safety_rework_issue": (
                OWNER_GATE_SAFETY_REWORK_ISSUE
            ),
            "owner_gate_safety_rework_acceptance_ids": (
                OWNER_GATE_SAFETY_REWORK_ACCEPTANCE_IDS
            ),
            "safety_rework_acceptance_ids": SAFETY_REWORK_ACCEPTANCE_IDS,
            "acceptance_ids": ACCEPTANCE_IDS,
        },
        "verification",
        errors,
    )
    bindings = verification.get("exact_bindings")
    if not isinstance(bindings, dict):
        errors.append("verification exact_bindings must be a mapping")
    else:
        if {key: bindings.get(key) for key in EXACT_BINDINGS} != EXACT_BINDINGS:
            errors.append("verification exact tenant/subscription/workspace/site/team bindings differ")
        if bindings.get("list_ids") != EXACT_LIST_IDS:
            errors.append("verification exact list IDs differ")
        if bindings.get("owner_author_associations_exact") != OWNER_ASSOCIATIONS:
            errors.append("verification owner associations differ")
        if bindings.get(
            "missing_or_malformed_author_association_behavior"
        ) != "reject_with_APPROVAL_OWNER_MISMATCH":
            errors.append("verification malformed owner association behavior differs")
    if verification.get("provisioner_bootstrap_verification") != (
        PROVISIONER_BOOTSTRAP_VERIFICATION
    ):
        errors.append("verification provisioner bootstrap policy differs")
    if verification.get(
        "provisioner_graph_application_role_inventory_verification"
    ) != PROVISIONER_GRAPH_APPLICATION_ROLE_INVENTORY:
        errors.append(
            "verification provisioner Graph application-role inventory differs"
        )
    if verification.get(
        "site_permission_administration_capability_verification"
    ) != SITE_PERMISSION_ADMIN_CAPABILITY:
        errors.append(
            "verification site-permission administration capability probe differs"
        )
    if verification.get("thresholds") != THRESHOLDS:
        errors.append("verification thresholds must equal the exact Issue #632 thresholds")
    negative = verification.get("negative_tests")
    negative_ids = [
        item.get("id") for item in negative if isinstance(item, dict)
    ] if isinstance(negative, list) else []
    if negative_ids != NEGATIVE_TEST_IDS:
        errors.append("verification negative tests must contain the exact ordered IDs")
    _validate_negative_assertions(negative, errors)

    policy = verification.get("evidence_policy")
    if not isinstance(policy, dict):
        errors.append("verification evidence_policy must be a mapping")
    else:
        _require_list(policy, "top_level_allowlist_exact", TOP_LEVEL_FIELDS,
                      "verification evidence top-level allowlist", errors)
        _require_list(policy, "step_field_allowlist_exact", STEP_FIELDS,
                      "verification evidence step allowlist", errors)
        _require_list(policy, "summary_field_allowlist_exact", SUMMARY_FIELDS,
                      "verification evidence summary allowlist", errors)
    required_evidence = verification.get("required_evidence")
    if (
        not isinstance(required_evidence, list)
        or not any(
            isinstance(item, str)
            and "azure_smart_detection_companion_drift" in item
            for item in required_evidence
        )
    ):
        errors.append(
            "verification required evidence must include Smart Detection drift"
        )
    invariants = verification.get("invariants")
    if (
        not isinstance(invariants, list)
        or not any(
            isinstance(item, str)
            and "canonical ARM ID" in item
            and "two identity-list reads" in item
            for item in invariants
        )
    ):
        errors.append(
            "verification Smart Detection identity invariant differs"
        )
    if verification.get("failure_behavior", {}).get("resume_request") != (
        "reject_before_lock_or_provider_access_with_RESUME_DISABLED_FOR_MVP"
    ):
        errors.append("verification resume error code must be RESUME_DISABLED_FOR_MVP")


def _validate_negative_assertions(
    negative: Any, errors: list[str]
) -> None:
    if not isinstance(negative, list):
        return
    by_id = {
        item.get("id"): item
        for item in negative
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    for test_id, expected in NEGATIVE_ASSERTIONS.items():
        item = by_id.get(test_id)
        assertion = item.get("assert") if isinstance(item, dict) else None
        if not isinstance(assertion, dict):
            errors.append(
                f"verification negative test {test_id} assert must be a mapping"
            )
            continue
        for key, value in expected.items():
            if assertion.get(key) != value:
                errors.append(
                    f"verification negative test {test_id} assertion "
                    f"{key} must equal the production classification"
                )


def _validate_cross_contract(
    domain: dict[str, Any], verification: dict[str, Any], errors: list[str]
) -> None:
    domain_policy = domain.get("evidence_policy", {})
    verification_policy = verification.get("evidence_policy", {})
    for domain_key, verification_key in (
        ("strict_top_level_allowlist", "top_level_allowlist_exact"),
        ("step_result_allowlist", "step_field_allowlist_exact"),
        ("summary_field_allowlist_exact", "summary_field_allowlist_exact"),
    ):
        if domain_policy.get(domain_key) != verification_policy.get(verification_key):
            errors.append(
                f"domain {domain_key} and verification {verification_key} differ"
            )


def _validate_runner(path: Path, errors: list[str]) -> None:
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except FileNotFoundError:
        errors.append(f"missing runner source: {path}")
        return
    except (OSError, SyntaxError) as exc:
        errors.append(f"invalid runner source: {type(exc).__name__}")
        return
    for name, expected in {
        "_EVIDENCE_KEYS": set(TOP_LEVEL_FIELDS),
        "_STEP_EVIDENCE_KEYS": set(STEP_FIELDS),
        "_SUMMARY_EVIDENCE_KEYS": set(SUMMARY_FIELDS),
        "_SUMMARY_COUNT_KEYS": set(SUMMARY_COUNT_FIELDS),
    }.items():
        actual = _literal_assignment(tree, name)
        if not isinstance(actual, (set, frozenset)) or actual != expected:
            errors.append(f"runner {name} must equal the contract field set")
    if (
        _top_level_literal_assignments(tree, "_HOST_STATE_RELATIVE_PATH")
        != [HOST_STATE_RELATIVE_PATH]
    ):
        errors.append("runner persistent host state path differs")
    if (
        _top_level_literal_assignments(
            tree, "_LEGACY_HOST_STATE_RELATIVE_PATH"
        )
        != [LEGACY_HOST_STATE_RELATIVE_PATH]
    ):
        errors.append("runner legacy host lock path differs")
    if "RESUME_DISABLED_FOR_MVP" not in _string_literals(tree):
        errors.append("runner must emit RESUME_DISABLED_FOR_MVP")


def _validate_source_and_test_markers(repo_root: Path, errors: list[str]) -> None:
    for relative, markers in SOURCE_MARKERS.items():
        try:
            text = (repo_root / relative).read_text(encoding="utf-8")
        except OSError:
            errors.append(f"missing marker source: {relative.as_posix()}")
            continue
        for marker in markers:
            if marker not in text:
                errors.append(f"missing source marker {marker!r} in {relative.as_posix()}")
        if (
            relative == COMPOSITION_PATH
            and "SITE_PERMISSION_ADMIN_CAPABILITY_INVALID" in text
        ):
            errors.append(
                "composition must map every site-permission capability failure "
                "to SITE_PERMISSION_ADMIN_CAPABILITY_UNAVAILABLE"
            )
    try:
        composition_tree = ast.parse(
            (repo_root / COMPOSITION_PATH).read_text(encoding="utf-8")
        )
    except (OSError, SyntaxError):
        errors.append("composition owner association allowlist is unavailable")
    else:
        if _literal_assignment(
            composition_tree, "_APPROVED_OWNER_ASSOCIATIONS"
        ) != tuple(OWNER_ASSOCIATIONS):
            errors.append("composition owner association allowlist differs")
        _validate_smart_detection_composition_structure(
            composition_tree, errors
        )
        for name, expected in (
            (
                "_DEPLOYMENT_RECONCILIATION_ATTEMPTS",
                DEPLOYMENT_RECONCILIATION_POLICY["attempts"],
            ),
            (
                "_DEPLOYMENT_RECONCILIATION_DELAY_SECONDS",
                DEPLOYMENT_RECONCILIATION_POLICY["delay_seconds"],
            ),
            (
                "_APPROVED_FAILED_BASELINE_TEMPLATE_HASHES",
                tuple(
                    FAILED_BASELINE_ACCEPTANCE_POLICY[
                        "approved_legacy_template_hashes"
                    ]
                ),
            ),
        ):
            if _top_level_literal_assignments(composition_tree, name) != [expected]:
                errors.append(
                    f"composition {name} differs from ARM reconciliation contract"
                )
        for name, expected in (
            ("_PROVIDER_READBACK_ATTEMPTS", PROVIDER_READBACK_POLICY["attempts"]),
            ("_PROVIDER_READBACK_DELAY_SECONDS", PROVIDER_READBACK_POLICY["delay_seconds"]),
            ("_PROVIDER_READBACK_MAX_SECONDS", PROVIDER_READBACK_POLICY["maximum_elapsed_seconds"]),
            ("_SAFE_PROVIDER_STATES", tuple(PROVIDER_READBACK_POLICY["allowed_states"])),
            ("_PROVIDER_REGISTER_STATES", tuple(PROVIDER_READBACK_POLICY["register_on_states"])),
            (
                "_PROVIDER_POLL_WITHOUT_REGISTER_STATES",
                tuple(PROVIDER_READBACK_POLICY["poll_without_register_on_states"]),
            ),
            ("_PROVIDER_SUCCESS_STATE", PROVIDER_READBACK_POLICY["success_state"]),
            ("_PROVIDER_TIMEOUT_ERROR", PROVIDER_READBACK_POLICY["timeout_error"]),
            ("_PROVIDER_AMBIGUOUS_STATE_ERROR", PROVIDER_READBACK_POLICY["ambiguous_state_error"]),
            (
                "_PROVIDER_MAX_REGISTER_WRITES_PER_NAMESPACE",
                PROVIDER_READBACK_POLICY["maximum_register_writes_per_namespace"],
            ),
        ):
            if _top_level_literal_assignments(composition_tree, name) != [expected]:
                errors.append(f"composition {name} differs from provider contract")

    try:
        azure_live_tree = ast.parse(
            (repo_root / AZURE_LIVE_COMMANDS_PATH).read_text(encoding="utf-8")
        )
    except (OSError, SyntaxError):
        errors.append("Azure CLI cloud selection size binding is unavailable")
    else:
        _validate_smart_detection_command_schema(azure_live_tree, errors)
        if _literal_assignment(
            azure_live_tree, "_MAX_CLOUD_SELECTION_BYTES"
        ) != 4096:
            errors.append(
                "Azure CLI cloud selection size must equal contract value 4096"
            )
    try:
        sealed_runtime_source = (
            repo_root / AZURE_CLI_SEALED_RUNTIME_PATH
        ).read_text(encoding="utf-8")
    except OSError:
        errors.append("Azure CLI sealed runtime source is unavailable")
    else:
        sealed_runtime_sha256 = hashlib.sha256(
            sealed_runtime_source.encode("utf-8")
        ).hexdigest()
        if sealed_runtime_sha256 != AZURE_CLI_SEALED_RUNTIME_SOURCE_SHA256:
            errors.append("Azure CLI sealed runtime source digest differs")
        if "validate_private_azure_profile" in sealed_runtime_source:
            errors.append(
                "Azure CLI private profile schema must not be a trust anchor"
            )
        _validate_sealed_runtime_account_binding(
            sealed_runtime_source,
            errors,
        )
    for relative in TEST_PATHS:
        if not (repo_root / relative).is_file():
            errors.append(f"missing activation test source: {relative.as_posix()}")


def _portable_ast_dump(node: ast.AST) -> str:
    normalized = copy.deepcopy(node)
    for item in ast.walk(normalized):
        if hasattr(item, "type_params"):
            delattr(item, "type_params")
    return ast.dump(normalized, include_attributes=False)


def _assignment_value(tree: ast.AST, name: str) -> ast.AST | None:
    matches: list[ast.AST] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            matches.append(node.value)
    return matches[0] if len(matches) == 1 else None


def _ast_expression_matches(value: ast.AST | None, source: str) -> bool:
    if value is None:
        return False
    expected = ast.parse(source, mode="eval").body
    return ast.dump(value, include_attributes=False) == ast.dump(
        expected, include_attributes=False
    )


def _nested_function_definition(
    tree: ast.AST, name: str
) -> ast.FunctionDef | None:
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    return matches[0] if len(matches) == 1 else None


def _validate_smart_detection_composition_structure(
    tree: ast.Module, errors: list[str]
) -> None:
    literal_bindings = {
        "_SMART_DETECTION_ACTION_GROUP_NAME": (
            AZURE_APPLICATION_INSIGHTS_COMPANION_POLICY["name_exact"]
        ),
        "_SMART_DETECTION_ACTION_GROUP_TYPE": (
            AZURE_APPLICATION_INSIGHTS_COMPANION_POLICY[
                "type_case_insensitive"
            ].casefold()
        ),
        "_SMART_DETECTION_ACTION_GROUP_SHORT_NAME": (
            AZURE_APPLICATION_INSIGHTS_COMPANION_POLICY[
                "group_short_name_exact"
            ]
        ),
        "_SMART_DETECTION_ACTION_GROUP_API_VERSION": (
            AZURE_APPLICATION_INSIGHTS_COMPANION_POLICY[
                "detail_read_api_version_exact"
            ]
        ),
        "_SMART_DETECTION_ARM_ROLE_RECEIVERS": tuple(
            AZURE_APPLICATION_INSIGHTS_COMPANION_POLICY[
                "arm_role_receivers_exact"
            ]
        ),
    }
    for name, expected in literal_bindings.items():
        if (
            _top_level_literal_assignments(tree, name) != [expected]
            or _module_scope_binding_count(tree, name) != 1
            or _pattern_binding_count(tree, name) != 0
        ):
            errors.append(f"composition {name} differs from companion contract")

    expected_id_expression = (
        'f"/subscriptions/{SUBSCRIPTION_ID}/resourceGroups/{RESOURCE_GROUP}" '
        '"/providers/Microsoft.Insights/actionGroups/" '
        'f"{_SMART_DETECTION_ACTION_GROUP_NAME}"'
    )
    if (
        _module_scope_binding_count(
            tree, "_SMART_DETECTION_ACTION_GROUP_ID"
        ) != 1
        or _pattern_binding_count(
            tree, "_SMART_DETECTION_ACTION_GROUP_ID"
        ) != 0
        or not _ast_expression_matches(
            _assignment_value(tree, "_SMART_DETECTION_ACTION_GROUP_ID"),
            expected_id_expression,
        )
    ):
        errors.append("composition Smart Detection ARM ID binding differs")

    expected_counts_expression = """{
        "armRoleReceivers": len(_SMART_DETECTION_ARM_ROLE_RECEIVERS),
        "emailReceivers": 0,
        "smsReceivers": 0,
        "webhookReceivers": 0,
        "eventHubReceivers": 0,
        "itsmReceivers": 0,
        "azureAppPushReceivers": 0,
        "automationRunbookReceivers": 0,
        "voiceReceivers": 0,
        "logicAppReceivers": 0,
        "azureFunctionReceivers": 0,
    }"""
    if (
        _module_scope_binding_count(
            tree, "_SMART_DETECTION_RECEIVER_COUNTS"
        ) != 1
        or _pattern_binding_count(
            tree, "_SMART_DETECTION_RECEIVER_COUNTS"
        ) != 0
        or not _ast_expression_matches(
            _assignment_value(tree, "_SMART_DETECTION_RECEIVER_COUNTS"),
            expected_counts_expression,
        )
    ):
        errors.append("composition Smart Detection receiver counts differ")

    identity_validator = _function_definition(
        tree, "_validate_smart_detection_action_group_identity"
    )
    property_validator = _function_definition(
        tree, "_validate_smart_detection_action_group"
    )
    if identity_validator is None or property_validator is None:
        errors.append("composition Smart Detection validators are unavailable")
    else:
        for function in (identity_validator, property_validator):
            actual_sha256 = hashlib.sha256(
                _portable_ast_dump(function).encode("utf-8")
            ).hexdigest()
            if (
                actual_sha256
                != SMART_DETECTION_FUNCTION_AST_SHA256[function.name]
            ):
                errors.append(
                    "composition Smart Detection "
                    f"{function.name} shape differs"
                )
        identity_names = {
            node.id for node in ast.walk(identity_validator) if isinstance(node, ast.Name)
        }
        if not {
            "_SMART_DETECTION_ACTION_GROUP_NAME",
            "_SMART_DETECTION_ACTION_GROUP_TYPE",
            "_SMART_DETECTION_ACTION_GROUP_ID",
            "RESOURCE_GROUP",
        }.issubset(identity_names) or (
            "AZURE_RESOURCE_INVENTORY_UNEXPECTED"
            not in _string_literals(identity_validator)
        ):
            errors.append("composition Smart Detection identity validator differs")
        property_names = {
            node.id for node in ast.walk(property_validator) if isinstance(node, ast.Name)
        }
        property_calls = {
            _call_name(node.func)
            for node in ast.walk(property_validator)
            if isinstance(node, ast.Call)
        }
        if (
            "_validate_smart_detection_action_group_identity" not in property_calls
            or not {
                "_SMART_DETECTION_ACTION_GROUP_SHORT_NAME",
                "_SMART_DETECTION_RECEIVER_COUNTS",
                "_SMART_DETECTION_ARM_ROLE_RECEIVERS",
            }.issubset(property_names)
            or "AZURE_RESOURCE_PROPERTY_DRIFT"
            not in _string_literals(property_validator)
        ):
            errors.append("composition Smart Detection property validator differs")

    inspect_method = _nested_function_definition(tree, "_inspect_azure_prewrite")
    if inspect_method is None:
        errors.append("composition Azure prewrite inventory method is unavailable")
        return
    inspect_sha256 = hashlib.sha256(
        _portable_ast_dump(inspect_method).encode("utf-8")
    ).hexdigest()
    if inspect_sha256 != SMART_DETECTION_PREWRITE_AST_SHA256:
        errors.append("composition Azure prewrite AST shape differs")
    if (
        sum(
            isinstance(node, ast.Return)
            for node in ast.walk(inspect_method)
        )
        != 4
        or _has_constant_false_control(inspect_method)
    ):
        errors.append(
            "composition Azure prewrite control-flow shape differs"
        )
    calls = [
        (node.lineno, _call_name(node.func))
        for node in ast.walk(inspect_method)
        if isinstance(node, ast.Call)
    ]
    snapshot_lines = sorted(
        line
        for line, name in calls
        if name == "_azure_inventory_identity_snapshot"
    )
    identity_lines = sorted(
        line
        for line, name in calls
        if name == "_validate_smart_detection_action_group_identity"
    )
    detail_assignments = [
        node
        for node in ast.walk(inspect_method)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "companion_detail"
            for target in node.targets
        )
    ]
    repeated_assignments = [
        node
        for node in ast.walk(inspect_method)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "repeated_resources"
            for target in node.targets
        )
    ]
    expected_detail = """self._azure_json([
        "resource",
        "show",
        "--resource-group",
        RESOURCE_GROUP,
        "--resource-type",
        "Microsoft.Insights/ActionGroups",
        "--name",
        _SMART_DETECTION_ACTION_GROUP_NAME,
        "--api-version",
        _SMART_DETECTION_ACTION_GROUP_API_VERSION,
    ])"""
    expected_repeated = (
        'self._azure.run(["resource", "list", "--resource-group", RESOURCE_GROUP])'
    )
    resource_list_call_count = sum(
        _ast_expression_matches(node, expected_repeated)
        for node in ast.walk(inspect_method)
        if isinstance(node, ast.Call)
    )
    detail_read_call_count = sum(
        _ast_expression_matches(node, expected_detail)
        for node in ast.walk(inspect_method)
        if isinstance(node, ast.Call)
    )
    ordered = (
        len(snapshot_lines) == 2
        and len(identity_lines) == 3
        and resource_list_call_count == 2
        and detail_read_call_count == 1
        and len(detail_assignments) == 1
        and len(repeated_assignments) == 1
        and snapshot_lines[0]
        < identity_lines[0]
        < detail_assignments[0].lineno
        < identity_lines[1]
        < repeated_assignments[0].lineno
        < snapshot_lines[1]
        < identity_lines[2]
    )
    if (
        not ordered
        or not _ast_expression_matches(detail_assignments[0].value, expected_detail)
        or not _ast_expression_matches(
            repeated_assignments[0].value, expected_repeated
        )
        or "AZURE_SMART_DETECTION_READBACK_FAILED"
        not in _string_literals(inspect_method)
        or "AZURE_RESOURCE_INVENTORY_CHANGED_DURING_READBACK"
        not in _string_literals(inspect_method)
    ):
        errors.append("composition Smart Detection readback sequence differs")


def _validate_smart_detection_command_schema(
    tree: ast.Module, errors: list[str]
) -> None:
    for name, expected in {
        "_SMART_DETECTION_ACTION_GROUP_NAME": (
            AZURE_APPLICATION_INSIGHTS_COMPANION_POLICY["name_exact"]
        ),
        "_SMART_DETECTION_ACTION_GROUP_TYPE": (
            AZURE_APPLICATION_INSIGHTS_COMPANION_POLICY[
                "type_case_insensitive"
            ]
        ),
        "_SMART_DETECTION_ACTION_GROUP_API_VERSION": (
            AZURE_APPLICATION_INSIGHTS_COMPANION_POLICY[
                "detail_read_api_version_exact"
            ]
        ),
    }.items():
        if (
            _top_level_literal_assignments(tree, name) != [expected]
            or _module_scope_binding_count(tree, name) != 1
            or _pattern_binding_count(tree, name) != 0
        ):
            errors.append(f"Azure command {name} differs from companion contract")

    schemas = _assignment_value(tree, "_COMMAND_SCHEMAS")
    schemas_sha256 = (
        hashlib.sha256(
            ast.dump(schemas, include_attributes=False).encode("utf-8")
        ).hexdigest()
        if schemas is not None
        else None
    )
    if schemas_sha256 != AZURE_COMMAND_SCHEMAS_AST_SHA256:
        errors.append("Azure command schemas AST shape differs")
    resource_show_entries: list[ast.AST] = []
    if isinstance(schemas, ast.Dict):
        for key, value in zip(schemas.keys, schemas.values):
            try:
                key_value = ast.literal_eval(key)
            except (TypeError, ValueError):
                continue
            if key_value == ("resource", "show"):
                resource_show_entries.append(value)
    resource_show = (
        resource_show_entries[0]
        if len(resource_show_entries) == 1
        else None
    )
    schema_mutations = 0
    mutation_methods = {
        "__delitem__",
        "__setitem__",
        "clear",
        "pop",
        "popitem",
        "setdefault",
        "update",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Subscript) and isinstance(
            node.ctx, (ast.Store, ast.Del)
        ):
            current = node.value
            while isinstance(current, (ast.Attribute, ast.Subscript)):
                current = current.value
            if isinstance(current, ast.Name) and current.id == "_COMMAND_SCHEMAS":
                schema_mutations += 1
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in mutation_methods
        ):
            current = node.func.value
            while isinstance(current, (ast.Attribute, ast.Subscript)):
                current = current.value
            if isinstance(current, ast.Name) and current.id == "_COMMAND_SCHEMAS":
                schema_mutations += 1
    if (
        len(resource_show_entries) != 1
        or _module_scope_binding_count(tree, "_COMMAND_SCHEMAS") != 1
        or _pattern_binding_count(tree, "_COMMAND_SCHEMAS") != 0
        or schema_mutations != 0
    ):
        errors.append(
            "Azure command resource show schema cardinality differs"
        )
    expected_schema = """_CommandSchema(
        ("resource", "show"),
        required=frozenset(
            {"--resource-group", "--resource-type", "--name", "--api-version"}
        ),
        optional=_COMMON_OPTIONAL,
        validators={
            "--resource-group": _single_exact(RESOURCE_GROUP),
            "--resource-type": _single_exact(
                _SMART_DETECTION_ACTION_GROUP_TYPE
            ),
            "--name": _single_exact(_SMART_DETECTION_ACTION_GROUP_NAME),
            "--api-version": _single_exact(
                _SMART_DETECTION_ACTION_GROUP_API_VERSION
            ),
            **_COMMON_VALIDATORS,
        },
    )"""
    if not _ast_expression_matches(resource_show, expected_schema):
        errors.append("Azure command resource show schema differs from contract")


def _call_name(node: ast.AST) -> str | None:
    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if not isinstance(current, ast.Name):
        return None
    parts.append(current.id)
    return ".".join(reversed(parts))


def _function_definition(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    matches = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if (
        len(matches) != 1
        or _module_scope_binding_count(tree, name) != 1
        or _name_store_or_delete_count(tree, name) != 0
        or _pattern_binding_count(tree, name) != 0
    ):
        return None
    return matches[0]


def _name_store_or_delete_count(tree: ast.AST, name: str) -> int:
    return sum(
        1
        for node in ast.walk(tree)
        if isinstance(node, ast.Name)
        and node.id == name
        and isinstance(node.ctx, (ast.Store, ast.Del))
    )


def _module_scope_binding_count(tree: ast.Module, name: str) -> int:
    class BindingVisitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.count = 0

        def visit_Name(self, node: ast.Name) -> None:
            if node.id == name and isinstance(node.ctx, (ast.Store, ast.Del)):
                self.count += 1

        def _visit_definition(
            self,
            node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
        ) -> None:
            if node.name == name:
                self.count += 1
            for decorator in node.decorator_list:
                self.visit(decorator)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for default in (*node.args.defaults, *node.args.kw_defaults):
                    if default is not None:
                        self.visit(default)

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._visit_definition(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._visit_definition(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self._visit_definition(node)

        def visit_Lambda(self, node: ast.Lambda) -> None:
            return

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                bound = alias.asname or alias.name.split(".", 1)[0]
                if bound == name:
                    self.count += 1

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            for alias in node.names:
                bound = alias.asname or alias.name
                if bound == name:
                    self.count += 1

        def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
            if node.name == name:
                self.count += 1
            for statement in node.body:
                self.visit(statement)

    visitor = BindingVisitor()
    visitor.visit(tree)
    return visitor.count


def _direct_call_statement_lines(
    function: ast.FunctionDef,
    name: str,
) -> list[int]:
    return [
        statement.lineno
        for statement in function.body
        if isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Call)
        and _call_name(statement.value.func) == name
    ]


def _pattern_binding_count(tree: ast.AST, name: str) -> int:
    count = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.MatchAs, ast.MatchStar)) and node.name == name:
            count += 1
        elif isinstance(node, ast.MatchMapping) and node.rest == name:
            count += 1
    return count


def _has_constant_false_control(tree: ast.AST) -> bool:
    return any(
        isinstance(node, (ast.If, ast.While))
        and isinstance(node.test, ast.Constant)
        and node.test.value is False
        for node in ast.walk(tree)
    )


def _has_raise_outside_exception_handlers(node: ast.AST) -> bool:
    if isinstance(node, ast.ExceptHandler):
        return False
    if isinstance(node, ast.Raise):
        return True
    return any(
        _has_raise_outside_exception_handlers(child)
        for child in ast.iter_child_nodes(node)
    )


def _outer_module_shape(tree: ast.Module) -> list[str]:
    shape: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            shape.append(ast.unparse(node))
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            shape.append(
                f"assign:{target.id}"
                if isinstance(target, ast.Name)
                else "invalid-assignment"
            )
        elif isinstance(node, ast.ClassDef):
            shape.append(f"class:{node.name}")
        elif isinstance(node, ast.FunctionDef):
            shape.append(f"function:{node.name}")
        else:
            shape.append(f"invalid:{type(node).__name__}")
    return shape


def _bootstrap_top_level_shape(tree: ast.Module) -> list[str]:
    shape: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            shape.append(ast.unparse(node))
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            shape.append(
                f"assign:{target.id}"
                if isinstance(target, ast.Name)
                else "invalid-assignment"
            )
        elif isinstance(node, ast.FunctionDef):
            shape.append(f"function:{node.name}")
        elif (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and _call_name(node.value.func) == "main"
            and not node.value.args
            and not node.value.keywords
        ):
            shape.append("call:main")
        else:
            shape.append(f"invalid:{type(node).__name__}")
    return shape


def _environment_assignment_lines(
    function: ast.FunctionDef,
    key: str,
) -> list[int]:
    lines: list[int] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Subscript):
                continue
            if not (
                isinstance(target.value, ast.Attribute)
                and isinstance(target.value.value, ast.Name)
                and target.value.value.id == "os"
                and target.value.attr == "environ"
            ):
                continue
            try:
                value = ast.literal_eval(target.slice)
            except (TypeError, ValueError):
                continue
            if value == key:
                lines.append(node.lineno)
    return lines


def _frozenset_literal_assignments(
    tree: ast.Module,
    name: str,
) -> list[Any]:
    values: list[Any] = []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            continue
        value = node.value
        if not (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "frozenset"
            and len(value.args) == 1
            and not value.keywords
        ):
            values.append(None)
            continue
        try:
            values.append(frozenset(ast.literal_eval(value.args[0])))
        except (TypeError, ValueError):
            values.append(None)
    return values


def _validate_sealed_runtime_account_binding(
    source: str,
    errors: list[str],
) -> None:
    try:
        outer_tree = ast.parse(source)
        bootstrap_assignments = _top_level_literal_assignments(
            outer_tree,
            "_BOOTSTRAP_SOURCE",
        )
        if (
            len(bootstrap_assignments) != 1
            or not isinstance(bootstrap_assignments[0], str)
            or _module_scope_binding_count(outer_tree, "_BOOTSTRAP_SOURCE") != 1
            or _name_store_or_delete_count(outer_tree, "_BOOTSTRAP_SOURCE") != 1
        ):
            raise ValueError("bootstrap source is not uniquely bound")
        bootstrap_source = bootstrap_assignments[0]
        expected_outer_shape = ['from __future__ import annotations', 'import fcntl', 'import hashlib', 'import json', 'import os', 'from dataclasses import dataclass', 'from pathlib import Path, PurePosixPath', 'import stat', 'import zipfile', 'assign:_CHUNK_SIZE', 'assign:_TAMPER_EXIT', 'assign:_ISOLATION_EXIT', 'class:SealedAzureCliRuntime', 'function:prepare_sealed_azure_cli_runtime', 'function:sealed_runtime_failure_code', 'function:_package_manifest', 'function:_read_regular_file', 'function:_trusted_directory', 'function:_sealed_package_memfd', 'function:_sealed_memfd', 'function:_stat_signature', 'function:_digest_update', 'assign:_BOOTSTRAP_SOURCE']
        if _outer_module_shape(outer_tree) != expected_outer_shape:
            raise ValueError("outer module shape differs")
        final_outer_statement = outer_tree.body[-1] if outer_tree.body else None
        if not (
            isinstance(final_outer_statement, ast.Assign)
            and len(final_outer_statement.targets) == 1
            and isinstance(final_outer_statement.targets[0], ast.Name)
            and final_outer_statement.targets[0].id == "_BOOTSTRAP_SOURCE"
        ):
            raise ValueError("bootstrap source is not the final outer binding")
        expected_outer_assignments = {
            "_CHUNK_SIZE": "1024 * 1024",
            "_TAMPER_EXIT": "86",
            "_ISOLATION_EXIT": "87",
            "_BOOTSTRAP_SOURCE": repr(bootstrap_source),
        }
        seen_outer_assignments: dict[str, str] = {}
        for node in outer_tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1:
                target = node.targets[0]
                if not isinstance(target, ast.Name):
                    raise ValueError("outer module assignment target differs")
                seen_outer_assignments[target.id] = ast.unparse(node.value)
            elif not isinstance(
                node,
                (
                    ast.Import, ast.ImportFrom, ast.FunctionDef,
                    ast.AsyncFunctionDef, ast.ClassDef,
                ),
            ):
                raise ValueError("outer module contains executable statements")
        if seen_outer_assignments != expected_outer_assignments:
            raise ValueError("outer module assignments differ")
        if (
            hashlib.sha256(bootstrap_source.encode("utf-8")).hexdigest()
            != AZURE_CLI_SEALED_BOOTSTRAP_SOURCE_SHA256
        ):
            errors.append("Azure CLI sealed bootstrap source digest differs")
        bootstrap_tree = ast.parse(bootstrap_source)
    except (SyntaxError, TypeError, ValueError):
        errors.append("Azure CLI sealed account-binding bootstrap is unavailable")
        return

    expected_top_level_shape = ['from __future__ import annotations', 'import ctypes', 'import hashlib', 'import json', 'import os', 'from pathlib import Path, PurePosixPath', 'import runpy', 'import select', 'import signal', 'import stat', 'import sys', 'import tempfile', 'import time', 'import zipfile', 'assign:TAMPER_EXIT', 'assign:ISOLATION_EXIT', 'assign:CHUNK_SIZE', 'assign:MAX_CLOUD_SELECTION_BYTES', 'assign:MAX_ACCOUNT_ASSERTION_BYTES', 'assign:ACCOUNT_ASSERTION_TIMEOUT_SECONDS', 'assign:EXPECTED_CLOUD_NAME', 'assign:EXPECTED_TENANT_ID', 'assign:EXPECTED_SUBSCRIPTION_ID', 'assign:ACCOUNT_ASSERTION_FIELDS', 'assign:WRITE_COMMAND_PREFIXES', 'assign:REQUIRED_APPARMOR_PROFILE', 'function:fail', 'function:signature', 'function:safe_archive_path', 'function:archive_target', 'function:validate_package_archive', 'function:copy_archived_verified', 'function:copy_config_file', 'function:config_file_digest', 'function:copy_private_azure_config', 'function:install_private_azure_cloud_config', 'function:validate_host_userns_profile', 'function:close_fd', 'function:close_inherited_descriptors', 'function:write_proc_mapping', 'function:write_id_maps', 'function:kill_account_process_group', 'function:terminate_account_child', 'function:terminate_child', 'function:arm_parent_death_signal', 'function:exit_with_child_status', 'function:wait_child_exit_without_reap', 'function:verify_write_account_binding', 'function:validate_account_binding_payload', 'function:enter_mapped_user_namespace', 'function:isolate', 'function:main', 'call:main']
    if _bootstrap_top_level_shape(bootstrap_tree) != expected_top_level_shape:
        errors.append("Azure CLI sealed bootstrap top-level shape differs")

    expected_literals = {
        "MAX_ACCOUNT_ASSERTION_BYTES": 16384,
        "ACCOUNT_ASSERTION_TIMEOUT_SECONDS": 30.0,
        "EXPECTED_CLOUD_NAME": "AzureCloud",
        "EXPECTED_TENANT_ID": EXACT_BINDINGS["tenant_id"],
        "EXPECTED_SUBSCRIPTION_ID": EXACT_BINDINGS["subscription_id"],
        "WRITE_COMMAND_PREFIXES": (
            ("provider", "register"),
            ("group", "create"),
            ("deployment", "group", "create"),
            ("functionapp", "deployment", "source", "config-zip"),
        ),
    }
    for name, expected in expected_literals.items():
        if (
            _top_level_literal_assignments(bootstrap_tree, name) != [expected]
            or _module_scope_binding_count(bootstrap_tree, name) != 1
            or _name_store_or_delete_count(bootstrap_tree, name) != 1
            or _pattern_binding_count(bootstrap_tree, name) != 0
        ):
            errors.append(f"Azure CLI sealed bootstrap {name} differs")
    if (
        _frozenset_literal_assignments(
            bootstrap_tree,
            "ACCOUNT_ASSERTION_FIELDS",
        ) != [frozenset({"id", "tenantId", "environmentName", "state"})]
        or _module_scope_binding_count(
            bootstrap_tree,
            "ACCOUNT_ASSERTION_FIELDS",
        ) != 1
        or _name_store_or_delete_count(
            bootstrap_tree,
            "ACCOUNT_ASSERTION_FIELDS",
        ) != 1
        or _pattern_binding_count(
            bootstrap_tree,
            "ACCOUNT_ASSERTION_FIELDS",
        ) != 0
    ):
        errors.append("Azure CLI sealed account assertion fields differ")

    attribute_store_targets = [
        _call_name(node)
        for node in ast.walk(bootstrap_tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.ctx, (ast.Store, ast.Del))
    ]
    if attribute_store_targets != [
        "sys.argv",
        "sys.stdout",
        "sys.stderr",
        "sys.__stdout__",
        "sys.__stderr__",
        "sys.argv",
    ]:
        errors.append(
            "Azure CLI sealed bootstrap attribute-write targets differ"
        )

    account_functions = [
        node
        for node in bootstrap_tree.body
        if isinstance(node, ast.FunctionDef)
        and node.name == "verify_write_account_binding"
    ]
    stream_isolation_valid = len(account_functions) == 1
    if stream_isolation_valid:
        account_function = account_functions[0]
        child_branches = [
            node
            for node in account_function.body
            if isinstance(node, ast.If)
            and isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "pid"
            and len(node.test.ops) == 1
            and isinstance(node.test.ops[0], ast.Eq)
            and len(node.test.comparators) == 1
            and isinstance(node.test.comparators[0], ast.Constant)
            and node.test.comparators[0].value == 0
        ]
        stream_isolation_valid = len(child_branches) == 1
    if stream_isolation_valid:
        child_branch = child_branches[0]
        child_tries = [
            node for node in child_branch.body if isinstance(node, ast.Try)
        ]
        stream_isolation_valid = len(child_tries) == 1
    if stream_isolation_valid:
        child_try = child_tries[0]
        forbidden_control_flow = (
            ast.Return,
            ast.Yield,
            ast.YieldFrom,
            ast.FunctionDef,
            ast.AsyncFunctionDef,
            ast.ClassDef,
            ast.Lambda,
        )
        stream_prefix_sha256 = hashlib.sha256(
            "\n".join(
                _portable_ast_dump(node) for node in child_try.body[:16]
            ).encode("utf-8")
        ).hexdigest()
        stream_isolation_valid = (
            len(child_try.body) >= 16
            and stream_prefix_sha256
            == AZURE_CLI_SEALED_CHILD_STREAM_PREFIX_AST_SHA256
            and not any(
                isinstance(node, forbidden_control_flow)
                for node in ast.walk(child_branch)
            )
            and not any(
                _has_raise_outside_exception_handlers(node)
                for node in child_try.body
            )
        )
        stream_assignments = [
            (
                _call_name(node.targets[0]),
                ast.unparse(node.value),
                node.lineno,
            )
            for node in child_try.body
            if isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Attribute)
            and _call_name(node.targets[0])
            in {
                "sys.stdout",
                "sys.stderr",
                "sys.__stdout__",
                "sys.__stderr__",
            }
        ]
        expected_stream_assignments = [
            ("sys.stdout", "child_stdout"),
            ("sys.stderr", "child_stderr"),
            ("sys.__stdout__", "child_stdout"),
            ("sys.__stderr__", "child_stderr"),
        ]
        stream_isolation_valid = (
            stream_isolation_valid
            and [
                (target, value)
                for target, value, _line in stream_assignments
            ] == expected_stream_assignments
        )
        dup2_lines = [
            node.lineno
            for node in child_try.body
            if isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Call)
            and _call_name(node.value.func) == "os.dup2"
        ]
        run_module_lines = [
            node.lineno
            for node in ast.walk(child_try)
            if isinstance(node, ast.Call)
            and _call_name(node.func) == "runpy.run_module"
        ]
        if stream_assignments:
            first_stream_line = stream_assignments[0][2]
            last_stream_line = stream_assignments[-1][2]
        else:
            first_stream_line = last_stream_line = -1
        stream_isolation_valid = (
            stream_isolation_valid
            and len(dup2_lines) == 2
            and len(run_module_lines) == 1
            and max(dup2_lines) < first_stream_line
            and last_stream_line < run_module_lines[0]
        )
    if not stream_isolation_valid:
        errors.append(
            "Azure CLI sealed bootstrap child stream isolation differs"
        )

    dynamic_namespace_calls = {
        "globals", "locals", "vars", "exec", "eval", "compile",
        "setattr", "delattr",
    }
    bootstrap_call_names = {
        _call_name(node.func)
        for node in ast.walk(bootstrap_tree)
        if isinstance(node, ast.Call)
    }
    dynamic_namespace_names = dynamic_namespace_calls | {"__builtins__"}
    referenced_names = {
        node.id for node in ast.walk(bootstrap_tree)
        if isinstance(node, ast.Name)
    }
    if (
        dynamic_namespace_calls & bootstrap_call_names
        or dynamic_namespace_names & referenced_names
    ):
        errors.append(
            "Azure CLI sealed bootstrap must not mutate its namespace dynamically"
        )

    required_function_names = (
        "main",
        "verify_write_account_binding",
        "validate_account_binding_payload",
        "close_inherited_descriptors",
        "wait_child_exit_without_reap",
        "kill_account_process_group",
        "terminate_account_child",
        "arm_parent_death_signal",
    )
    functions = {
        name: _function_definition(bootstrap_tree, name)
        for name in required_function_names
    }
    missing_or_shadowed = [
        name for name, function in functions.items() if function is None
    ]
    if missing_or_shadowed:
        errors.append(
            "Azure CLI sealed account-binding functions are missing or "
            "shadowed: " + ", ".join(missing_or_shadowed)
        )
        return
    main_function = functions["main"]
    verify_function = functions["verify_write_account_binding"]
    wait_function = functions["wait_child_exit_without_reap"]
    kill_function = functions["kill_account_process_group"]
    terminate_function = functions["terminate_account_child"]
    assert main_function is not None
    assert verify_function is not None
    assert wait_function is not None
    assert kill_function is not None
    assert terminate_function is not None

    kill_calls = [
        _call_name(node.func)
        for node in ast.walk(kill_function)
        if isinstance(node, ast.Call)
    ]
    terminate_calls = [
        _call_name(node.func)
        for node in ast.walk(terminate_function)
        if isinstance(node, ast.Call)
    ]
    if (
        kill_calls.count("os.killpg") != 1
        or kill_calls.count("os.kill") != 1
        or terminate_calls.count("kill_account_process_group") != 1
        or terminate_calls.count("os.waitpid") != 1
    ):
        errors.append(
            "Azure CLI account cleanup must kill the process group with a "
            "leader fallback and reap the child"
        )

    wait_calls = [
        _call_name(node.func)
        for node in ast.walk(wait_function)
        if isinstance(node, ast.Call)
    ]
    wait_attributes = {
        node.attr for node in ast.walk(wait_function)
        if isinstance(node, ast.Attribute)
    }
    if (
        wait_calls.count("os.waitid") != 1
        or "WNOWAIT" not in wait_attributes
        or _has_constant_false_control(wait_function)
    ):
        errors.append(
            "Azure CLI account child must be observed without reaping before "
            "its process group is terminated"
        )

    main_calls = [
        (_call_name(node.func), node.lineno)
        for node in ast.walk(main_function)
        if isinstance(node, ast.Call)
    ]
    verify_lines = [
        line for name, line in main_calls
        if name == "verify_write_account_binding"
    ]
    write_lines = [
        line for name, line in main_calls if name == "runpy.run_module"
    ]
    direct_verify_lines = _direct_call_statement_lines(
        main_function,
        "verify_write_account_binding",
    )
    direct_write_lines = _direct_call_statement_lines(
        main_function,
        "runpy.run_module",
    )
    config_lines = _environment_assignment_lines(main_function, "AZURE_CONFIG_DIR")
    if not (
        len(config_lines) == len(verify_lines) == len(write_lines) == 1
        and direct_verify_lines == verify_lines
        and direct_write_lines == write_lines
        and config_lines[0] < verify_lines[0] < write_lines[0]
    ):
        errors.append(
            "Azure CLI sealed main must bind one private config, assert once, "
            "then execute exactly one target command"
        )

    account_argv_values = [
        ast.unparse(node.value)
        for node in ast.walk(verify_function)
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Attribute)
            and _call_name(target) == "sys.argv"
            for target in node.targets
        )
    ]
    expected_account_argv = (
        "['az', 'account', 'show', '--subscription', "
        "EXPECTED_SUBSCRIPTION_ID, '--query', "
        "'{id:id,tenantId:tenantId,environmentName:environmentName,state:state}', "
        "'--output', 'json', '--only-show-errors']"
    )
    if account_argv_values != [expected_account_argv]:
        errors.append("Azure CLI sealed account assertion argv differs")

    verifier_calls = [
        (_call_name(node.func), node.lineno)
        for node in ast.walk(verify_function)
        if isinstance(node, ast.Call)
    ]
    verifier_names = [name for name, _ in verifier_calls]
    account_cli_lines = [
        line for name, line in verifier_calls if name == "runpy.run_module"
    ]
    close_lines = [
        line for name, line in verifier_calls
        if name == "close_inherited_descriptors"
    ]
    observe_lines = [
        line for name, line in verifier_calls
        if name == "wait_child_exit_without_reap"
    ]
    kill_lines = [
        line for name, line in verifier_calls
        if name == "kill_account_process_group"
    ]
    direct_observe_lines = _direct_call_statement_lines(
        verify_function,
        "wait_child_exit_without_reap",
    )
    direct_kill_lines = _direct_call_statement_lines(
        verify_function,
        "kill_account_process_group",
    )
    reap_lines = [
        line for name, line in verifier_calls if name == "os.waitpid"
    ]
    if not (
        verifier_names.count("os.fork") == 1
        and verifier_names.count("os.pipe2") == 1
        and verifier_names.count("os.setsid") == 1
        and verifier_names.count("arm_parent_death_signal") == 1
        and verifier_names.count("select.select") == 1
        and verifier_names.count("wait_child_exit_without_reap") == 1
        and verifier_names.count("validate_account_binding_payload") == 1
        and verifier_names.count("kill_account_process_group") == 1
        and verifier_names.count("terminate_account_child") >= 1
        and len(account_cli_lines) == len(close_lines) == 1
        and len(observe_lines) == len(kill_lines) == len(reap_lines) == 1
        and direct_observe_lines == observe_lines
        and direct_kill_lines == kill_lines
        and not _has_constant_false_control(verify_function)
        and close_lines[0] < account_cli_lines[0]
        and observe_lines[0] < kill_lines[0] < reap_lines[0]
    ):
        errors.append(
            "Azure CLI account child must be parent-pinned, bounded, reaped, "
            "FD-closed and validated exactly once"
        )


def _literal_assignment(tree: ast.AST, name: str) -> Any:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(target, ast.Name) and target.id == name for target in targets):
            try:
                return ast.literal_eval(node.value)
            except (TypeError, ValueError):
                return None
    return None


def _top_level_literal_assignments(tree: ast.AST, name: str) -> list[Any]:
    values: list[Any] = []
    for node in getattr(tree, "body", []):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(
            isinstance(target, ast.Name) and target.id == name
            for target in targets
        ):
            continue
        try:
            values.append(ast.literal_eval(node.value))
        except (TypeError, ValueError):
            values.append(None)
    return values


def _string_literals(tree: ast.AST) -> set[str]:
    return {
        node.value for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _require_values(
    payload: dict[str, Any],
    expected: dict[str, Any],
    label: str,
    errors: list[str],
) -> None:
    for key, value in expected.items():
        if payload.get(key) != value:
            errors.append(f"{label} {key} must equal {value!r}")


def _require_list(
    payload: dict[str, Any],
    key: str,
    expected: list[str],
    label: str,
    errors: list[str],
) -> None:
    if payload.get(key) != expected:
        errors.append(f"{label} must equal the exact ordered field list")


if __name__ == "__main__":
    sys.exit(main())
