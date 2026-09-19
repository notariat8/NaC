from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any, Iterable

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts import validate_identity_registry  # noqa: E402


CONTRACT_PATH = REPO_ROOT / "workflows" / "verification-contracts" / "m365-bff-failed-partial-safe-completion.verification.yaml"
TEST_PATH = REPO_ROOT / "tests" / "test_m365_bff_failed_partial_safe_completion.py"
RECONCILER_PATH = REPO_ROOT / "src" / "nac_bff" / "azure_function_deployment_reconciliation.py"
RECONCILER_TEST_PATH = REPO_ROOT / "tests" / "test_nac_bff_azure_function_deployment_reconciliation.py"
LIVE_COMMAND_TEST_PATH = REPO_ROOT / "tests" / "test_nac_bff_azure_live_commands.py"
ISSUE746_GATE_PATH = REPO_ROOT / "src" / "nac_bff" / "issue746_reconciliation_gate.py"
ACTIVATION_COMPOSITION_PATH = REPO_ROOT / "src" / "nac_bff" / "azure_activation_composition.py"
CLI_PATH = REPO_ROOT / "src" / "nac_cli" / "cli.py"
AI_SBOM_PATH = REPO_ROOT / "sbom" / "ai" / "nac-ai-sbom-draft.json"
AI_SBOM_MAPPING_PATH = REPO_ROOT / "sbom" / "ai" / "nac-ai-sbom-export-mapping.json"
QUALITY_GATE_PATH = REPO_ROOT / "scripts" / "quality_gate.py"
WINDOWS_WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "windows-portability.yml"
AGENT_CONTEXT_PATH = REPO_ROOT / "agent-context" / "index.json"
IDENTITY_REGISTRY_PATH = validate_identity_registry.REGISTRY_PATH
IDENTITY_SCHEMA_PATH = REPO_ROOT / "policies" / "github-identity-registry.schema.json"
SPEC_PATHS = (
    REPO_ROOT / "docs" / "de" / "superpowers" / "specs" / "2026-09-15-m365-bff-failed-partial-safe-completion-design.md",
    REPO_ROOT / "docs" / "en" / "superpowers" / "specs" / "2026-09-15-m365-bff-failed-partial-safe-completion-design.md",
)
PLAN_PATHS = (
    REPO_ROOT / "docs" / "de" / "superpowers" / "plans" / "2026-09-15-m365-bff-failed-partial-safe-completion.md",
    REPO_ROOT / "docs" / "en" / "superpowers" / "plans" / "2026-09-15-m365-bff-failed-partial-safe-completion.md",
)

REQUIRED_ACCEPTANCE_IDS = tuple(f"AC-746-{index:02d}" for index in range(1, 9))
REQUIRED_PLATFORMS = {
    "windows_native",
    "windows_remote_ci",
    "azure_linux_runtime_optional",
    "post_pr_remote",
}
REQUIRED_PROVENANCE = {
    "issue620_parent": "parent_environment_trail",
    "issue632_live_contract": "future_live_gate_contract",
    "issue739_current_trail": "latest_documented_failed_partial_trail",
    "issue743_historical_interruption": "separate_historical_interruption",
}


def identity_binding_sha256(kind: str, value: str) -> str:
    """Hash a protected identity value without copying it into public evidence."""
    return hashlib.sha256(
        f"nac-issue-746-{kind}-v1\0{value}".encode("utf-8")
    ).hexdigest()
