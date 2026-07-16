from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
DOMAIN_PATH = Path("workflows/contracts/m365-azure-bff-live-activation.contract.json")
VERIFICATION_PATH = Path(
    "workflows/verification-contracts/"
    "m365-azure-bff-live-activation.verification.contract.yaml"
)
RUNNER_PATH = Path("src/nac_bff/azure_activation_runner.py")
COMPOSITION_PATH = Path("src/nac_bff/azure_activation_composition.py")
ATTESTATION_PATH = Path("src/nac_bff/azure_activation_attestations.py")
CLI_PATH = Path("src/nac_cli/cli.py")
M365_RUNNER_PATH = Path("src/nac_m365_graph/mvp_test_environment_deploy.py")
SEALED_TOOLCHAIN_PATH = Path("src/nac_m365_graph/sealed_toolchain.py")
NODE_RUNTIME_INTEGRITY_PATH = Path(
    "src/nac_m365_graph/node_runtime_integrity.py"
)
AZURE_CLI_SEALED_RUNTIME_PATH = Path(
    "src/nac_bff/azure_cli_sealed_runtime.py"
)
BFF_TEST_ENVIRONMENT_PATH = Path("src/nac_bff/test_environment.py")
README_PATH = Path("workflows/contracts/README.md")
QUALITY_GATE_PATH = Path("scripts/quality_gate.py")

LEADING_ISSUE = "https://github.com/notariat8/NaC/issues/632"
PARENT_ISSUE = "https://github.com/notariat8/NaC/issues/620"
ACCEPTANCE_IDS = [f"AC-632-{index:02d}" for index in range(1, 9)]
TOP_LEVEL_FIELDS = [
    "schema_version", "status", "started_at_utc", "finished_at_utc",
    "activation_hash", "approved_commit_sha", "approved_tree_sha",
    "approval_reference_sha256", "toolchain_attestations_sha256",
    "target_binding_sha256",
    "permission_boundary_sha256", "ledger_head_sha256", "step_results", "summary",
]
APPROVAL_FIELDS = [
    "owner-approved", "expected_activation_sha256",
    "approved_commit_sha", "approved_tree_sha",
    "target_binding_sha256", "permission_boundary_sha256",
    "step_sequence_sha256", "toolchain_attestations_sha256",
    "no_automatic_rollback_or_deletion",
]
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
    "tampered_access_passed", "resume_enabled",
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
    "wrong_hash", "wrong_owner_login", "toolchain_attestation_tamper",
    "dirty_tree", "wrong_target", "duplicates", "broader_permissions",
    "race", "secret_sentinel", "prepared_input_drift",
    "health_auth_ready_order", "synthetic_restoration_failure",
    "first_error_after_write", "resume_disabled",
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
    "required_summary_fields": 19,
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
            "tampered",
            "restore_assigned",
            "final_assigned_read",
            "readyz",
        ]
    },
    "synthetic_restoration_failure": {
        "stable_error_code": "SYNTHETIC_STATE_RESTORATION_FAILED"
    },
    "toolchain_attestation_tamper": {
        "stable_error_codes": [
            "TOOLCHAIN_ATTESTATION_INVALID",
            "APPROVAL_PAYLOAD_MISMATCH",
        ]
    },
    "resume_disabled": {"stable_error_code": "RESUME_DISABLED_FOR_MVP"},
}
SOURCE_MARKERS: dict[Path, tuple[str, ...]] = {
    RUNNER_PATH: (
        "_EVIDENCE_KEYS", "_STEP_EVIDENCE_KEYS", "_SUMMARY_EVIDENCE_KEYS",
        "toolchain_attestations_sha256", "TOOLCHAIN_ATTESTATION_INVALID",
        "RESUME_DISABLED_FOR_MVP", "reconcile_azure_bff_live_activation_lock",
        "FINALIZATION_LOCK_RECONCILED",
    ),
    COMPOSITION_PATH: (
        "prepared-inputs.redacted.json", "bicep_parameters_snapshot_sha256",
        "inspect_uami_sites_selected", "inspect_site_read_permission",
        "/healthz", "/readyz", "restore_assigned",
        "toolchain_attestations_sha256", "sealed_toolchain",
        "build_node_runtime_integrity_payloads",
    ),
    ATTESTATION_PATH: (
        "build_activation_attestation_plan",
        "toolchain_attestations_sha256",
        "reads_private_key",
        "executes_provider_requests",
    ),
    CLI_PATH: (
        "bff-azure-activate-live", "bff-azure-activation-attestations",
        "bff-azure-activation-recovery", "--confirm-unlock",
        "--owner-approved", "--execute-live-activation",
        "--azure-cli-toolchain-sha256", "--m365-cli-sha256",
        "--m365-node-sha256", "--build-python-sha256",
        "--build-node-sha256",
        "--build-npm-cli-sha256", "--gh-cli-sha256",
        "--provisioner-certificate-sha256",
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
        "copy_private_azure_config", "validate_private_azure_profile",
        "azureProfile.json", "clouds.config", "AZURE_CONFIG_DIR",
        "AZURE_CLI_RUNTIME_ISOLATION_UNAVAILABLE",
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
}
TEST_PATHS = (
    Path("tests/test_nac_m365_sealed_toolchain.py"),
    Path("tests/test_nac_m365_node_runtime_integrity.py"),
    Path("tests/test_nac_bff_azure_activation.py"),
    Path("tests/test_nac_bff_azure_activation_attestations.py"),
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
    env = dict(os.environ)
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

    gate = domain.get("consolidated_owner_gate")
    if not isinstance(gate, dict):
        errors.append("domain consolidated_owner_gate must be an object")
    else:
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
                "azure_cli_config_mode": (
                    "stable_nofollow_copy_to_private_mount_namespace_tmpfs_plus_"
                    "per_process_exact_profile_binding"
                ),
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

    recovery = domain.get("runner_interface", {}).get("finalization_recovery")
    expected_recovery = {
        "command": "nac m365 teams-sharepoint bff-azure-activation-recovery",
        "same_owner_binding_arguments_as_live_runner_required": True,
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
    for relative in TEST_PATHS:
        if not (repo_root / relative).is_file():
            errors.append(f"missing activation test source: {relative.as_posix()}")
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
