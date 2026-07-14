from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from nac_bff.azure_readiness import (  # noqa: E402
    COMMAND,
    CONTRACT_ID,
    SCHEMA_VERSION,
    build_azure_bff_readiness,
)


CONTRACT_PATH = "workflows/contracts/m365-azure-bff-offline-readiness.contract.json"
VERIFICATION_PATH = (
    "workflows/verification-contracts/"
    "m365-azure-bff-offline-readiness.verification.json"
)
LEADING_ISSUE = "https://github.com/notariat8/NaC/issues/620"
ACCEPTANCE_IDS = [f"AC-620-{index:02d}" for index in range(1, 8)]
EVIDENCE_DEPENDENCIES = {
    "live_verification_contract": {
        "path": "workflows/verification-contracts/m365-mvp-test-environment-live.verification.json",
        "sha256": "c55be3abaf0807b37851ada42a49c8eb1a88be1c6cd1dce70c57896b1c8fac81",
        "status": "PASSED",
        "schema_version": "nac.verification-contract/v0.1",
        "contract_id": "verification.m365_mvp_test_environment_live_attestation",
        "leading_issue": LEADING_ISSUE,
    },
    "live_redacted_evidence": {
        "path": "workflows/verification-contracts/evidence/m365-mvp-test-environment-deploy.redacted.json",
        "sha256": "65f0276a248f533e95caf35b63bc3c402108226734bf3f939d85a7cddbc9c1ea",
        "status": "PASSED",
        "schema_version": "nac.m365-mvp-test-environment-deploy-evidence/v0.1",
    },
}
EXPECTED_CATEGORIES = [
    "source",
    "function_host",
    "packaging",
    "bicep",
    "managed_identity",
    "cors",
    "readiness_files",
]
REQUIRED_MARKERS: dict[str, tuple[str, ...]] = {
    "src/nac_cli/cli.py": (
        "bff-azure-readiness",
        "build_azure_bff_readiness",
        "format_azure_bff_readiness",
    ),
    "src/nac_bff/fastapi_adapter.py": (
        "run_sync_with_request_budget",
        "request deadline exceeded",
    ),
    "deploy/runtime/azure/nac-bff/build_package.py": (
        "def build_package_bytes",
        "def validate_package",
        "package-manifest.json",
        "remoteBuildRequired",
        "--build-remote true",
    ),
    "scripts/quality_gate.py": (
        "m365_azure_bff_offline_readiness",
        "M365 Azure BFF Offline Readiness",
        "scripts/validate_m365_azure_bff_offline_readiness.py",
    ),
    "docs/de/cli.md": (
        COMMAND,
        "ausschließlich offline",
        "keine Environment-Secrets",
        "keine HTTP-, DNS-, Azure- oder Graph-Zugriffe",
        "READY` oder `NOT_READY",
    ),
    "docs/en/cli.md": (
        COMMAND,
        "exclusively offline",
        "no environment secrets",
        "no HTTP, DNS,",
        "Azure or Graph access",
        "READY` or `NOT_READY",
    ),
    "tests/test_nac_bff_azure_readiness.py": (
        "test_current_repository_is_ready_with_bound_compile_evidence",
        "test_builder_does_not_use_environment_network_dns_or_subprocesses",
        "test_package_builder_is_byte_deterministic_and_manifest_valid",
        "test_unhashed_or_incomplete_dependency_lock_is_not_ready",
        "test_stale_bicep_compile_evidence_is_not_ready",
        "test_central_cli_emits_json_and_ready_exit_code",
    ),
}


def main() -> int:
    errors = validate(REPO_ROOT)
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: M365 Azure BFF readiness is deterministic, redacted and offline-only.")
    return 0


def validate(repo_root: Path) -> list[str]:
    errors: list[str] = []
    contract = _read_json(repo_root / CONTRACT_PATH, errors)
    if contract:
        _validate_contract(contract, repo_root, errors)
    verification = _read_json(repo_root / VERIFICATION_PATH, errors)
    if verification:
        _validate_verification_contract(verification, repo_root, errors)
    _validate_markers(repo_root, errors)
    try:
        readiness = build_azure_bff_readiness(repo_root)
    except Exception as exc:
        errors.append(f"offline readiness builder failed: {type(exc).__name__}")
    else:
        _validate_readiness(readiness, errors)
    return errors


def _read_json(path: Path, errors: list[str]) -> dict[str, Any]:
    if not path.is_file():
        errors.append(f"missing contract: {CONTRACT_PATH}")
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid contract JSON: {type(exc).__name__}")
        return {}
    if not isinstance(payload, dict):
        errors.append("contract must be a JSON object")
        return {}
    return payload