REQUIRED_GATES = {
    "SPEC_746_APPROVAL": {
        "issue": 746,
        "authorizes": "specification_and_offline_implementation_only",
    },
    "ISSUE_739_QUARANTINE_RELEASE": {
        "issue": 739,
        "authorizes": "three_local_append_only_release_records_only",
    },
    "ISSUE_632_NEW_LIVE_RUN": {
        "issue": 632,
        "authorizes": "one_separately_hash_bound_live_run_only",
    },
}
REQUIRED_APPROVAL_REPLAY_CASES = {
    "old_632_comment", "old_739_comment", "spec_746_comment", "wrong_issue",
    "wrong_login", "wrong_author_association", "changed_body", "changed_hash",
    "cross_issue_replay", "owner_approved", "owner_approval_reference",
    "approval_body_sha256",
}
REQUIRED_IDENTITY_GATE_CASES = {
    "missing_process_role", "missing_approval_role", "inactive_identity",
    "login_registry_mismatch", "missing_operator", "association_only",
    "no_external_requirement_single_principal",
    "binding_external_requirement_single_principal",
    "binding_external_requirement_same_principal_accounts",
    "binding_external_requirement_distinct_principals",
    "incomplete_requirement_assessment",
    "unsupported_requirement_source_type",
}
REQUIRED_PREFLIGHT_CASES = {
    "action", "activation_hash", "state_sha256", "evidence_sha256",
    "ledger_head_sha256", "target_lock_sha256", "legacy_lock_sha256",
    "legacy_host_lock_sha256", "provider_observation_sha256", "failed_step",
    "failed_step_started_at_utc", "prepared_inputs_manifest_sha256",
    "function_package_sha256", "correlation_id",
    "target", "binary", "owner_permissions", "nofollow_path", "concurrent_lock",
}
REQUIRED_APPROVAL_REBINDING_CASES = {
    "reconciler_commit", "reconciler_tree", "reconciler_toolchain_sha256",
    "required_owner_login", "required_owner_principal_id_sha256",
}
REQUIRED_PROVIDER_BLOCK_CASES = {
    "deployment_applied", "missing_field", "unknown_field", "snapshot_drift",
    "redirect", "auth_error", "network_block", "timeout", "non_redactable",
}
REQUIRED_REDACTION_SINKS = {
    "provider_response", "exception", "stdout", "stderr", "log",
    "temporary_artifact", "approval_text", "telemetry", "shell_history",
}
REQUIRED_CREDENTIAL_CASES = {
    "interactive_login", "device_code", "token_refresh", "cache_create",
    "config_rewrite", "host_bytes_changed", "host_metadata_changed",
}
REQUIRED_STATUS_COUNTER_HASH_CASES = {
    "historic_writes_started_not_current_write", "inspection_required_status",
    "not_applied_classification", "stable_contract_codes_exact",
    "observation_codes_exact", "all_blocked_branches_case_bound",
    "foreign_code_rejected", "error_platform_backend_unavailable",
    "preflight_all_counters_zero", "inspection_two_snapshots_zero_mutations",
    "release_three_local_appends_only", "state_hash_unchanged",
    "evidence_hash_unchanged", "ledger_hash_unchanged", "marker_hash_expected",
    "three_journal_hashes_expected", "network_and_subprocess_counts_bounded",
}
REQUIRED_WINDOWS_EDGES = {
    "live", "recovery", "interruption_reconciliation",
    "function_deployment_reconciliation",
    "function_deployment_provenance_loss",
}
REQUIRED_WINDOWS_SIDE_EFFECTS = {
    "credential", "state", "lock", "network", "subprocess", "tenant", "provider",
}
REQUIRED_REMOTE_CONTEXTS = {
    "Privacy and Secrets Guard / secret-scan",
    "Privacy and Secrets Guard / privacy-lint",
    "NaC Quality Gate / quality-gate",
    "NaC Windows Portability / windows-offline-cli",
}
FOUR_EYES_APPROVAL = "FOUR_EYES_APPROVAL"
BLOCKED_REQUIREMENT_ASSESSMENT_INVALID = "BLOCKED_REQUIREMENT_ASSESSMENT_INVALID"
EXPECTED_PR_FILES = {
    ".codex/agents/nac-docs-parity-reviewer.toml",
    ".codex/agents/nac-policy-reviewer.toml",
    ".codex/agents/nac-scope-mapper.toml",
    ".codex/agents/nac-validation-reviewer.toml",
    ".github/workflows/governance-policy-sync.yml",
    ".github/workflows/windows-portability.yml",
    ".pi/agents/nac-docs-parity-reviewer.md",
    ".pi/agents/nac-policy-reviewer.md",
    ".pi/agents/nac-scope-mapper.md",
    ".pi/agents/nac-validation-reviewer.md",
    "agent-context/index.json",
    "AGENTS.md",
    "assets/docs/generic-workbench/VIS-721-manifest.json",
    "docs/de/cli.md",
    "docs/de/START_HERE.md",
    "docs/de/minimum-requirements.md",
    "docs/de/role-model.md",
    "docs/de/superpowers/plans/2026-09-15-m365-bff-failed-partial-safe-completion.md",
    "docs/de/superpowers/specs/2026-09-15-m365-bff-failed-partial-safe-completion-design.md",
    "docs/en/cli.md",
    "docs/en/START_HERE.md",
    "docs/en/minimum-requirements.md",
    "docs/en/role-model.md",
    "docs/en/superpowers/plans/2026-09-15-m365-bff-failed-partial-safe-completion.md",
    "docs/en/superpowers/specs/2026-09-15-m365-bff-failed-partial-safe-completion-design.md",
    "policies/access-control-policy.yaml",
    "policies/github-identity-registry.json",
    "policies/github-identity-registry.schema.json",
    "policies/process-policy.yaml",
    "policies/role-model-policy.yaml",
    "sbom/ai/nac-ai-sbom-draft.json",
    "sbom/ai/nac-ai-sbom-export-mapping.json",
    "scripts/onboarding_wizard.py",
    "scripts/privacy_lint.py",
    "scripts/quality_gate.py",
    "scripts/validate_agent_authentication_boundary.py",
    "scripts/validate_business_case_type_azure_blob_worm.py",
    "scripts/validate_business_case_type_graph_write_edge.py",
    "scripts/validate_generic_workbench_foundation.py",
    "scripts/validate_graft_context_layer.py",
    "scripts/validate_identity_registry.py",
    "scripts/validate_m365_azure_bff_live_activation.py",
    "scripts/validate_m365_azure_bff_performance_acceptance.py",
    "scripts/validate_m365_bff_failed_partial_safe_completion.py",
    "scripts/validate_m365_release_readiness_gate.py",
    "scripts/validate_m365_sharepoint_bpmn_viewer_adapter.py",
    "scripts/validate_microsoft_first_onprem_target_architecture.py",
    "scripts/validate_notarial_application_interface_inventory.py",
    "scripts/validate_xnotar_xjustiz_package_boundary.py",
    "src/nac_ai_sbom/export_mapping.py",
    "src/nac_bff/activation_security_backend.py",
    "src/nac_bff/activation_security_linux.py",
    "src/nac_bff/activation_security_windows.py",
    "src/nac_bff/approved_git_tree.py",
    "src/nac_bff/azure_activation_attestations.py",
    "src/nac_bff/azure_activation_composition.py",
    "src/nac_bff/azure_function_deployment_reconciliation.py",
    "src/nac_bff/issue746_reconciliation_gate.py",
    "src/nac_bff/azure_activation_contract.py",
    "src/nac_bff/azure_activation_provisioner_bootstrap.py",
    "src/nac_bff/azure_activation_runner.py",
    "src/nac_bff/azure_activation.py",
    "src/nac_bff/azure_interruption_baseline.py",
    "src/nac_bff/azure_interruption_reconciliation.py",
    "src/nac_bff/azure_live_commands_win.py",
    "src/nac_bff/azure_live_commands.py",
    "src/nac_bff/azure_performance_acceptance.py",
    "src/nac_bff/azure_performance_authorization.py",
    "src/nac_bff/azure_performance_infrastructure_safety.py",
    "src/nac_bff/azure_performance_lease_broker_auth.py",
    "src/nac_bff/azure_performance_lease.py",
    "src/nac_bff/azure_performance_owner_gate.py",
    "src/nac_bff/azure_performance_runtime.py",
    "src/nac_bff/azure_performance_storage_ports.py",
    "src/nac_cli/cli.py",
    "src/nac_identity/governance_registry.py",
    "src/nac_m365_graph/business_case_type_production_adapters.py",
    "src/nac_m365_graph/business_case_type_production_composition.py",
    "src/nac_m365_graph/business_case_type_write_state.py",
    "src/nac_m365_graph/mvp_test_environment_deploy.py",
    "src/nac_m365_graph/node_runtime_integrity.py",
    "src/nac_m365_graph/sealed_toolchain.py",
    "src/nac_m365_graph/spfx_site_deployment.py",
    "src/nac_runtime/platform_file_lock.py",
    "src/nac_runtime/sqlite_evidence_staging_outbox.py",
    "src/notary_kg/business_case_type_migration_quarantine.py",
    "src/notary_kg/business_case_type_migration_runner.py",
    "src/notary_kg/pilot_checklist.py",
    "src/notary_kg/workflow_contract.py",
    "tests/test_activation_security_backend.py",
    "tests/test_activation_security_windows.py",
    "tests/test_agent_authentication_boundary.py",
    "tests/test_business_case_type_graph_write_composition.py",
    "tests/test_business_case_type_graph_write_crash_recovery.py",
    "tests/test_business_case_type_graph_write_state_store.py",
    "tests/test_business_case_type_migration_cli.py",
    "tests/test_business_case_type_migration_quarantine.py",
    "tests/test_business_case_type_production_adapters.py",
    "tests/test_business_case_type_production_composition.py",
    "tests/test_codex_agent_context_index_audit.py",
    "tests/test_graft_context_layer.py",
    "tests/test_identity_registry.py",
    "tests/test_issue746_reconciliation_gate.py",
    "tests/test_m365_azure_bff_live_activation_contract.py",
    "tests/test_m365_bff_failed_partial_safe_completion.py",
    "tests/test_m365_mvp_test_environment_deploy.py",
    "tests/test_m365_sharepoint_bpmn_viewer_adapter.py",
    "tests/test_nac_bff_approved_git_tree.py",
    "tests/test_nac_bff_azure_activation_attestations.py",
    "tests/test_nac_bff_azure_activation_cli.py",
    "tests/test_nac_bff_azure_activation_composition.py",
    "tests/test_nac_bff_azure_activation_owner_gate.py",
    "tests/test_nac_bff_azure_activation_provisioner_bootstrap.py",
    "tests/test_nac_bff_azure_activation_runner.py",
    "tests/test_nac_bff_azure_function_deployment_reconciliation.py",
    "tests/test_nac_bff_azure_interruption_baseline.py",
    "tests/test_nac_bff_azure_interruption_reconciliation.py",
    "tests/test_nac_bff_azure_live_commands.py",
    "tests/test_nac_bff_azure_performance_acceptance.py",
    "tests/test_nac_bff_azure_performance_authorization.py",
    "tests/test_nac_bff_azure_performance_infrastructure_safety.py",
    "tests/test_nac_bff_azure_performance_lease_broker_auth.py",
    "tests/test_nac_bff_azure_performance_owner_gate.py",
    "tests/test_nac_bff_azure_performance_runtime.py",
    "tests/test_nac_bff_azure_performance_storage_ports.py",
    "tests/test_nac_m365_node_runtime_integrity.py",
    "tests/test_nac_m365_sealed_toolchain.py",
    "tests/test_notarkammer_demo_runtime_seed.py",
    "tests/test_notary_kg.py",
    "tests/test_platform_file_lock.py",
    "tests/test_sqlite_evidence_staging_outbox.py",
    "tests/test_validate_generic_workbench_foundation.py",
    "tests/test_validate_windows_offline_cli_portability.py",
    "tests/test_windows_offline_cli_portability.py",
    "tests/test_xnotar_xjustiz_package_boundary.py",
    "workflows/contracts/m365-azure-bff-live-activation.contract.json",
    "workflows/verification-contracts/m365-azure-bff-live-activation.verification.contract.yaml",
    "workflows/verification-contracts/m365-bff-failed-partial-safe-completion.verification.yaml",
}
REQUIRED_EXISTING_REGRESSIONS = {
    "test_total_provenance_loss_is_terminal_and_has_closed_zero_counters",
    "test_provenance_loss_rejects_wrong_binding_or_partial_inventory",
    "test_provenance_loss_confirmation_loader_binds_hash_and_shape",
    "test_provenance_loss_is_local_terminal_before_github_or_factory",
    "test_exact_approval_releases_locks_without_changing_failed_run",
    "test_wrong_owner_or_hash_never_releases_a_lock",
    "test_crash_after_lock_append_is_recovered_idempotently",
}
REQUIRED_ADAPTER_BOUNDARY_REGRESSIONS = {
    "test_function_reconciliation_rest_reads_are_exactly_bounded",
    "test_function_reconciliation_observation_projects_not_applied",
    "test_function_reconciliation_observation_rejects_applied_signal",
    "test_failures_expose_stable_codes_without_raw_output",
    "test_invalid_json_is_redacted",
    "test_duplicate_json_keys_are_rejected_and_redacted",
    "test_bound_artifact_hash_mismatch_stops_before_provider",
    "test_minimal_env_does_not_copy_credential_variables",
    "test_custom_cloud_config_is_rejected_before_subprocess",
    "test_group_writable_azure_config_root_is_rejected",
    "test_unauthenticated_cli_state_fails_closed_without_output",
    "test_adapter_forwards_bound_artifacts_with_per_call_timeout",
}
REQUIRED_NEW_TEST_METHODS = {
    "test_provenance_loss_is_terminal_without_follow_on_authority",
    "test_contract_maps_every_acceptance_id_to_platform_command_and_evidence",
    "test_provenance_roles_are_distinct_and_not_runtime_state",
    "test_approval_replay_matrix_blocks_before_mutation",
    "test_registry_approval_mode_is_source_bound_before_release",
    "test_protected_evidence_loader_rejects_unsafe_windows_inputs",
    "test_protected_identity_resolver_requires_three_same_principal_accounts",
    "test_preflight_binding_drift_matrix_blocks_before_provider",
    "test_reconciler_binding_changes_require_new_approval_after_bounded_reads",
    "test_double_snapshot_accepts_only_stable_not_applied",
    "test_provider_decision_block_matrix_has_zero_writes",
    "test_redaction_sentinel_matrix_never_reaches_any_sink",
    "test_credential_config_boundary_blocks_refresh_and_preserves_host_state",
    "test_status_error_counter_and_hash_matrix_is_exact",
    "test_windows_matrix_blocks_before_every_side_effect_edge",
    "test_crash_before_first_append_keeps_all_journals_held",
    "test_crash_after_true_prefix_completes_only_with_same_approval",
    "test_crash_after_all_appends_returns_idempotent_release",
    "test_owner_comment_loader_verifies_live_canonical_provenance",
    "test_unknown_tail_and_wrong_order_block_without_further_release",
    "test_remote_verifier_errors_are_stable_and_redacted",
    "test_verify_pr_checks_cli_requires_and_forwards_all_identity_inputs",
    "test_required_remote_checks_match_exact_context_names",
    "test_ai_sbom_registers_issue746_agentic_contract_without_release_export",
}
_STABLE_ERROR_CODES = {
    "FUNCTION_DEPLOYMENT_PROVENANCE_LOST",
    "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_ARGUMENTS_INVALID",
    "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_ARGUMENTS_REQUIRED",
    "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_BINDING_INVALID",
    "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_CONFIRMATION_INVALID",
    "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_CONFIRMATION_REQUIRED",
    "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_STATE_INVALID",
    "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_STATE_UNINSPECTABLE",
    "FUNCTION_DEPLOYMENT_CONFIRMATION_REQUIRED",
    "FUNCTION_DEPLOYMENT_APPROVAL_ARGUMENTS_REQUIRED",
    "FUNCTION_DEPLOYMENT_APPROVAL_ARGUMENTS_INVALID",
    "FUNCTION_DEPLOYMENT_APPROVAL_INVALID",
    "FUNCTION_DEPLOYMENT_APPROVAL_MISMATCH",
    "FUNCTION_DEPLOYMENT_RECONCILIATION_UNSUPPORTED",
    "FUNCTION_DEPLOYMENT_PROVIDER_OBSERVATION_DRIFT",
    "AZURE_FUNCTION_DEPLOYMENT_NOT_APPLIED_NOT_PROVEN",
    "FUNCTION_DEPLOYMENT_LOCAL_ARTIFACT_CHANGED",
    "FUNCTION_DEPLOYMENT_LOCK_SET_CHANGED",
    "OWNER_COMMENT_VERIFICATION_FAILED",
    "PLATFORM_SECURITY_BACKEND_UNAVAILABLE",
    "AZURE_FUNCTION_RECONCILIATION_ACCOUNT_MISMATCH",
    "AZURE_FUNCTION_RECONCILIATION_DEPLOYMENTS_INVALID",
    "AZURE_FUNCTION_RECONCILIATION_READ_FAILED",
    "AZURE_FUNCTION_RECONCILIATION_READ_FORBIDDEN",
    "AZURE_FUNCTION_RECONCILIATION_SITE_INVALID",
    "AZURE_FUNCTION_RECONCILIATION_TARGET_MISMATCH",
    "AZURE_FUNCTION_RECONCILIATION_TIME_INVALID",
    "FUNCTION_DEPLOYMENT_ARTIFACT_INVALID",
    "FUNCTION_DEPLOYMENT_INSPECTION_LOCAL_WRITE_DETECTED",
    "FUNCTION_DEPLOYMENT_LOCAL_SNAPSHOT_INVALID",
    "FUNCTION_DEPLOYMENT_LOCK_NOT_HELD",
    "FUNCTION_DEPLOYMENT_LOCK_REPLACED",
    "FUNCTION_DEPLOYMENT_LOCK_SET_INVALID",
    "FUNCTION_DEPLOYMENT_MARKER_INVALID",
    "FUNCTION_DEPLOYMENT_RELEASE_FAILED",
    "FUNCTION_DEPLOYMENT_RELEASE_PROGRESS_INVALID",
    "FUNCTION_DEPLOYMENT_STATE_CHANGED",
    "FUNCTION_DEPLOYMENT_STATE_INVALID",
    "FUNCTION_DEPLOYMENT_ARTIFACT_STATE_INVALID",
    "FUNCTION_DEPLOYMENT_EVIDENCE_INVALID",
    "FUNCTION_DEPLOYMENT_LEDGER_INVALID",
    "FUNCTION_DEPLOYMENT_PACKAGE_BINDING_INVALID",
    "FUNCTION_DEPLOYMENT_PREPARED_INPUTS_INVALID",
    "FUNCTION_DEPLOYMENT_PROVIDER_OBSERVATION_INVALID",
    "FUNCTION_DEPLOYMENT_RECONCILER_BINDING_INVALID",
    "FUNCTION_DEPLOYMENT_RUNTIME_REVALIDATION_FAILED",
}

