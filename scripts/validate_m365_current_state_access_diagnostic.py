from __future__ import annotations

import ast
from pathlib import Path
import subprocess
import sys
from typing import Any

try:
    import yaml
except ModuleNotFoundError:  # bootstrap-safe; PyYAML remains the declared runtime
    yaml = None


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT = REPO_ROOT / "workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml"
REQUIRED_TOP_LEVEL = {
    "schema_version", "contract_id", "leading_issue", "delivery_mode",
    "risk_gate", "specifications", "plans", "acceptance_ids", "base_binding",
    "normative_classifications", "ports", "required_remote_checks", "phases",
    "authorization", "snapshot", "side_effect_counters",
    "counter_matrix", "ac_evidence", "exact_artifacts",
    "forbidden_import_markers", "commands",
}
REQUIRED_ACS = [f"AC-748-{index:02d}" for index in range(1, 9)]
REQUIRED_CLASSES = [
    "SPFX_SUBJECT_MISSING",
    "BFF_REQUEST_NOT_OBSERVED",
    "BFF_AUTHENTICATION_REJECTED_401",
    "BFF_AUTHORIZATION_REJECTED_403",
]
REQUIRED_PORTS = [
    "ClientObservationReceiptPort", "TeamsTabMetadataReadPort",
    "SharePointAppCatalogReadPort", "EntraApiPermissionReadPort",
    "AzureFunctionMetadataReadPort", "AzureFunctionRequestLogReadPort",
    "SharePointAccessDecisionReadPort",
]
REQUIRED_CHECKS = [
    "Privacy and Secrets Guard / secret-scan",
    "Privacy and Secrets Guard / privacy-lint",
    "NaC Quality Gate / quality-gate",
    "NaC Windows Portability / windows-offline-cli",
]
REQUIRED_FILES = [
    ".github/workflows/windows-portability.yml",
    "agent-context/index.json",
    "assets/docs/generic-workbench/VIS-721-manifest.json",
    "docs/de/cli.md",
    "docs/en/cli.md",
    "docs/de/superpowers/specs/2026-09-20-m365-current-state-access-diagnostic-design.md",
    "docs/en/superpowers/specs/2026-09-20-m365-current-state-access-diagnostic-design.md",
    "docs/de/superpowers/plans/2026-09-20-m365-current-state-access-diagnostic.md",
    "docs/en/superpowers/plans/2026-09-20-m365-current-state-access-diagnostic.md",
    "scripts/quality_gate.py",
    "scripts/validate_m365_current_state_access_diagnostic.py",
    "scripts/validate_spec_traceability.py",
    "src/nac_bff/current_state_access_diagnostic.py",
    "src/nac_bff/current_state_access_gate.py",
    "src/nac_bff/current_state_access_ports.py",
    "src/nac_bff/activation_security_backend.py",
    "src/nac_bff/azure_live_commands_win.py",
    "src/nac_bff/current_state_access_adapters.py",
    "src/nac_bff/current_state_access_composition.py",
    "tests/test_m365_current_state_access_diagnostic.py",
    "tests/test_m365_current_state_access_gate.py",
    "docs/de/m365-current-state-access-diagnostic.md",
    "docs/en/m365-current-state-access-diagnostic.md",
    "src/nac_cli/cli.py",
    "tests/test_nac_cli.py",
    "tests/test_spec_traceability.py",
    "tests/test_windows_offline_cli_portability.py",
    "workflows/contracts/spec-traceability.contract.json",
    "workflows/verification-contracts/m365-current-state-access-diagnostic.verification.yaml",
]