def _validate_contract(contract: dict[str, Any], repo_root: Path, errors: list[str]) -> None:
    expected = {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "status": "implemented_offline_gate",
        "command": COMMAND,
    }
    for key, value in expected.items():
        if contract.get(key) != value:
            errors.append(f"contract {key} must be {value}")

    if contract.get("leading_issue") != LEADING_ISSUE:
        errors.append(f"contract leading_issue must be {LEADING_ISSUE}")
    if contract.get("acceptance_ids") != ACCEPTANCE_IDS:
        errors.append("contract acceptance_ids must trace all Issue #620 criteria")
    if contract.get("verification_contract") != VERIFICATION_PATH:
        errors.append("contract verification_contract must reference its paired descriptor")
    if set(contract.get("acceptance_traceability", {})) != set(ACCEPTANCE_IDS):
        errors.append("contract acceptance_traceability must cover every acceptance ID")
    _validate_evidence_dependencies(contract, repo_root, "contract", errors)
    deployment = contract.get("deployment_boundary")
    if not isinstance(deployment, dict) or deployment.get("technology") != "Azure Functions Flex Consumption OneDeploy" or deployment.get("remote_build_required") is not True or deployment.get("required_cli_flag") != "--build-remote true":
        errors.append("contract must require Flex OneDeploy remote build")

    inputs = contract.get("input_boundary")
    if not isinstance(inputs, dict) or inputs.get("categories") != EXPECTED_CATEGORIES:
        errors.append("contract input_boundary.categories must define the seven readiness categories")
    elif inputs.get("repository_files_only") is not True:
        errors.append("contract input_boundary.repository_files_only must be true")

    offline = contract.get("offline_boundary")
    if not isinstance(offline, dict) or not offline:
        errors.append("contract offline_boundary must be a non-empty object")
    elif any(value is not False for value in offline.values()):
        errors.append("all contract offline_boundary values must be false")

    output = contract.get("output_contract")
    if not isinstance(output, dict):
        errors.append("contract output_contract must be an object")
    else:
        if output.get("statuses") != ["READY", "NOT_READY"]:
            errors.append("contract output statuses must be READY and NOT_READY")
        if output.get("deterministic") is not True or output.get("redacted") is not True:
            errors.append("contract output must be deterministic and redacted")
        if output.get("exit_codes") != {"READY": 0, "NOT_READY": 2}:
            errors.append("contract exit codes must map READY to 0 and NOT_READY to 2")

    redaction = contract.get("redaction")
    if not isinstance(redaction, dict):
        errors.append("contract redaction must be an object")
    else:
        for field in (
            "file_contents_included",
            "environment_values_included",
            "credentials_included",
            "tenant_or_application_ids_included",
            "raw_provider_responses_included",
        ):
            if redaction.get(field) is not False:
                errors.append(f"contract redaction.{field} must be false")


def _validate_verification_contract(
    verification: dict[str, Any],
    repo_root: Path,
    errors: list[str],
) -> None:
    expected = {
        "schema_version": "nac.verification-contract/v0.1",
        "contract_id": "verification.m365_azure_bff_offline_readiness",
        "domain_contract_id": CONTRACT_ID,
        "leading_issue": LEADING_ISSUE,
    }
    for key, value in expected.items():
        if verification.get(key) != value:
            errors.append(f"verification contract {key} must be {value}")
    if verification.get("acceptance_ids") != ACCEPTANCE_IDS:
        errors.append("verification contract must trace all Issue #620 acceptance IDs")
    if set(verification.get("acceptance_traceability", {})) != set(ACCEPTANCE_IDS):
        errors.append("verification acceptance traceability must cover every acceptance ID")
    _validate_evidence_dependencies(verification, repo_root, "verification", errors)

    lock = verification.get("dependency_lock_evidence")
    if not isinstance(lock, dict):
        errors.append("verification dependency_lock_evidence must be an object")
    else:
        if lock.get("status") != "PASSED":
            errors.append("dependency lock evidence must be PASSED")
        if lock.get("path") != "deploy/runtime/azure/nac-bff/requirements.txt":
            errors.append("dependency lock evidence path is invalid")
        if lock.get("package_count") != 24:
            errors.append("dependency lock evidence must bind exactly 24 packages")
        direct = lock.get("direct_dependencies")
        if not isinstance(direct, dict) or direct.get("azure-identity") != "1.25.3":
            errors.append("dependency lock evidence must bind azure-identity 1.25.3")
        digest = lock.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            errors.append("dependency lock evidence must include a SHA-256 digest")

    bicep = verification.get("bicep_compile_evidence")
    allowed_bicep_statuses = {"PASSED"}
    if not isinstance(bicep, dict):
        errors.append("verification bicep_compile_evidence must be an object")
    else:
        if bicep.get("status") not in allowed_bicep_statuses:
            errors.append("Bicep evidence must be PASSED")
        if bicep.get("compiler_version") != "0.45.6":
            errors.append("Bicep evidence must pin compiler version 0.45.6")
        execution = bicep.get("execution_boundary")
        if not isinstance(execution, dict) or any(
            value is not False for value in execution.values()
        ):
            errors.append("Bicep evidence execution boundaries must all be false")