_DYNAMIC_ERROR_HELPERS = {
    "_validate_failed_state",
    "_validate_prepared_inputs",
    "_stable_observation",
    "_pre_mutation_revalidation_error",
    "_validate_bindings",
}


def _command_signature(
    platform: str,
    command: str,
    acceptance_ids: Iterable[str],
    remote_evidence: Iterable[str],
    scope: str,
    side_effect_class: str,
) -> tuple[str, str, tuple[str, ...], tuple[str, ...], str, str]:
    return (
        platform,
        command,
        tuple(acceptance_ids),
        tuple(sorted(remote_evidence)),
        scope,
        side_effect_class,
    )


EXPECTED_COMMANDS = {
    "spec_traceability": _command_signature("windows_native", "python scripts/validate_spec_traceability.py", ["AC-746-07"], ["NaC Quality Gate / quality-gate"], "repository_static", "local_read_or_synthetic"),
    "language_parity": _command_signature("windows_native", "python scripts/validate_language_parity.py", ["AC-746-01"], ["NaC Quality Gate / quality-gate"], "repository_static", "local_read_or_synthetic"),
    "doc_links": _command_signature("windows_native", "python scripts/validate_doc_links.py", ["AC-746-01", "AC-746-07"], ["NaC Quality Gate / quality-gate"], "repository_static", "local_read_or_synthetic"),
    "issue746_validator": _command_signature("windows_native", "python scripts/validate_m365_bff_failed_partial_safe_completion.py", REQUIRED_ACCEPTANCE_IDS, ["NaC Quality Gate / quality-gate"], "repository_static", "local_read_or_synthetic"),
    "ai_sbom": _command_signature("windows_remote_ci", "python scripts/validate_ai_sbom.py", ["AC-746-07", "AC-746-08"], ["NaC Windows Portability / windows-offline-cli"], "repository_aggregate", "ci_read_or_synthetic"),
    "ai_sbom_export_mapping": _command_signature("windows_native", "python scripts/validate_ai_sbom_export_mapping.py", ["AC-746-07", "AC-746-08"], ["NaC Quality Gate / quality-gate"], "repository_aggregate", "local_read_or_synthetic"),
    "issue746_windows_tests": _command_signature("windows_native", "python -m unittest discover -s tests -p test_activation_security*.py", ["AC-746-02", "AC-746-03", "AC-746-05", "AC-746-06", "AC-746-08"], ["NaC Windows Portability / windows-offline-cli"], "repository_static", "local_read_or_synthetic"),
    "issue746_gate_tests": _command_signature("windows_native", "python -m unittest discover -s tests -p test_issue746_reconciliation_gate.py", ["AC-746-03", "AC-746-05", "AC-746-06", "AC-746-08"], ["NaC Windows Portability / windows-offline-cli"], "repository_static", "local_read_or_synthetic"),
    "windows_bff_regression_tests": _command_signature("windows_native", "python -m unittest discover -s tests -p test_nac_bff_azure_*.py", ["AC-746-03", "AC-746-05", "AC-746-06", "AC-746-07", "AC-746-08"], ["NaC Windows Portability / windows-offline-cli"], "repository_static", "local_read_or_synthetic"),
    "windows_business_case_regression_tests": _command_signature("windows_native", "python -m unittest discover -s tests -p test_business_case_type_*.py", ["AC-746-05", "AC-746-07", "AC-746-08"], ["NaC Windows Portability / windows-offline-cli"], "repository_static", "local_read_or_synthetic"),
    "windows_m365_regression_tests": _command_signature("windows_native", "python -m unittest discover -s tests -p test_m365_*.py", ["AC-746-05", "AC-746-07", "AC-746-08"], ["NaC Windows Portability / windows-offline-cli"], "repository_static", "local_read_or_synthetic"),
    "windows_sqlite_outbox_tests": _command_signature("windows_native", "python -m unittest discover -s tests -p test_sqlite_evidence_staging_outbox.py", ["AC-746-05", "AC-746-07", "AC-746-08"], ["NaC Windows Portability / windows-offline-cli"], "repository_static", "local_read_or_synthetic"),
    "azure_runtime_compatibility": _command_signature("azure_linux_runtime_optional", "python -m unittest discover -s tests -p test_nac_bff_azure_function_host.py", ["AC-746-07"], ["NaC Quality Gate / quality-gate"], "azure_target_compatibility", "ci_read_or_synthetic"),
    "activation_validator": _command_signature("windows_native", "python scripts/validate_m365_azure_bff_live_activation.py", ["AC-746-03", "AC-746-04", "AC-746-05", "AC-746-06"], ["NaC Windows Portability / windows-offline-cli"], "repository_static", "local_read_or_synthetic"),
    "graft_build": _command_signature("windows_native", "graft build", ["AC-746-07", "AC-746-08"], ["NaC Windows Portability / windows-offline-cli"], "repository_aggregate", "local_read_or_synthetic"),
    "graft_check": _command_signature("windows_native", "graft check", ["AC-746-07", "AC-746-08"], ["NaC Windows Portability / windows-offline-cli"], "repository_aggregate", "local_read_or_synthetic"),
    "strict_doctor": _command_signature("windows_native", "python scripts/nac.py doctor --profile strict", REQUIRED_ACCEPTANCE_IDS, ["NaC Windows Portability / windows-offline-cli"], "repository_aggregate", "local_read_or_synthetic"),
    "fetch_main": _command_signature("post_pr_remote", "git fetch --no-tags --prune origin main", ["AC-746-07", "AC-746-08"], ["fresh origin/main"], "pr_747_expected_head", "github_read_only"),
    "diff_files": _command_signature("post_pr_remote", "git diff --name-status origin/main...HEAD", ["AC-746-07", "AC-746-08"], ["complete file list"], "pr_747_expected_head", "github_read_only"),
    "diff_commits": _command_signature("post_pr_remote", "git log --oneline origin/main..HEAD", ["AC-746-07", "AC-746-08"], ["complete commit list"], "pr_747_expected_head", "github_read_only"),
    "diff_patch": _command_signature("post_pr_remote", "git diff origin/main...HEAD", ["AC-746-01", "AC-746-07", "AC-746-08"], ["complete base...head patch"], "pr_747_expected_head", "github_read_only"),
    "diff_whitespace": _command_signature("post_pr_remote", "git diff --check origin/main...HEAD", ["AC-746-07"], ["complete base...head whitespace check"], "pr_747_expected_head", "github_read_only"),
    "pr_checks_watch": _command_signature("post_pr_remote", "github-connector read notariat8/NaC PR 747 checks --expected-head HEAD", ["AC-746-07", "AC-746-08"], sorted(REQUIRED_REMOTE_CONTEXTS), "pr_747_expected_head", "github_read_only"),
    "pr_checks_enforced": _command_signature("post_pr_remote", "python-api scripts.validate_m365_bff_failed_partial_safe_completion:main(argv, github_reader=trusted_github_connector_port)", ["AC-746-07", "AC-746-08"], ["exact required check names and successful states"], "pr_747_expected_head", "github_read_only"),
}


def load_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Issue #746 verification contract must be an object")
    return payload


def _spec_affected_artifacts(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    marker = "```nac-spec-traceability\n"
    start = text.index(marker) + len(marker)
    end = text.index("\n```", start)
    manifest = yaml.safe_load(text[start:end])
    return set(manifest.get("affected_artifacts", []))


def required_stable_error_codes() -> set[str]:
    return set(_STABLE_ERROR_CODES)


def _keys(payload: object) -> set[str]:
    return set(payload) if isinstance(payload, dict) else set()


def _method_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _reconciler_literal_error_codes() -> set[str]:
    tree = ast.parse(
        RECONCILER_PATH.read_text(encoding="utf-8"),
        filename=str(RECONCILER_PATH),
    )
    codes: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"_blocked", "_provenance_loss_blocked"}
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            codes.add(node.args[0].value)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "_provenance_loss_blocked"
            and node.args
            and isinstance(node.args[0], ast.Name)
            and node.args[0].id == "PROVENANCE_LOSS"
        ):
            codes.add("FUNCTION_DEPLOYMENT_PROVENANCE_LOST")
        if (
            isinstance(node, ast.Assign)
            and any(
                isinstance(target, ast.Name)
                and target.id == "_OBSERVATION_ERROR_CODES"
                for target in node.targets
            )
            and isinstance(node.value, ast.Call)
            and node.value.args
            and isinstance(node.value.args[0], (ast.Set, ast.List, ast.Tuple))
        ):
            for element in node.value.args[0].elts:
                if isinstance(element, ast.Constant) and isinstance(element.value, str):
                    codes.add(element.value)
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name in _DYNAMIC_ERROR_HELPERS
        ):
            for child in ast.walk(node):
                if not isinstance(child, ast.Return) or child.value is None:
                    continue
                for value in ast.walk(child.value):
                    if (
                        isinstance(value, ast.Constant)
                        and isinstance(value.value, str)
                        and (
                            "_INVALID" in value.value
                            or value.value.endswith("_FAILED")
                        )
                    ):
                        codes.add(value.value)
    return codes


def classify_provider_observation(snapshots: list[dict[str, Any]]) -> str:
    if len(snapshots) != 2 or snapshots[0] != snapshots[1]:
        return "BLOCKED"
    if set(snapshots[0]) != {"classification"}:
        return "BLOCKED"
    if snapshots[0]["classification"] != "FUNCTION_DEPLOYMENT_NOT_APPLIED":
        return "BLOCKED"
    return "FUNCTION_DEPLOYMENT_NOT_APPLIED"


def _validate_block_cases(
    errors: list[str], payload: object, required: set[str], label: str,
    expected_fields: dict[str, object],
) -> None:
    if _keys(payload) != required:
        errors.append(f"{label} must contain exactly {sorted(required)}")
        return
    assert isinstance(payload, dict)
    for case_id, case in payload.items():
        if not isinstance(case, dict):
            errors.append(f"{label}.{case_id} must be an object")
            continue
        for field, expected in expected_fields.items():
            if case.get(field) != expected:
                errors.append(f"{label}.{case_id}.{field} must be {expected!r}")