def _load() -> tuple[dict[str, Any] | None, list[str]]:
    if not CONTRACT.exists():
        return None, ["verification contract missing"]
    try:
        if yaml is not None:
            value = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
        else:
            from validate_spec_traceability import load_simple_yaml_mapping

            value = load_simple_yaml_mapping(CONTRACT)
            acceptance = value.get("acceptance_ids")
            if isinstance(acceptance, str) and acceptance.startswith("["):
                value["acceptance_ids"] = [
                    item.strip()
                    for item in acceptance[1:-1].split(",")
                    if item.strip()
                ]
            for section in ("base_binding", "side_effect_counters", "counter_matrix"):
                mapping = value.get(section)
                if isinstance(mapping, dict):
                    for key, item in tuple(mapping.items()):
                        if isinstance(item, str) and item.isdigit():
                            mapping[key] = int(item)
    except (OSError, ValueError) as exc:
        return None, [f"verification contract unreadable: {exc}"]
    if not isinstance(value, dict):
        return None, ["verification contract must be a mapping"]
    return value, []


def validate() -> list[str]:
    contract, errors = _load()
    if contract is None:
        return errors
    if set(contract) != REQUIRED_TOP_LEVEL:
        errors.append("verification contract top-level schema is not closed")
    checks = (
        ("schema_version", "nac.m365-current-state-access-diagnostic/v0.1"),
        ("contract_id", "m365-current-state-access-diagnostic"),
        ("leading_issue", "https://github.com/notariat8/NaC/issues/748"),
        ("acceptance_ids", REQUIRED_ACS),
        ("normative_classifications", REQUIRED_CLASSES),
        ("ports", REQUIRED_PORTS),
        ("required_remote_checks", REQUIRED_CHECKS),
    )
    for key, expected in checks:
        if contract.get(key) != expected:
            errors.append(f"contract value mismatch: {key}")
    base = contract.get("base_binding", {})
    if base != {
        "merged_pr": 747,
        "merge_commit": "80bf813375d7fc2ab292dfdbcc1db447fdb6684a",
        "merge_tree": "007e277ca5643f7cb63355961fd0422d92fd4b87",
        "final_pr": 749,
        "final_head_must_descend_from_merge_commit": True,
    }:
        errors.append("post-merge base binding mismatch")
    counters = contract.get("side_effect_counters", {})
    if not isinstance(counters, dict) or counters.get("port_factory") != 1 or counters.get("network_read") != "classification_specific" or counters.get("run_gate_consume_write") != 1 or counters.get("result_evidence_write") != 1:
        errors.append("allowed side-effect counters mismatch")
    if isinstance(counters, dict) and any(
        value != 0
        for key, value in counters.items()
        if key not in {"port_factory", "network_read", "run_gate_consume_write", "result_evidence_write"}
    ):
        errors.append("forbidden side-effect counter is nonzero")
    expected_counter_matrix = {
        "repository_implementation_network_read": 0,
        "final_gate_provider_network_read": 0,
        "windows_preflight_network_read": 0,
        "SPFX_SUBJECT_MISSING_network_read_per_acquisition": 2,
        "BFF_REQUEST_NOT_OBSERVED_network_read_per_acquisition": 6,
        "BFF_AUTHENTICATION_REJECTED_401_network_read_per_acquisition": 6,
        "BFF_AUTHORIZATION_REJECTED_403_network_read_per_acquisition": 6,
    }
    if contract.get("counter_matrix") != expected_counter_matrix:
        errors.append("phase/classification counter matrix mismatch")
    exact_artifacts = contract.get("exact_artifacts")
    if not isinstance(exact_artifacts, list) or set(exact_artifacts) != set(REQUIRED_FILES):
        errors.append("exact artifact scope mismatch")
    ac_evidence = contract.get("ac_evidence")
    required_evidence_fields = {
        "artifacts", "validators", "positive_tests", "negative_cases",
        "expected_result", "required_remote_checks",
    }
    if not isinstance(ac_evidence, dict) or set(ac_evidence) != set(REQUIRED_ACS):
        errors.append("AC evidence matrix mismatch")
    else:
        referenced_test_methods: set[str] = set()
        commands = contract.get("commands", [])
        for ac_id, evidence in ac_evidence.items():
            if not isinstance(evidence, dict) or set(evidence) != required_evidence_fields:
                errors.append(f"AC evidence fields mismatch: {ac_id}")
                continue
            for field in required_evidence_fields - {"expected_result"}:
                value = evidence.get(field)
                if not isinstance(value, list) or not value or not all(
                    isinstance(item, str) and item.strip() for item in value
                ):
                    errors.append(f"AC evidence list empty: {ac_id} {field}")
            if not isinstance(evidence.get("expected_result"), str) or not evidence["expected_result"].strip():
                errors.append(f"AC evidence result empty: {ac_id}")
            referenced_test_methods.update(evidence.get("positive_tests", []))
            referenced_test_methods.update(evidence.get("negative_cases", []))
            if set(evidence.get("positive_tests", [])) & set(
                evidence.get("negative_cases", [])
            ):
                errors.append(f"AC positive and negative evidence overlap: {ac_id}")
            for artifact in evidence.get("artifacts", []):
                if artifact not in REQUIRED_FILES:
                    errors.append(f"AC evidence artifact outside exact scope: {ac_id} {artifact}")
            for validator in evidence.get("validators", []):
                if validator not in commands:
                    errors.append(f"AC validator is not executable by contract: {ac_id} {validator}")
            for check in evidence.get("required_remote_checks", []):
                if check not in REQUIRED_CHECKS:
                    errors.append(f"AC check outside required checks: {ac_id} {check}")
    authorization = contract.get("authorization", {})
    if not isinstance(authorization, dict) or any(
        authorization.get(key) is not True
        for key in (
            "required_before_port_factory",
            "required_before_every_read",
            "credential_write_guard_required",
            "persistent_one_shot_marker_required",
            "crash_does_not_restore_run_permission",
        )
    ):
        errors.append("one-shot authorization gate contract mismatch")
    for relative in REQUIRED_FILES:
        if not (REPO_ROOT / relative).is_file():
            errors.append(f"required artifact missing: {relative}")
    try:
        committed = subprocess.run(
            ["git", "diff", "--name-only", "origin/main...HEAD"],
            cwd=REPO_ROOT, check=True, capture_output=True, text=True,
        ).stdout.splitlines()
        status = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=all"],
            cwd=REPO_ROOT, check=True, capture_output=True, text=True,
        ).stdout.splitlines()
        working = {
            line[3:].replace("\\", "/")
            for line in status
            if len(line) > 3
        }
        actual_scope = {path.replace("\\", "/") for path in committed} | working
        if actual_scope != set(REQUIRED_FILES):
            errors.append(
                "actual main...worktree artifact scope mismatch: "
                f"missing={sorted(set(REQUIRED_FILES) - actual_scope)} "
                f"extra={sorted(actual_scope - set(REQUIRED_FILES))}"
            )
    except (OSError, subprocess.CalledProcessError) as exc:
        errors.append(f"actual artifact scope cannot be verified: {exc}")
    source_files = [
        REPO_ROOT / f"src/nac_bff/current_state_access_{name}.py"
        for name in ("diagnostic", "gate", "ports", "adapters", "composition")
    ]
    forbidden = contract.get("forbidden_import_markers", [])
    for path in source_files:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for marker in forbidden if isinstance(forbidden, list) else []:
            if marker in text:
                errors.append(f"forbidden provenance dependency: {path.name} {marker}")
    quality = (REPO_ROOT / "scripts/quality_gate.py").read_text(encoding="utf-8")
    if "scripts/validate_m365_current_state_access_diagnostic.py" not in quality:
        errors.append("feature validator is not registered in quality gate")
    workflow = (REPO_ROOT / ".github/workflows/windows-portability.yml").read_text(encoding="utf-8")
    windows_commands = [
        "python -m unittest discover -s tests -p test_m365_current_state_access_diagnostic.py",
        "python -m unittest discover -s tests -p test_m365_current_state_access_gate.py",
        "python -m unittest discover -s tests -p test_nac_cli.py",
        "python -m unittest discover -s tests -p test_windows_offline_cli_portability.py",
        "python -m unittest discover -s tests -p test_spec_traceability.py",
        "python scripts/validate_m365_current_state_access_diagnostic.py",
        "python scripts/validate_spec_traceability.py",
    ]
    for command in windows_commands:
        if command not in contract.get("commands", []) or command not in workflow:
            errors.append(f"Windows workflow command missing: {command}")
    all_test_methods: set[str] = set()
    for path in (
        REPO_ROOT / "tests/test_m365_current_state_access_diagnostic.py",
        REPO_ROOT / "tests/test_m365_current_state_access_gate.py",
        REPO_ROOT / "tests/test_nac_cli.py",
        REPO_ROOT / "tests/test_windows_offline_cli_portability.py",
        REPO_ROOT / "tests/test_spec_traceability.py",
    ):
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        methods = [node for node in ast.walk(tree) if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")]
        all_test_methods.update(method.name for method in methods)
        if not methods:
            errors.append(f"required test suite is empty: {path.name}")
        if path.name in {
            "test_m365_current_state_access_diagnostic.py",
            "test_m365_current_state_access_gate.py",
        }:
            for node in tree.body:
                if isinstance(node, ast.Raise) and "skiptest" in ast.unparse(node).lower():
                    errors.append(f"required feature suite has module skip: {path.name}")
                if isinstance(node, ast.ClassDef) and any(
                    "skip" in ast.unparse(decorator).lower()
                    for decorator in node.decorator_list
                ):
                    errors.append(f"required feature suite class is skipped: {path.name} {node.name}")
        for method in methods:
            rendered = ast.unparse(method).lower()
            is_feature_suite = path.name in {
                "test_m365_current_state_access_diagnostic.py",
                "test_m365_current_state_access_gate.py",
            }
            if "skip" in rendered and (
                is_feature_suite or method.name in referenced_test_methods
            ):
                errors.append(f"required test is skipped: {path.name} {method.name}")
    if isinstance(ac_evidence, dict):
        missing_methods = referenced_test_methods - all_test_methods
        if missing_methods:
            errors.append(f"AC evidence test methods missing: {sorted(missing_methods)}")
    gate_source = (REPO_ROOT / "src/nac_bff/current_state_access_gate.py").read_text(encoding="utf-8")
    composition_source = (REPO_ROOT / "src/nac_bff/current_state_access_composition.py").read_text(encoding="utf-8")
    for marker in ("create_exclusive", "consume_current_state_run_gate"):
        if marker not in gate_source:
            errors.append(f"persistent run gate marker missing: {marker}")
    protected_start = composition_source.find(
        "def run_current_state_access_diagnostic_from_protected_inputs("
    )
    protected_end = composition_source.find("\n\n__all__", protected_start)
    protected_body = composition_source[protected_start:protected_end]
    consume_position = protected_body.find("consume_current_state_run_gate(")
    github_position = protected_body.find(
        'transport.read(operation="github_gate"'
    )
    provider_authorize_position = protected_body.find(
        "transport.authorize_provider_reads("
    )
    first_verify_position = protected_body.find(
        "verify_consumed_current_state_run_gate("
    )
    verify_position = protected_body.rfind("verify_consumed_current_state_run_gate(")
    factory_position = protected_body.find("ports = build_current_state_access_ports(")
    if (
        protected_start < 0
        or consume_position < 0
        or github_position < 0
        or provider_authorize_position < 0
        or first_verify_position < 0
        or not (
            consume_position < first_verify_position < github_position
            < provider_authorize_position
        )
        or verify_position < 0
        or factory_position < 0
        or not (provider_authorize_position < verify_position < factory_position)
    ):
        errors.append(
            "gate/provider ordering does not enforce consume -> marker verify -> GitHub verify -> "
            "provider authorization -> marker verify -> port factory"
        )
    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("STATUS: FAILED")
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("STATUS: PASSED")
    print("OK: Issue #748 current-state diagnostic contract and evidence matrix are valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