def _validate_evidence_dependencies(
    document: dict[str, Any],
    repo_root: Path,
    label: str,
    errors: list[str],
) -> None:
    if document.get("evidence_dependencies") != EVIDENCE_DEPENDENCIES:
        errors.append(f"{label} evidence dependencies must bind the live MVP baseline")
        return
    for dependency_id, descriptor in EVIDENCE_DEPENDENCIES.items():
        relative_path = descriptor["path"]
        path = repo_root / relative_path
        if not path.is_file():
            errors.append(f"{label} evidence dependency is missing: {relative_path}")
            continue
        try:
            raw = path.read_bytes()
            payload = json.loads(raw)
        except (OSError, json.JSONDecodeError):
            errors.append(f"{label} evidence dependency is invalid: {relative_path}")
            continue
        if not isinstance(payload, dict):
            errors.append(f"{label} evidence dependency must be an object: {relative_path}")
            continue
        if hashlib.sha256(raw).hexdigest() != descriptor["sha256"]:
            errors.append(f"{label} evidence dependency digest mismatch: {relative_path}")
        if payload.get("status") != descriptor["status"]:
            errors.append(f"{label} evidence dependency must be PASSED: {relative_path}")
        schema_key = (
            "schemaVersion"
            if dependency_id == "live_redacted_evidence"
            else "schema_version"
        )
        if payload.get(schema_key) != descriptor["schema_version"]:
            errors.append(f"{label} evidence dependency schema mismatch: {relative_path}")
        if dependency_id == "live_verification_contract":
            if payload.get("contract_id") != descriptor["contract_id"]:
                errors.append(f"{label} live verification contract ID mismatch")
            if payload.get("leading_issue") != descriptor["leading_issue"]:
                errors.append(f"{label} live verification issue binding mismatch")
            scope = payload.get("verification_scope")
            if (
                not isinstance(scope, dict)
                or scope.get("workspace_id_exact") != "notary_team_01"
                or scope.get("data_class_exact") != "synthetic_only"
            ):
                errors.append(f"{label} live verification scope binding mismatch")
        else:
            scope = payload.get("scope")
            if (
                not isinstance(scope, dict)
                or scope.get("workspaceVerified") is not True
            ):
                errors.append(f"{label} live evidence workspace verification mismatch")

def _validate_markers(repo_root: Path, errors: list[str]) -> None:
    for relative_path, markers in REQUIRED_MARKERS.items():
        path = repo_root / relative_path
        if not path.is_file():
            errors.append(f"missing required file: {relative_path}")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            errors.append(f"could not read required file: {relative_path}")
            continue
        for marker in markers:
            if marker not in text:
                errors.append(f"{relative_path} is missing marker: {marker}")


def _validate_readiness(readiness: dict[str, object], errors: list[str]) -> None:
    if readiness.get("schema_version") != SCHEMA_VERSION:
        errors.append("readiness schema version does not match the contract")
    if readiness.get("contract_id") != CONTRACT_ID:
        errors.append("readiness contract ID does not match the contract")
    if readiness.get("status") != "READY":
        errors.append("repository Azure BFF readiness must be READY")
    checks = readiness.get("checks")
    if not isinstance(checks, list) or [check.get("id") for check in checks] != EXPECTED_CATEGORIES:
        errors.append("readiness output must contain the seven ordered categories")
    else:
        statuses = {check["id"]: check.get("status") for check in checks}
        for check_id in (
            "source",
            "function_host",
            "packaging",
            "bicep",
            "managed_identity",
            "cors",
            "readiness_files",
        ):
            if statuses.get(check_id) != "READY":
                errors.append(f"readiness category {check_id} must be READY")
    boundaries = readiness.get("boundaries")
    if not isinstance(boundaries, dict) or any(value is not False for value in boundaries.values()):
        errors.append("readiness output boundaries must all remain false")
    redaction = readiness.get("redaction")
    if not isinstance(redaction, dict) or any(value is not False for value in redaction.values()):
        errors.append("readiness output redaction flags must all remain false")


if __name__ == "__main__":
    raise SystemExit(main())