def _validate_ai_sbom(errors: list[str]) -> None:
    sbom = json.loads(AI_SBOM_PATH.read_text(encoding="utf-8"))
    mapping = json.loads(AI_SBOM_MAPPING_PATH.read_text(encoding="utf-8"))
    entries = {
        item.get("id"): item
        for item in sbom.get("clusters", {}).get("system_level_properties", [])
        if isinstance(item, dict)
    }
    entry = entries.get("m365-bff-failed-partial-safe-completion-contract")
    expected = {
        "artifact": "workflows/verification-contracts/m365-bff-failed-partial-safe-completion.verification.yaml",
        "leading_issue": "https://github.com/notariat8/NaC/issues/746",
        "human_review_owner": "owner_solo_approval_source_bound",
        "approval_mode": "OWNER_SOLO_APPROVAL",
        "four_eyes_satisfied": False,
        "external_two_person_requirement": "not_applicable_no_cited_source_for_issue_746",
        "provider_boundary": (
            "local_terminal_classification_before_provider_access"
        ),
        "evidence_binding": (
            "protected_confirmation_resolver_principal_and_original_lock_hashes"
        ),
        "privacy_boundary": "synthetic_public_registry_real_mapping_repo_external",
        "release_export_enabled": False,
    }
    if not isinstance(entry, dict):
        errors.append("AI-SBOM Issue #746 system-level property is missing")
    else:
        for key, value in expected.items():
            if entry.get(key) != value:
                errors.append(f"AI-SBOM Issue #746 {key} must be {value!r}")
    if mapping.get("scope", {}).get("release_export_enabled") is not False:
        errors.append("AI-SBOM release export must remain disabled")
    if mapping.get("source_documents", {}).get("issue_746_verification_contract") != "workflows/verification-contracts/m365-bff-failed-partial-safe-completion.verification.yaml":
        errors.append("AI-SBOM export mapping must reference the Issue #746 contract")
    required_component_refs = {
        "models": "m365-bff-failed-partial-safe-completion-no-model-runtime",
        "datasets": "m365-bff-failed-partial-safe-completion-synthetic-fixtures",
        "infrastructure": "m365-bff-failed-partial-safe-completion-offline-runtime",
        "security_properties": "m365-bff-failed-partial-safe-completion-boundary",
        "key_performance_indicators": "m365-bff-failed-partial-safe-completion-acceptance",
    }
    clusters = sbom.get("clusters", {})
    for cluster, item_id in required_component_refs.items():
        items = clusters.get(cluster, [])
        if not any(
            isinstance(item, dict) and item.get("id") == item_id
            for item in items
        ):
            errors.append(f"AI-SBOM Issue #746 entry missing from {cluster}")
    extensions = clusters.get("metadata", {}).get("component_extensions", [])
    metadata = next(
        (
            item
            for item in extensions
            if isinstance(item, dict)
            and item.get("id")
            == "m365-bff-failed-partial-safe-completion-contract"
        ),
        None,
    )
    if not isinstance(metadata, dict) or metadata.get("release_readiness") != "blocked":
        errors.append("AI-SBOM Issue #746 metadata must remain release-blocked")


def validate_contract(contract: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if contract.get("schema_version") != "nac.m365-bff-failed-partial-safe-completion/v0.2":
        errors.append("invalid Issue #746 schema_version")
    if contract.get("leading_issue") != "https://github.com/notariat8/NaC/issues/746":
        errors.append("leading_issue must be Issue #746")
    if contract.get("contract_id") != "m365-bff-failed-partial-safe-completion":
        errors.append("contract_id must remain m365-bff-failed-partial-safe-completion")
    for key, expected in {
        "existing_domain_contract": "workflows/contracts/m365-azure-bff-live-activation.contract.json",
        "existing_verification_contract": "workflows/verification-contracts/m365-azure-bff-live-activation.verification.contract.yaml",
    }.items():
        if contract.get(key) != expected or not (REPO_ROOT / expected).is_file():
            errors.append(f"{key} must resolve to the existing #739 contract")
    if contract.get("acceptance_ids") != list(REQUIRED_ACCEPTANCE_IDS):
        errors.append("acceptance_ids must contain AC-746-01 through AC-746-08 in order")
    expected_blockers = {
        "protected_operational_provider_identity_resolution_pending",
        "issue739_original_provenance_lost_terminal",
        "windows_remote_ci_evidence_pending",
    }
    if contract.get("acceptance_status") != "BLOCKED":
        errors.append("acceptance_status must remain BLOCKED until all owner and evidence gates close")
    if set(contract.get("acceptance_blockers", [])) != expected_blockers:
        errors.append("acceptance_blockers must exactly describe the unresolved Issue #746 gates")
    pr_scope = contract.get("pr_scope", {})
    if pr_scope.get("base_ref") != "origin/main":
        errors.append("pr_scope.base_ref must be origin/main")
    if set(pr_scope.get("exact_changed_files", [])) != EXPECTED_PR_FILES:
        errors.append("pr_scope.exact_changed_files does not match the reviewed PR scope")
    for spec_path in SPEC_PATHS:
        if _spec_affected_artifacts(spec_path) != EXPECTED_PR_FILES:
            errors.append(
                f"{spec_path.relative_to(REPO_ROOT)} affected_artifacts must match the exact reviewed PR scope"
            )
    identity_schema = json.loads(IDENTITY_SCHEMA_PATH.read_text(encoding="utf-8"))
    if identity_schema.get("$comment") != "SPDX-License-Identifier: AGPL-3.0-or-later":
        errors.append("technical identity registry schema must declare AGPL-3.0-or-later")

    for group in ("specifications", "plans"):
        paths = contract.get(group)
        if _keys(paths) != {"de", "en"}:
            errors.append(f"{group} must contain de and en")
            continue
        assert isinstance(paths, dict)
        for language, relative in paths.items():
            if not isinstance(relative, str) or not (REPO_ROOT / relative).is_file():
                errors.append(f"{group}.{language} does not resolve to a file")

    provenance = contract.get("provenance")
    if _keys(provenance) != set(REQUIRED_PROVENANCE):
        errors.append("provenance roles must remain exact and distinct")
    else:
        assert isinstance(provenance, dict)
        for key, role in REQUIRED_PROVENANCE.items():
            item = provenance[key]
            if not isinstance(item, dict) or item.get("role") != role or item.get("runtime_state_source") is not False:
                errors.append(f"provenance.{key} must be non-runtime provenance with role {role}")
        if len({item.get("issue") for item in provenance.values() if isinstance(item, dict)}) != 4:
            errors.append("provenance issue numbers must remain distinct")

    gates = contract.get("gates")
    if _keys(gates) != set(REQUIRED_GATES):
        errors.append("three non-interchangeable gates are required")
    else:
        assert isinstance(gates, dict)
        for gate_id, expected_gate in REQUIRED_GATES.items():
            if gates[gate_id] != expected_gate:
                errors.append(
                    f"{gate_id} must remain exactly bound to its issue and authorization"
                )

    commands = contract.get("commands")
    if not isinstance(commands, list) or not commands:
        errors.append("commands must be a non-empty array")
    else:
        platforms = {item.get("platform") for item in commands if isinstance(item, dict)}
        if platforms != REQUIRED_PLATFORMS:
            errors.append(f"commands must cover exactly {sorted(REQUIRED_PLATFORMS)}")
        mapped: set[str] = set()
        actual_commands: dict[str, tuple[str, str, tuple[str, ...], tuple[str, ...], str, str]] = {}
        for item in commands:
            if not isinstance(item, dict):
                errors.append("every command must be an object")
                continue
            command_id = item.get("id")
            if command_id in actual_commands:
                errors.append(f"duplicate command id: {command_id}")
            mapped.update(item.get("acceptance_ids", []))
            if isinstance(command_id, str):
                actual_commands[command_id] = _command_signature(
                    str(item.get("platform")),
                    str(item.get("command")),
                    item.get("acceptance_ids", []),
                    item.get("remote_evidence", []),
                    str(item.get("scope")),
                    str(item.get("side_effect_class")),
                )
        if set(actual_commands) != set(EXPECTED_COMMANDS):
            errors.append("command IDs must match the exact Issue #746 matrix")
        for command_id, expected in EXPECTED_COMMANDS.items():
            if actual_commands.get(command_id) != expected:
                errors.append(f"command {command_id} differs from the approved matrix")
        windows_command = str(EXPECTED_COMMANDS["issue746_windows_tests"][1])
        for manifest_path in (*SPEC_PATHS, *PLAN_PATHS):
            if windows_command not in manifest_path.read_text(encoding="utf-8"):
                errors.append(
                    f"{manifest_path.relative_to(REPO_ROOT)} must contain the exact Windows test command"
                )
        if mapped != set(REQUIRED_ACCEPTANCE_IDS):
            errors.append("commands must map every and only Issue #746 acceptance ID")

    identity_gate = contract.get("identity_gate")
    if not isinstance(identity_gate, dict):
        errors.append("identity_gate is missing")
    else:
        if identity_gate.get("public_registry_scope") != "synthetic_examples_only":
            errors.append("the checked-in identity registry must remain synthetic-only")
        if identity_gate.get("protected_identity_resolver") != {
            "required": True,
            "schema_version": "nac.protected-identity-resolver/v1",
            "contract_id": "issue-746-owner-account-principal-resolution",
            "repository_external": True,
            "platform": "windows_sid_dacl_backend",
            "required_owner_binding": "current_user_sid",
            "required_dacl": "current_user_system_administrators_no_broad_write",
            "nofollow_atomic_open_required": True,
            "duplicate_json_keys_rejected": True,
            "maximum_bytes": 131072,
            "expected_sha256_required": True,
            "git_executable_absolute_path_required": True,
            "git_executable_sha256_required": True,
            "git_path_discovery_forbidden": True,
            "exact_known_account_binding_count": 3,
            "all_known_accounts_same_principal": True,
            "account_identifiers_must_not_enter_repository_or_evidence": True,
        }:
            errors.append("protected identity resolver contract must remain exact")
        if identity_gate.get("separation_key") != "principal_id":
            errors.append("four-eyes separation must use principal_id")
        if identity_gate.get("owner_solo_authority") != {
            "role": "prozessverantwortung", "qualification": "process_design"
        }:
            errors.append("identity_gate.owner_solo_authority must bind role and qualification")
        if identity_gate.get("four_eyes_roles") != {
            "operator": "prozessverantwortung", "approver": "freigabeverantwortung"
        }:
            errors.append("identity_gate.four_eyes_roles must bind both separated roles")
        if identity_gate.get("same_principal_accounts_satisfy_four_eyes") is not False:
            errors.append("accounts of one principal must never satisfy four eyes")
        if identity_gate.get("selected_approval_status") != validate_identity_registry.OWNER_SOLO_APPROVAL:
            errors.append("Issue #746 must select OWNER_SOLO_APPROVAL without a bound external two-person source")
        if identity_gate.get("owner_solo_recorded_as_four_eyes") is not False:
            errors.append("OWNER_SOLO_APPROVAL must never be recorded as four eyes")
        if identity_gate.get("acceptance_requires_second_qualified_principal") is not False:
            errors.append("Issue #746 must not invent an uncited second-principal requirement")
        if identity_gate.get("role_name_alone_proves_two_person_requirement") is not False:
            errors.append("a role label alone must not prove a two-person requirement")
        requirement = identity_gate.get("external_two_person_requirement")
        if requirement != {
            "applies": False,
            "applicable": False,
            "active": False,
            "requires_distinct_natural_persons": False,
            "source_type": None,
            "source_id": None,
            "citation": None,
            "version": None,
            "canonical_digest": None,
            "scope": "issue-746-safe-completion",
            "absence_reason": "no_applicable_cited_external_two_person_requirement",
        }:
            errors.append("Issue #746 external two-person assessment must explicitly record no applicable bound source")
        if set(identity_gate.get("allowed_external_source_types", [])) != {
            "statutory", "regulatory", "contractual", "security_binding"
        }:
            errors.append("external two-person source types must remain exact")
        if identity_gate.get("binding_external_requirement_single_principal_status") != validate_identity_registry.BLOCKED_SINGLE_PRINCIPAL:
            errors.append("binding external two-person duties must block a single principal")
        if identity_gate.get("distinct_qualified_principals_status") != FOUR_EYES_APPROVAL:
            errors.append("true four-eyes approval must require distinct qualified principals")
        if identity_gate.get("invalid_requirement_assessment_status") != BLOCKED_REQUIREMENT_ASSESSMENT_INVALID:
            errors.append("invalid requirement assessments must fail closed")
        if identity_gate.get("required_owner_login_is_transport_only") is not True:
            errors.append("required_owner_login must be declared transport-only")
        if identity_gate.get("governance_authority_field") != "principal_id":
            errors.append("governance authority must bind to principal_id")
        if identity_gate.get("operator_account_source") != "explicit_cli_argument":
            errors.append("operator account must come from an explicit CLI argument")
        if identity_gate.get("operator_account_required") is not True:
            errors.append("operator account must be required for acceptance")
        if identity_gate.get("owner_solo_evidence") != {
            "required": True,
            "source": "protected_identity_resolver_and_live_github_owner_comment",
            "public_registry_is_synthetic_only": True,
            "protected_identity_resolver_required": True,
            "protected_identity_resolver_sha256_bound_to_approval": True,
            "approval_reference_required": True,
            "approval_body_sha256_required": True,
            "provider_qualified_account_input_required": True,
            "account_id_sha256_bound_to_approval": True,
            "principal_id_sha256_bound_to_approval": True,
            "identity_digest_domain_separation": "nac-issue-746-<kind>-v1-null-prefix",
            "raw_resolver_identity_values_in_evidence": False,
            "author_association": "OWNER",
            "issue": 746,
            "pr": 747,
            "bind_to_final_head": True,
            "approval_mode": "OWNER_SOLO_APPROVAL",
            "four_eyes_satisfied": False,
        }:
            errors.append("owner-solo evidence must bind the explicit decision to PR #747 final head")

    identity_cases = contract.get("identity_gate_cases")
    if _keys(identity_cases) != REQUIRED_IDENTITY_GATE_CASES:
        errors.append("identity_gate_cases must contain the exact source-bound approval matrix")
    elif isinstance(identity_cases, dict):
        for case_id in ("missing_process_role", "missing_approval_role", "inactive_identity", "login_registry_mismatch", "missing_operator", "association_only"):
            if identity_cases.get(case_id) != {"expected_status": "BLOCKED"}:
                errors.append(f"identity_gate_cases.{case_id} must remain BLOCKED")
        if identity_cases.get("no_external_requirement_single_principal") != {"expected_status": "OWNER_SOLO_APPROVAL", "four_eyes_satisfied": False}:
            errors.append("single-principal approval without a bound source must be OWNER_SOLO_APPROVAL")
        for case_id in ("binding_external_requirement_single_principal", "binding_external_requirement_same_principal_accounts"):
            if identity_cases.get(case_id) != {"expected_status": "BLOCKED_SINGLE_PRINCIPAL", "mutation_count": 0}:
                errors.append(f"identity_gate_cases.{case_id} must fail closed")
        if identity_cases.get("binding_external_requirement_distinct_principals") != {"expected_status": "FOUR_EYES_APPROVAL", "four_eyes_satisfied": True}:
            errors.append("distinct qualified principals must produce FOUR_EYES_APPROVAL")
        for case_id in ("incomplete_requirement_assessment", "unsupported_requirement_source_type"):
            if identity_cases.get(case_id) != {"expected_status": "BLOCKED_REQUIREMENT_ASSESSMENT_INVALID", "mutation_count": 0}:
                errors.append(f"identity_gate_cases.{case_id} must reject invalid requirement evidence")
    _validate_block_cases(errors, contract.get("approval_replay_cases"), REQUIRED_APPROVAL_REPLAY_CASES, "approval_replay_cases", {"expected_status": "BLOCKED", "mutation_count": 0})
    _validate_block_cases(errors, contract.get("preflight_binding_cases"), REQUIRED_PREFLIGHT_CASES, "preflight_binding_cases", {"expected_status": "BLOCKED", "provider_read_snapshot_count": 0, "total_write_count": 0})
    _validate_block_cases(
        errors,
        contract.get("approval_rebinding_cases"),
        REQUIRED_APPROVAL_REBINDING_CASES,
        "approval_rebinding_cases",
        {
            "expected_status": "FUNCTION_DEPLOYMENT_RECONCILIATION_REQUIRED",
            "provider_read_snapshot_count": 2,
            "current_operation_write_count": 0,
            "new_owner_approval_required": True,
        },
    )
    _validate_block_cases(errors, {key: value for key, value in (contract.get("provider_decision_cases") or {}).items() if key != "stable_not_applied"}, REQUIRED_PROVIDER_BLOCK_CASES, "provider_decision_cases", {"expected_status": "BLOCKED", "provider_write_count": 0, "tenant_write_count": 0, "credential_write_count": 0})
    _validate_block_cases(errors, contract.get("redaction_sentinel_cases"), REQUIRED_REDACTION_SINKS, "redaction_sentinel_cases", {"sentinel_reaches_sink": False, "unknown_field_status": "BLOCKED"})
    _validate_block_cases(errors, contract.get("credential_boundary_cases"), REQUIRED_CREDENTIAL_CASES, "credential_boundary_cases", {"expected_status": "BLOCKED", "credential_write_count": 0, "host_state_unchanged": True})

    if _keys(contract.get("status_counter_hash_cases")) != REQUIRED_STATUS_COUNTER_HASH_CASES:
        errors.append("status_counter_hash_cases must contain the exact planned cases")
    else:
        status_cases = contract["status_counter_hash_cases"]
        exact_status_values = {
            "historic_writes_started_not_current_write": {"historic_writes_started": True, "current_invocation_local_mutation_count": 0},
            "inspection_required_status": {"status": "FUNCTION_DEPLOYMENT_RECONCILIATION_REQUIRED"},
            "not_applied_classification": {"classification": "FUNCTION_DEPLOYMENT_NOT_APPLIED"},
            "stable_contract_codes_exact": {"foreign_codes_allowed": False},
            "observation_codes_exact": {"foreign_codes_allowed": False},
            "all_blocked_branches_case_bound": {"required": True},
            "foreign_code_rejected": {"expected_status": "BLOCKED"},
            "error_platform_backend_unavailable": {"error_code": "PLATFORM_SECURITY_BACKEND_UNAVAILABLE"},
            "preflight_all_counters_zero": {"all_counters": 0},
            "inspection_two_snapshots_zero_mutations": {"provider_read_snapshot_count": 2, "current_invocation_local_mutation_count": 0},
            "release_three_local_appends_only": {"current_invocation_local_mutation_count": 3, "write_scope": "lock_journals_only"},
            "state_hash_unchanged": {"required": True},
            "evidence_hash_unchanged": {"required": True},
            "ledger_hash_unchanged": {"required": True},
            "marker_hash_expected": {"required": True},
            "three_journal_hashes_expected": {"required": True},
            "network_and_subprocess_counts_bounded": {"required": True},
        }
        if status_cases != exact_status_values:
            errors.append("status_counter_hash_cases values differ from the approved matrix")
    if set(contract.get("stable_error_codes_exact", [])) != required_stable_error_codes():
        errors.append("stable_error_codes_exact does not match the Issue #746 contract")
    missing_runtime_codes = _reconciler_literal_error_codes() - set(
        contract.get("stable_error_codes_exact", [])
    )
    if missing_runtime_codes:
        errors.append(
            "stable_error_codes_exact misses reconciler codes: "
            + ", ".join(sorted(missing_runtime_codes))
        )
    missing_provenance_runtime_codes = {
        "FUNCTION_DEPLOYMENT_PROVENANCE_LOST",
        "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_BINDING_INVALID",
        "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_STATE_INVALID",
        "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_STATE_UNINSPECTABLE",
    } - _reconciler_literal_error_codes()
    if missing_provenance_runtime_codes:
        errors.append(
            "terminal provenance-loss runtime codes are missing: "
            + ", ".join(sorted(missing_provenance_runtime_codes))
        )

    windows = contract.get("windows_fail_closed_matrix")
    if _keys(windows) != REQUIRED_WINDOWS_EDGES:
        errors.append("windows_fail_closed_matrix must contain all four live edges")
    else:
        assert isinstance(windows, dict)
        for edge, cases in windows.items():
            if _keys(cases) != REQUIRED_WINDOWS_SIDE_EFFECTS:
                errors.append(f"windows edge {edge} must cover every side-effect boundary")
                continue
            expected_case = (
                {
                    "status": "BLOCKED",
                    "missing_capability_status": "BLOCKED",
                    "reached_after_complete_preflight": False,
                    "write_allowed": False,
                    "required_gate": "not_authorized_by_issue746",
                }
                if edge in {
                    "live", "recovery",
                    "function_deployment_provenance_loss",
                }
                else {
                    "status": "GUARDED_READ_ONLY",
                    "missing_capability_status": "BLOCKED",
                    "reached_after_complete_preflight": True,
                    "write_allowed": False,
                    "required_gate": "issue746_readonly_reconciliation",
                }
            )
            for side_effect, case in cases.items():
                if not isinstance(case, dict) or case != expected_case:
                    errors.append(
                        f"windows {edge}/{side_effect} is not capability-gated"
                    )

    journal = contract.get("journal_crash_cases")
    required_journal = {
        "before_first_append", "after_first_append", "after_second_append",
        "changed_approval", "unknown_tail", "wrong_order",
        "after_third_append_before_return", "same_approval_replay",
    }
    if _keys(journal) != required_journal:
        errors.append("journal_crash_cases must contain all planned crash windows")
    else:
        expected_journal = {
            "before_first_append": {"expected_status": "BLOCKED", "journal_states": ["HELD", "HELD", "HELD"], "same_approval_may_resume": True},
            "after_first_append": {"expected_status": "BLOCKED", "journal_states": ["RELEASED", "HELD", "HELD"], "same_approval_may_resume": True},
            "after_second_append": {"expected_status": "BLOCKED", "journal_states": ["RELEASED", "RELEASED", "HELD"], "same_approval_may_resume": True},
            "changed_approval": {"expected_status": "BLOCKED", "same_approval_may_resume": False},
            "unknown_tail": {"expected_status": "BLOCKED", "same_approval_may_resume": False},
            "wrong_order": {"expected_status": "BLOCKED", "same_approval_may_resume": False},
            "after_third_append_before_return": {"expected_status": "LOCK_JOURNALS_RELEASED", "journal_states": ["RELEASED", "RELEASED", "RELEASED"], "same_approval_may_resume": True},
            "same_approval_replay": {"expected_status": "LOCK_JOURNALS_RELEASED", "journal_states": ["RELEASED", "RELEASED", "RELEASED"], "same_approval_may_resume": True},
        }
        if journal != expected_journal:
            errors.append("journal_crash_cases values differ from the approved matrix")

    expected_reconciler_binding = {
        "command": "nac m365 teams-sharepoint bff-azure-function-deployment-reconcile",
        "terminal_state": "FAILED_PARTIAL",
        "failed_step": "deploy_function_package",
        "failure_code": "AZURE_FUNCTION_DEPLOYMENT_STATE_AMBIGUOUS",
        "inspection_status": "FUNCTION_DEPLOYMENT_RECONCILIATION_REQUIRED",
        "eligible_classification": "FUNCTION_DEPLOYMENT_NOT_APPLIED",
        "provider_read_snapshot_count": 2,
        "inspection_local_mutation_count": 0,
        "provider_write_count": 0,
        "confirmation_argument": "--confirm-release-quarantine",
        "release_action": "RELEASE_QUARANTINE_FOR_NOT_APPLIED_FUNCTION_DEPLOYMENT",
        "release_journal_order": ["target", "legacy", "legacy_host"],
        "resume_count": 0,
        "rollback_count": 0,
        "deletion_count": 0,
    }
    if contract.get("existing_reconciler_binding") != expected_reconciler_binding:
        errors.append("existing #739 reconciler binding differs")

    provenance_loss = contract.get("function_deployment_provenance_loss")
    expected_loss_counters = {
        "github_read_count",
        "credential_access_count",
        "network_access_count",
        "subprocess_count",
        "provider_read_count",
        "provider_write_count",
        "tenant_write_count",
        "local_write_count",
        "journal_append_count",
        "quarantine_release_count",
        "package_build_count",
        "live_run_count",
        "recovery_count",
        "retry_count",
        "rollback_count",
        "deletion_count",
    }
    expected_provenance_loss_keys = {
        "issue",
        "action",
        "run_id",
        "confirmation_schema",
        "confirmation_source",
        "confirmation_sha256_required",
        "identity_resolver_required",
        "identity_resolver_access",
        "identity_resolver_sha256_bound_in_confirmation",
        "principal_mode",
        "owner_confirmation_evidence",
        "legacy_github_approval_arguments_required",
        "legacy_github_approval_arguments_allowed",
        "ordinary_arguments_are_not_trusted_expected_values",
        "canonical_run_path_source",
        "original_lock_binding_source",
        "activation_plan_build_allowed",
        "expected_artifact_categories",
        "positive_condition",
        "partial_expected_inventory",
        "uninspectable_expected_inventory",
        "exact_result",
        "operation_counts_closed",
        "forbidden_sources",
        "opens_gates",
    }
    if not isinstance(provenance_loss, dict):
        errors.append("terminal #739 provenance-loss contract is missing")
    else:
        if set(provenance_loss) != expected_provenance_loss_keys:
            errors.append("terminal #739 provenance-loss keys differ")
        if (
            provenance_loss.get("issue") != 739
            or provenance_loss.get("action")
            != "CONFIRM_FUNCTION_DEPLOYMENT_PROVENANCE_LOST"
            or provenance_loss.get("run_id")
            != "nac-bff-live-20260908-issue739-v4"
            or provenance_loss.get("principal_mode") != "OWNER_SOLO_APPROVAL"
            or provenance_loss.get(
                "identity_resolver_sha256_bound_in_confirmation"
            )
            is not True
            or provenance_loss.get("owner_confirmation_evidence")
            != "protected_confirmation_record_only"
            or provenance_loss.get("legacy_github_approval_arguments_required")
            is not False
            or provenance_loss.get("legacy_github_approval_arguments_allowed")
            is not False
            or provenance_loss.get("original_lock_binding_source")
            != "protected_confirmation_record"
            or provenance_loss.get("activation_plan_build_allowed") is not False
            or provenance_loss.get("confirmation_sha256_required") is not True
            or provenance_loss.get("identity_resolver_required") is not True
            or provenance_loss.get("canonical_run_path_source")
            != "fixed_output_root_plus_confirmed_activation_hash"
            or provenance_loss.get("positive_condition")
            != "canonical_run_directory_and_all_three_confirmation_bound_original_lock_journals_absent"
            or provenance_loss.get("partial_expected_inventory")
            != "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_STATE_INVALID"
            or provenance_loss.get("uninspectable_expected_inventory")
            != "FUNCTION_DEPLOYMENT_PROVENANCE_LOSS_STATE_UNINSPECTABLE"
            or provenance_loss.get("expected_artifact_categories")
            != [
                "resume_state",
                "activation_evidence",
                "ledger",
                "target_lock_journal",
                "legacy_lock_journal",
                "legacy_host_lock_journal",
                "prepared_inputs_manifest",
                "function_package",
            ]
            or provenance_loss.get("forbidden_sources")
            != ["model_knowledge", "issue_text", "provider_state"]
            or provenance_loss.get("ordinary_arguments_are_not_trusted_expected_values")
            is not True
            or provenance_loss.get("opens_gates") != []
        ):
            errors.append("terminal #739 provenance-loss binding differs")
        if provenance_loss.get("exact_result") != {
            "status": "BLOCKED",
            "reason_code": "FUNCTION_DEPLOYMENT_PROVENANCE_LOST",
            "terminal": True,
            "retry_allowed": False,
            "next_phase": None,
            "cli_exit_code": 2,
        }:
            errors.append("terminal #739 provenance-loss result differs")
        counters = provenance_loss.get("operation_counts_closed")
        if (
            not isinstance(counters, dict)
            or set(counters) != expected_loss_counters
            or any(type(value) is not int or value != 0 for value in counters.values())
        ):
            errors.append("terminal #739 provenance-loss counters are not closed zero")

    if set(contract.get("required_existing_regressions", [])) != REQUIRED_EXISTING_REGRESSIONS:
        errors.append("required existing #739 regressions are incomplete")
    elif not REQUIRED_EXISTING_REGRESSIONS.issubset(
        _method_names(RECONCILER_TEST_PATH) | _method_names(
            REPO_ROOT / "tests" / "test_nac_bff_azure_activation_cli.py"
        )
    ):
        errors.append("required existing #739 regression methods are missing")
    if set(contract.get("required_adapter_boundary_regressions", [])) != REQUIRED_ADAPTER_BOUNDARY_REGRESSIONS:
        errors.append("required adapter-boundary regressions are incomplete")
    elif not REQUIRED_ADAPTER_BOUNDARY_REGRESSIONS.issubset(_method_names(LIVE_COMMAND_TEST_PATH)):
        errors.append("required live-command adapter regression methods are missing")
    if not REQUIRED_NEW_TEST_METHODS.issubset(_method_names(TEST_PATH)):
        errors.append("required Issue #746 test methods are missing")

    remote = contract.get("remote_checks")
    if not isinstance(remote, dict) or remote.get("expected_pr") != 747:
        errors.append("remote checks must remain bound to PR #747")
    elif set(remote.get("exact_contexts", [])) != REQUIRED_REMOTE_CONTEXTS:
        errors.append("remote check contexts must match exact workflow/job names")
    elif remote.get("missing_skipped_cancelled_renamed_or_duplicate") != "BLOCKED":
        errors.append("remote check failure states must remain BLOCKED")

    boundary = contract.get("side_effect_boundary")
    if not isinstance(boundary, dict) or any(boundary.get(key) != 0 for key in ("tenant_write_count", "provider_write_count", "credential_write_count", "live_run_count")):
        errors.append("Issue #746 repository work must retain a zero live/write boundary")

    if '"m365_bff_failed_partial_safe_completion"' not in QUALITY_GATE_PATH.read_text(encoding="utf-8"):
        errors.append("strict quality gate does not register the Issue #746 validator")
    expected_windows_command = (
        'python -m unittest discover -s tests -p '
        '"test_m365_bff_failed_partial_safe_completion.py"'
    )
    if expected_windows_command not in WINDOWS_WORKFLOW_PATH.read_text(encoding="utf-8"):
        errors.append("Windows portability workflow does not execute the Issue #746 tests")
    expected_gate_command = (
        'python -m unittest discover -s tests -p '
        '"test_issue746_reconciliation_gate.py"'
    )
    if expected_gate_command not in WINDOWS_WORKFLOW_PATH.read_text(encoding="utf-8"):
        errors.append("Windows portability workflow does not execute the productive Issue #746 gate tests")
    context_index = json.loads(AGENT_CONTEXT_PATH.read_text(encoding="utf-8"))
    if "workflows/verification-contracts/m365-bff-failed-partial-safe-completion.verification.yaml" not in context_index.get("verification_contracts", []):
        errors.append("agent-context verification-contract registry is missing Issue #746")

    registry = json.loads(validate_identity_registry.REGISTRY_PATH.read_text(encoding="utf-8"))
    if (
        validate_identity_registry.validate_registry(registry)
        or validate_identity_registry.validate_public_registry_privacy(registry)
    ):
        errors.append("identity registry is invalid")
    else:
        accounts_by_principal: dict[str, list[str]] = {}
        for account in registry.get("accounts", []):
            if not isinstance(account, dict) or not account.get("active", False):
                continue
            account_id = account.get("account_id")
            principal_id = account.get("principal_id")
            if isinstance(account_id, str) and isinstance(principal_id, str):
                accounts_by_principal.setdefault(principal_id, []).append(account_id)
        for account_ids in accounts_by_principal.values():
            if len(account_ids) > 1 and validate_identity_registry.satisfies_four_eyes(
                registry, account_ids[0], account_ids[1]
            ):
                errors.append("two accounts of one principal incorrectly satisfy four eyes")

    reconciler_text = RECONCILER_PATH.read_text(encoding="utf-8")
    for marker in (
        'ACTION = "RELEASE_QUARANTINE_FOR_NOT_APPLIED_FUNCTION_DEPLOYMENT"',
        'FAILURE_CODE = "AZURE_FUNCTION_DEPLOYMENT_STATE_AMBIGUOUS"',
        'NOT_APPLIED = "FUNCTION_DEPLOYMENT_NOT_APPLIED"',
        'PROVENANCE_LOSS = "FUNCTION_DEPLOYMENT_PROVENANCE_LOST"',
        "def classify_function_deployment_provenance_loss(",
        "_OBSERVATION_ERROR_CODES = frozenset",
    ):
        if marker not in reconciler_text:
            errors.append(f"existing #739 reconciler marker missing: {marker}")

    gate_text = ISSUE746_GATE_PATH.read_text(encoding="utf-8")
    for marker in (
        "class Issue746ReconciliationAuthorization",
        "def verify_issue746_readonly_reconciliation_gate(",
        'AUTHORIZATION_SCOPE = "issue746_readonly_reconciliation"',
        'GATE_CLOSED = "ISSUE_746_RECONCILIATION_GATE_CLOSED"',
        "authorization.verify(expected_head=head, expected_tree=tree)",
    ):
        if marker not in gate_text:
            errors.append(f"productive Issue #746 gate marker missing: {marker}")

    composition_text = ACTIVATION_COMPOSITION_PATH.read_text(encoding="utf-8")
    if composition_text.count(
        "issue746_authorization: Issue746ReconciliationAuthorization"
    ) < 4:
        errors.append("Issue #746 authorization is not mandatory in both factories and runtime verifiers")
    if composition_text.count("self._verify_issue746_authorization()") != 2:
        errors.append("Issue #746 authorization is not revalidated on both provider-read paths")

    cli_text = CLI_PATH.read_text(encoding="utf-8")
    if cli_text.count("verify_issue746_readonly_reconciliation_gate(") != 2:
        errors.append("both reconciliation CLI entries must execute the productive Issue #746 gate")
    if cli_text.count("issue746_authorization=issue746_authorization") != 2:
        errors.append("both reconciliation CLI entries must forward the Issue #746 authorization")
    for forbidden in (
        "issue746_github_reader = GitHubApprovalVerifier(",
        "github_reader.read_json(",
        '["gh", "pr"',
        '["gh", "api"',
    ):
        if forbidden in cli_text or forbidden in gate_text:
            errors.append(
                "Issue #746 read-only reconciliation must use the injected semantic GitHub channel"
            )

    _validate_ai_sbom(errors)
    return errors


def _context_name(item: dict[str, Any]) -> str:
    workflow = item.get("workflowName") or item.get("workflow_name")
    name = item.get("name") or item.get("context")
    return f"{workflow} / {name}" if workflow else str(name)


def validate_check_rollup(checks: Iterable[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in checks:
        grouped.setdefault(_context_name(item), []).append(item)
    for context in sorted(REQUIRED_REMOTE_CONTEXTS):
        instances = grouped.get(context, [])
        if len(instances) != 1:
            errors.append(f"{context}: expected exactly one check, found {len(instances)}")
            continue
        conclusion = str(instances[0].get("conclusion") or instances[0].get("state") or "").upper()
        if conclusion not in {"SUCCESS", "PASSED"}:
            errors.append(f"{context}: expected success, found {conclusion or 'missing'}")
    return errors


def remote_check_negative_cases(valid: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    cases: dict[str, list[dict[str, Any]]] = {}
    cases["missing"] = copy.deepcopy(valid[:-1])
    duplicate = copy.deepcopy(valid)
    duplicate.append(copy.deepcopy(valid[0]))
    cases["duplicate"] = duplicate
    for label, conclusion in (("non_success", "FAILURE"), ("skipped", "SKIPPED"), ("cancelled", "CANCELLED")):
        changed = copy.deepcopy(valid)
        changed[0]["conclusion"] = conclusion
        cases[label] = changed
    renamed = copy.deepcopy(valid)
    renamed[0]["name"] = f"{renamed[0]['name']}-renamed"
    cases["renamed"] = renamed
    return cases


def validate_pr_payload(
    payload: dict[str, Any], *, expected_pr: int, expected_head: str
) -> list[str]:
    errors: list[str] = []
    if payload.get("number") != expected_pr:
        errors.append("returned PR number does not match expected PR")
    repository = payload.get("repository")
    if (
        payload.get("url")
        != f"https://github.com/notariat8/NaC/pull/{expected_pr}"
        or not isinstance(repository, dict)
        or repository.get("nameWithOwner") != "notariat8/NaC"
    ):
        errors.append("returned PR repository identity does not match notariat8/NaC")
    if payload.get("headRefOid") != expected_head:
        errors.append("local expected head does not match PR headRefOid")
    errors.extend(validate_check_rollup(payload.get("statusCheckRollup", [])))
    return errors


def validate_acceptance_roles(
    payload: dict[str, Any],
    registry: dict[str, Any],
    operator_account_id: str,
    identity_gate: dict[str, Any] | None = None,
) -> list[str]:
    errors = validate_identity_registry.validate_registry(registry)
    if errors:
        return ["identity registry is invalid for acceptance"]
    try:
        operator = validate_identity_registry.resolve_principal(
            registry, operator_account_id
        )
    except ValueError:
        operator = None
    if operator is None:
        return ["explicit operator account does not resolve to an active principal"]
    gate = identity_gate or load_contract().get("identity_gate", {})
    requirement = gate.get("external_two_person_requirement", {})
    requirement_applies = requirement.get("applies") is True
    approved_accounts = {
        f"github:{review.get('author', {}).get('login')}"
        for review in payload.get("latestReviews", [])
        if isinstance(review, dict)
        and str(review.get("state", "")).upper() == "APPROVED"
        and isinstance(review.get("author"), dict)
        and isinstance(review["author"].get("login"), str)
    }
    if not requirement_applies:
        decision = validate_identity_registry.evaluate_approval_mode(
            registry,
            operator_account_id=operator_account_id,
            external_two_person_required=False,
        )
        if decision.get("status") != validate_identity_registry.OWNER_SOLO_APPROVAL:
            return [f"Issue #746 owner-solo decision failed: {decision.get('status')}"]
        if str(decision.get("four_eyes_satisfied", "")).lower() != "false":
            return ["OWNER_SOLO_APPROVAL must not claim four-eyes separation"]
        required_role = gate.get("owner_solo_authority", {}).get("role")
        required_qualification = gate.get("owner_solo_authority", {}).get("qualification")
        if required_role not in operator.get("technical_role_ids", []):
            return ["operator principal lacks the required process role"]
        if required_qualification not in operator.get("qualifications", []):
            return ["operator principal lacks the required process qualification"]
        evidence = payload.get("ownerSoloApproval")
        head = payload.get("headRefOid")
        identity_resolver_sha256 = (
            evidence.get("identity_resolver_sha256")
            if isinstance(evidence, dict)
            else None
        )
        if not isinstance(identity_resolver_sha256, str) or not re.fullmatch(
            r"[0-9a-f]{64}", identity_resolver_sha256
        ):
            return ["owner-solo evidence lacks the protected identity resolver digest"]
        canonical_body = (
            "OWNER_SOLO_APPROVAL\n"
            "issue=746\n"
            "pr=747\n"
            f"head_sha={head}\n"
            f"account_id_sha256={identity_binding_sha256('account-id', operator_account_id)}\n"
            f"principal_id_sha256={identity_binding_sha256('principal-id', str(operator.get('principal_id')))}\n"
            f"identity_resolver_sha256={identity_resolver_sha256}\n"
            "four_eyes_satisfied=false"
        )
        expected_evidence = {
            "issue": 746,
            "pr": 747,
            "head_sha": head,
            "account_id_sha256": identity_binding_sha256(
                "account-id", operator_account_id
            ),
            "principal_id_sha256": identity_binding_sha256(
                "principal-id", str(operator.get("principal_id"))
            ),
            "identity_resolver_sha256": identity_resolver_sha256,
            "approval_mode": validate_identity_registry.OWNER_SOLO_APPROVAL,
            "four_eyes_satisfied": False,
            "author_association": "OWNER",
            "approval_reference": evidence.get("approval_reference") if isinstance(evidence, dict) else None,
            "approval_body_sha256": hashlib.sha256(canonical_body.encode("utf-8")).hexdigest(),
        }
        if (
            not isinstance(head, str)
            or len(head) != 40
            or not isinstance(evidence, dict)
            or evidence != expected_evidence
            or not isinstance(evidence.get("approval_reference"), str)
            or not evidence["approval_reference"].startswith(
                "https://github.com/notariat8/NaC/issues/746#issuecomment-"
            )
        ):
            return ["immutable OWNER_SOLO_APPROVAL evidence is missing or not bound to PR #747 final head"]
        return []

    citation = requirement.get("citation")
    source_type = requirement.get("source_type")
    if (
        source_type not in set(gate.get("allowed_external_source_types", []))
        or not isinstance(citation, str)
        or not citation.strip()
        or requirement.get("active") is not True
        or requirement.get("applicable") is not True
        or requirement.get("requires_distinct_natural_persons") is not True
    ):
        return ["bound two-person requirement evidence is invalid or lacks a citation"]
    if str(payload.get("reviewDecision", "")).upper() != "APPROVED":
        return ["current PR reviewDecision is not APPROVED for the bound two-person requirement"]
    approver_role = gate.get("four_eyes_roles", {}).get("approver")
    head = payload.get("headRefOid")
    for review in payload.get("latestReviews", []):
        if not isinstance(review, dict) or str(review.get("state", "")).upper() != "APPROVED":
            continue
        if review.get("commit", {}).get("oid") != head:
            continue
        author = review.get("author")
        login = author.get("login") if isinstance(author, dict) else None
        if not isinstance(login, str):
            continue
        account_id = f"github:{login}"
        try:
            approver = validate_identity_registry.resolve_principal(registry, account_id)
        except ValueError:
            approver = None
        if (
            approver
            and approver.get("principal_id") != operator.get("principal_id")
            and approver_role in approver.get("technical_role_ids", [])
        ):
            return []
    if not approved_accounts:
        return ["bound two-person requirement evidence is invalid or lacks an approved reviewer"]
    return ["bound two-person requirement has no distinct qualified final-head approver principal"]


def load_protected_json(
    path_value: str | None,
    expected_sha256: str | None,
    *,
    label: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    if not path_value or not expected_sha256:
        return None, [f"{label} path and sha256 are required"]
    path = Path(path_value)
    if not path.is_absolute():
        return None, [f"{label} path must be absolute"]
    normalized = Path(os.path.abspath(path_value))
    try:
        normalized.relative_to(REPO_ROOT.resolve())
        return None, [f"{label} must be stored outside the repository"]
    except ValueError:
        pass
    if os.name == "nt":
        try:
            from nac_bff.activation_security_backend import (
                SecurityBoundaryError,
                get_platform_security_backend,
            )

            backend = get_platform_security_backend()
            binding = backend.inspect_private_path(
                normalized, purpose="protected-identity-resolver"
            )
            if binding.size > 131072:
                return None, [f"{label} exceeds the bounded resolver size"]
            with backend.open_bound_read(normalized, binding) as handle:
                payload_bytes = handle.read(131073)
        except (OSError, SecurityBoundaryError, RuntimeError):
            return None, [f"{label} secure Windows handle/SID/DACL open failed"]
        if len(payload_bytes) > 131072:
            return None, [f"{label} exceeds the bounded resolver size"]
    else:
        payload_bytes, secure_errors = _load_posix_protected_bytes(
            normalized, label
        )
        if secure_errors:
            return None, secure_errors
        assert payload_bytes is not None
    actual_sha256 = hashlib.sha256(payload_bytes).hexdigest()
    if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256) or actual_sha256 != expected_sha256:
        return None, [f"{label} sha256 mismatch"]
    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate key")
            result[key] = value
        return result

    try:
        payload = json.loads(
            payload_bytes.decode("utf-8"), object_pairs_hook=reject_duplicate_keys
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return None, [f"{label} must be UTF-8 JSON"]
    if not isinstance(payload, dict):
        return None, [f"{label} must contain a JSON object"]
    return payload, []


def _load_posix_protected_bytes(
    normalized: Path, label: str
) -> tuple[bytes | None, list[str]]:
    nofollow = getattr(os, "O_NOFOLLOW", None)
    directory = getattr(os, "O_DIRECTORY", None)
    if nofollow is None or directory is None:
        return None, [f"{label} requires the supported POSIX no-follow backend"]
    directory_descriptor: int | None = None
    descriptor: int | None = None
    try:
        directory_descriptor = os.open("/", os.O_RDONLY | directory | nofollow)
        components = normalized.parts[1:]
        if not components:
            raise OSError("protected path must identify a leaf file")
        for component in components[:-1]:
            next_descriptor = os.open(
                component,
                os.O_RDONLY | directory | nofollow,
                dir_fd=directory_descriptor,
            )
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        descriptor = os.open(
            components[-1],
            os.O_RDONLY | nofollow,
            dir_fd=directory_descriptor,
        )
    except OSError:
        if descriptor is not None:
            os.close(descriptor)
            descriptor = None
        if directory_descriptor is not None:
            os.close(directory_descriptor)
            directory_descriptor = None
        return None, [f"{label} secure open failed"]
    try:
        file_stat = os.fstat(descriptor)
        if (
            not stat.S_ISREG(file_stat.st_mode)
            or file_stat.st_uid != os.geteuid()
            or stat.S_IMODE(file_stat.st_mode) != 0o600
        ):
            return None, [f"{label} must be owned by the current user with mode 0600"]
        if file_stat.st_size > 131072:
            return None, [f"{label} exceeds the bounded resolver size"]
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            payload_bytes = handle.read(131073)
        if len(payload_bytes) > 131072:
            return None, [f"{label} exceeds the bounded resolver size"]
    finally:
        if descriptor is not None:
            os.close(descriptor)
        if directory_descriptor is not None:
            os.close(directory_descriptor)
    return payload_bytes, []


def validate_protected_identity_resolver(
    payload: dict[str, Any], operator_account_id: str
) -> tuple[dict[str, Any] | None, list[str]]:
    expected_keys = {
        "schema_version",
        "contract_id",
        "known_owner_account_count",
        "all_known_accounts_same_principal",
        "external_two_person_requirement",
        "git_attestation",
        "registry",
    }
    if set(payload) != expected_keys:
        return None, ["protected identity resolver has an invalid shape"]
    if (
        payload.get("schema_version") != "nac.protected-identity-resolver/v1"
        or payload.get("contract_id")
        != "issue-746-owner-account-principal-resolution"
        or payload.get("known_owner_account_count") != 3
        or payload.get("all_known_accounts_same_principal") is not True
    ):
        return None, ["protected identity resolver contract binding is invalid"]
    registry = payload.get("registry")
    if not isinstance(registry, dict) or validate_identity_registry.validate_registry(
        registry
    ):
        return None, ["protected identity resolver registry is invalid"]
    git_attestation = payload.get("git_attestation")
    if (
        not isinstance(git_attestation, dict)
        or set(git_attestation) != {"executable_path", "executable_sha256"}
        or not isinstance(git_attestation.get("executable_path"), str)
        or not Path(git_attestation["executable_path"]).is_absolute()
        or not isinstance(git_attestation.get("executable_sha256"), str)
        or re.fullmatch(r"[0-9a-f]{64}", git_attestation["executable_sha256"])
        is None
    ):
        return None, ["protected identity resolver Git attestation is invalid"]
    accounts = registry.get("accounts", [])
    active_accounts = [
        account
        for account in accounts
        if isinstance(account, dict) and account.get("active") is True
    ]
    principal_ids = {account.get("principal_id") for account in active_accounts}
    if len(accounts) != 3 or len(active_accounts) != 3 or len(principal_ids) != 1:
        return None, ["protected identity resolver must bind exactly three active accounts to one principal"]
    try:
        operator = validate_identity_registry.resolve_principal(
            registry, operator_account_id
        )
    except ValueError:
        operator = None
    if operator is None or operator.get("principal_id") not in principal_ids:
        return None, ["protected identity resolver does not resolve the operator"]
    matching_accounts = [
        account
        for account in active_accounts
        if account.get("account_id") == operator_account_id
    ]
    if (
        len(matching_accounts) != 1
        or matching_accounts[0].get("provider") != "github"
        or matching_accounts[0].get("login")
        != operator_account_id.split(":", 1)[-1]
    ):
        return None, [
            "protected identity resolver does not bind a GitHub operator account"
        ]
    if "prozessverantwortung" not in operator.get("technical_role_ids", []):
        return None, ["protected identity resolver principal lacks the process role"]
    if "freigabeverantwortung" not in operator.get("technical_role_ids", []):
        return None, ["protected identity resolver principal lacks the approval role"]
    if "process_design" not in operator.get("qualifications", []):
        return None, ["protected identity resolver principal lacks the process qualification"]
    requirement = payload.get("external_two_person_requirement")
    if not isinstance(requirement, dict) or set(requirement) != {
        "required", "citation", "scope", "source_sha256"
    }:
        return None, ["protected identity resolver external requirement binding is invalid"]
    if requirement.get("scope") != "issue746_readonly_reconciliation":
        return None, ["protected identity resolver external requirement scope is invalid"]
    if requirement.get("required") is False:
        if requirement.get("citation") is not None or requirement.get("source_sha256") is not None:
            return None, ["protected identity resolver external requirement absence is invalid"]
    elif requirement.get("required") is True:
        citation = requirement.get("citation")
        source_sha256 = requirement.get("source_sha256")
        if not isinstance(citation, str) or not citation.strip() or not isinstance(source_sha256, str) or re.fullmatch(r"[0-9a-f]{64}", source_sha256) is None:
            return None, ["protected identity resolver external requirement evidence is invalid"]
        return None, ["BLOCKED_SINGLE_PRINCIPAL"]
    else:
        return None, ["protected identity resolver external requirement decision is invalid"]
    return operator, []


def fetch_owner_solo_approval(
    reference: str | None,
    *,
    expected_head: str,
    operator_account_id: str,
    operator_principal_id: str,
    identity_resolver_sha256: str,
    github_reader: Any | None,
) -> tuple[dict[str, Any] | None, list[str]]:
    if not re.fullmatch(r"[0-9a-f]{64}", identity_resolver_sha256):
        return None, ["protected identity resolver digest is invalid"]
    match = re.fullmatch(
        r"https://github\.com/notariat8/NaC/issues/746#issuecomment-([1-9][0-9]*)",
        reference or "",
    )
    if match is None:
        return None, ["owner-solo approval reference must identify an Issue #746 comment"]
    if github_reader is None:
        return None, ["cannot read the referenced owner-solo approval comment"]
    try:
        comment = github_reader.read_issue_comment(
            owner="notariat8",
            repository="NaC",
            comment_id=int(match.group(1)),
        )
    except Exception:
        return None, ["cannot read the referenced owner-solo approval comment"]
    if not isinstance(comment, dict):
        return None, ["owner-solo approval comment response is invalid"]
    expected_body = (
        "OWNER_SOLO_APPROVAL\n"
        "issue=746\n"
        "pr=747\n"
        f"head_sha={expected_head}\n"
        f"account_id_sha256={identity_binding_sha256('account-id', operator_account_id)}\n"
        f"principal_id_sha256={identity_binding_sha256('principal-id', operator_principal_id)}\n"
        f"identity_resolver_sha256={identity_resolver_sha256}\n"
        "four_eyes_satisfied=false"
    )
    author = comment.get("user") if isinstance(comment, dict) else None
    author_login = author.get("login") if isinstance(author, dict) else None
    if (
        not isinstance(comment, dict)
        or comment.get("html_url") != reference
        or comment.get("created_at") != comment.get("updated_at")
        or comment.get("author_association") != "OWNER"
        or f"github:{author_login}" != operator_account_id
        or comment.get("body") != expected_body
    ):
        return None, ["owner-solo approval comment provenance or canonical body is invalid"]
    return {
        "issue": 746,
        "pr": 747,
        "head_sha": expected_head,
        "account_id_sha256": identity_binding_sha256(
            "account-id", operator_account_id
        ),
        "principal_id_sha256": identity_binding_sha256(
            "principal-id", operator_principal_id
        ),
        "identity_resolver_sha256": identity_resolver_sha256,
        "approval_mode": validate_identity_registry.OWNER_SOLO_APPROVAL,
        "four_eyes_satisfied": False,
        "author_association": "OWNER",
        "approval_reference": reference,
        "approval_body_sha256": hashlib.sha256(expected_body.encode("utf-8")).hexdigest(),
    }, []


def verify_pr_checks(
    expected_pr: int,
    expected_head_ref: str,
    protected_identity_resolver_file: str | None,
    protected_identity_resolver_sha256: str | None,
    operator_account_id: str,
    owner_solo_approval_reference: str | None,
    *,
    github_reader: Any | None = None,
) -> list[str]:
    errors: list[str] = []
    if expected_pr != 747:
        return ["expected PR must be 747"]
    git = subprocess.run(
        ["git", "rev-parse", expected_head_ref], cwd=REPO_ROOT,
        text=True, capture_output=True, check=False,
    )
    if git.returncode != 0:
        return ["FINAL_HEAD_RESOLUTION_FAILED"]
    expected_head = git.stdout.strip()
    diff = subprocess.run(
        ["git", "diff", "--name-only", "origin/main..." + expected_head],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False,
    )
    if diff.returncode != 0:
        return ["PR_SCOPE_RESOLUTION_FAILED"]
    actual_files = {line.strip().replace("\\", "/") for line in diff.stdout.splitlines() if line.strip()}
    if actual_files != EXPECTED_PR_FILES:
        errors.append(
            "complete base...head file scope differs from the reviewed allowlist: "
            f"missing={sorted(EXPECTED_PR_FILES - actual_files)}, "
            f"unexpected={sorted(actual_files - EXPECTED_PR_FILES)}"
        )
    if github_reader is None:
        errors.append("GITHUB_READ_CHANNEL_UNAVAILABLE")
        return errors
    try:
        payload = github_reader.read_pull_request(
            owner="notariat8", repository="NaC", number=expected_pr
        )
    except Exception:
        errors.append("GITHUB_PR_READ_FAILED")
        return errors
    if not isinstance(payload, dict):
        errors.append("GITHUB_PR_RESPONSE_INVALID")
        return errors
    errors.extend(
        validate_pr_payload(
            payload, expected_pr=expected_pr, expected_head=expected_head
        )
    )
    resolver, resolver_errors = load_protected_json(
        protected_identity_resolver_file,
        protected_identity_resolver_sha256,
        label="protected identity resolver",
    )
    errors.extend(resolver_errors)
    operator = None
    registry: dict[str, Any] = {}
    if resolver is not None:
        operator, identity_errors = validate_protected_identity_resolver(
            resolver, operator_account_id
        )
        errors.extend(identity_errors)
        candidate_registry = resolver.get("registry")
        if isinstance(candidate_registry, dict):
            registry = candidate_registry
    if operator is None:
        errors.append("protected identity resolver does not authorize the operator")
    else:
        approval, approval_errors = fetch_owner_solo_approval(
            owner_solo_approval_reference,
            expected_head=expected_head,
            operator_account_id=operator_account_id,
            operator_principal_id=str(operator.get("principal_id")),
            identity_resolver_sha256=str(protected_identity_resolver_sha256),
            github_reader=github_reader,
        )
        errors.extend(approval_errors)
        if approval is not None:
            payload["ownerSoloApproval"] = approval
    errors.extend(
        validate_acceptance_roles(
            payload,
            registry,
            operator_account_id,
            load_contract().get("identity_gate", {}),
        )
    )
    return errors


def main(
    argv: list[str] | None = None,
    *,
    github_reader: Any | None = None,
) -> int:
    parser = argparse.ArgumentParser(description="Validate the offline Issue #746 safe-completion contract.")
    parser.add_argument("--verify-pr-checks", action="store_true")
    parser.add_argument("--expected-pr", type=int, default=747)
    parser.add_argument("--expected-head-from-local-git", default="HEAD")
    parser.add_argument("--protected-identity-resolver-file")
    parser.add_argument("--protected-identity-resolver-sha256")
    parser.add_argument("--operator-account-id")
    parser.add_argument("--owner-solo-approval-reference")
    args = parser.parse_args(argv)

    errors = validate_contract(load_contract())
    if args.verify_pr_checks:
        missing = [
            option
            for option, value in (
                ("--protected-identity-resolver-file", args.protected_identity_resolver_file),
                ("--protected-identity-resolver-sha256", args.protected_identity_resolver_sha256),
                ("--operator-account-id", args.operator_account_id),
                ("--owner-solo-approval-reference", args.owner_solo_approval_reference),
            )
            if not value
        ]
        if missing:
            errors.append(
                ", ".join(missing) + " required with --verify-pr-checks"
            )
        else:
            errors.extend(
                verify_pr_checks(
                    args.expected_pr,
                    args.expected_head_from_local_git,
                    args.protected_identity_resolver_file,
                    args.protected_identity_resolver_sha256,
                    args.operator_account_id,
                    args.owner_solo_approval_reference,
                    github_reader=github_reader,
                )
            )
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("CONTRACT: VALID")
    print("ACCEPTANCE: BLOCKED")
    print("OK: Issue #746 remains offline and fail-closed; unresolved owner and evidence gates are explicit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
