from __future__ import annotations

import hashlib
import importlib.util
import json
import re
from pathlib import Path
from typing import Callable


SCHEMA_VERSION = "nac.m365-azure-bff-offline-readiness/v1"
CONTRACT_ID = "m365.azure_bff_offline_readiness"
COMMAND = "nac m365 teams-sharepoint bff-azure-readiness --format json"

_SOURCE_REQUIREMENTS = {
    "src/nac_bff/test_environment.py": ("class TestEnvironmentBff", "class ValidatedClaims"),
    "src/nac_bff/fastapi_adapter.py": ("def create_fastapi_app", "def create_unconfigured_app"),
    "src/nac_bff/composition.py": ("class BffSettings", "def create_app_from_env"),
    "src/nac_bff/entra_access_token.py": ("class EntraAccessTokenValidator",),
    "src/nac_bff/live_access_decision.py": ("class LiveAccessDecisionAdapter",),
    "src/nac_bff/synthetic_workspace_graph.py": ("class SyntheticWorkspaceGraphRestAdapter",),
}
_HOST_ROOT = "deploy/runtime/azure/nac-bff"
_BICEP_PATH = f"{_HOST_ROOT}/infra/main.bicep"
_PARAMETERS_PATH = f"{_HOST_ROOT}/infra/main.example.bicepparam"
_VERIFICATION_PATH = (
    "workflows/verification-contracts/"
    "m365-azure-bff-offline-readiness.verification.json"
)
_EXPECTED_LOCK = {
    "annotated-types": "0.7.0",
    "anyio": "4.14.2",
    "azure-core": "1.41.0",
    "azure-functions": "1.24.0",
    "azure-identity": "1.25.3",
    "certifi": "2026.6.17",
    "cffi": "2.1.0",
    "charset-normalizer": "3.4.9",
    "cryptography": "45.0.5",
    "fastapi": "0.116.1",
    "idna": "3.18",
    "markupsafe": "3.0.3",
    "msal": "1.37.0",
    "msal-extensions": "1.3.1",
    "pycparser": "3.0",
    "pydantic": "2.13.4",
    "pydantic-core": "2.46.4",
    "pyjwt": "2.13.0",
    "requests": "2.34.2",
    "starlette": "0.47.3",
    "typing-extensions": "4.16.0",
    "typing-inspection": "0.4.2",
    "urllib3": "2.7.0",
    "werkzeug": "3.1.8",
}


def build_azure_bff_readiness(repo_root: Path) -> dict[str, object]:
    root = repo_root.expanduser().resolve()
    checks = [
        _source_check(root),
        _function_host_check(root),
        _packaging_check(root),
        _bicep_check(root),
        _managed_identity_check(root),
        _cors_check(root),
        _readiness_files_check(root),
    ]
    ready_count = sum(check["status"] == "READY" for check in checks)
    status = "READY" if ready_count == len(checks) else "NOT_READY"
    return {
        "schema_version": SCHEMA_VERSION,
        "contract_id": CONTRACT_ID,
        "command": COMMAND,
        "status": status,
        "mode": "offline",
        "summary": {
            "checks_total": len(checks),
            "checks_ready": ready_count,
            "checks_not_ready": len(checks) - ready_count,
        },
        "boundaries": {
            "reads_environment": False,
            "reads_secret_files": False,
            "executes_http": False,
            "executes_dns": False,
            "accesses_azure": False,
            "accesses_graph": False,
            "performs_live_actions": False,
            "writes_files": False,
        },
        "redaction": {
            "file_contents_included": False,
            "environment_values_included": False,
            "credentials_included": False,
            "tenant_or_application_ids_included": False,
            "raw_provider_responses_included": False,
        },
        "checks": checks,
        "plan": [
            {
                "order": index,
                "check_id": check["id"],
                "status": check["status"],
                "action": check["next_action"],
                "live_action": False,
            }
            for index, check in enumerate(checks, start=1)
        ],
    }


def format_azure_bff_readiness(payload: dict[str, object]) -> str:
    lines = [
        f"STATUS: {payload['status']}",
        "MODE: offline",
    ]
    for check in payload.get("checks", []):
        if isinstance(check, dict):
            lines.append(f"{check.get('status')}: {check.get('id')} - {check.get('title')}")
    return "\n".join(lines) + "\n"


def _source_check(root: Path) -> dict[str, object]:
    requirements = [
        _file_with_markers(root, path, markers)
        for path, markers in _SOURCE_REQUIREMENTS.items()
    ]
    return _group(
        "source",
        "BFF source boundary",
        requirements,
        "Restore the missing or incomplete BFF source boundary and rerun the offline check.",
    )


def _function_host_check(root: Path) -> dict[str, object]:
    requirements = [
        _file_with_markers(
            root,
            f"{_HOST_ROOT}/function_app.py",
            ("create_app_from_env", "func.AsgiFunctionApp", "func.AuthLevel.ANONYMOUS"),
        ),
        _json_requirement(
            root,
            f"{_HOST_ROOT}/host.json",
            lambda value: value.get("version") == "2.0"
            and value.get("extensions", {}).get("http", {}).get("routePrefix") == "",
            "Azure Functions host metadata must use host version 2.0 and an empty route prefix.",
        ),
    ]
    return _group(
        "function_host",
        "Azure Functions Python v2 host",
        requirements,
        "Restore the minimal Python v2 Function host metadata and rerun the offline check.",
    )


def _packaging_check(root: Path) -> dict[str, object]:
    funcignore_path = f"{_HOST_ROOT}/.funcignore"
    requirements = [
        _dependency_lock_requirement(root),
        _package_builder_requirement(root),
        _file_with_markers(
            root,
            funcignore_path,
            ("local.settings.json", "tests/", ".venv/", "__pycache__/"),
        ),
    ]
    return _group(
        "packaging",
        "Function package inputs",
        requirements,
        "Restore pinned runtime dependencies and package exclusions, then rerun the offline check.",
    )


def _bicep_check(root: Path) -> dict[str, object]:
    requirements = [
        _file_with_markers(
            root,
            _BICEP_PATH,
            (
                "targetScope = 'resourceGroup'",
                "Microsoft.Storage/storageAccounts@",
                "Microsoft.OperationalInsights/workspaces@",
                "Microsoft.Insights/components@",
                "Microsoft.Web/serverfarms@",
                "Microsoft.Web/sites@",
                "tier: 'FlexConsumption'",
                "name: 'python'",
                "version: '3.12'",
            ),
        ),
        _file_with_markers(
            root,
            _PARAMETERS_PATH,
            (
                "using './main.bicep'",
                "param location = 'germanywestcentral'",
            ),
        ),
        _text_requirement(
            root,
            _BICEP_PATH,
            _contains_no_bicep_secrets,
            "Bicep must not contain secret parameters, key listing, credentials or Graph provisioning.",
        ),
        _bicep_compile_evidence_requirement(root),
    ]
    return _group(
        "bicep",
        "Azure Bicep baseline",
        requirements,
        "Restore the bounded resource-group Bicep baseline and rerun the offline check.",
    )


def _managed_identity_check(root: Path) -> dict[str, object]:
    requirements = [
        _file_with_markers(
            root,
            _BICEP_PATH,
            (
                "Microsoft.ManagedIdentity/userAssignedIdentities@",
                "type: 'SystemAssigned, UserAssigned'",
                "userAssignedIdentityResourceId: managedIdentity.id",
                "allowSharedKeyAccess: false",
                "defaultToOAuthAuthentication: true",
                "DisableLocalAuth: true",
                "AzureWebJobsStorage__clientId: managedIdentity.properties.clientId",
                "AzureWebJobsStorage__credential: 'managedidentity'",
                "Authorization=AAD",
            ),
        ),
        _managed_identity_adapter_requirement(root),
    ]
    return _group(
        "managed_identity",
        "Separated system- and user-assigned managed identities",
        requirements,
        "Restore the system-assigned broker boundary and the client-id-bound UAMI storage, telemetry and Graph bindings, then rerun the offline check.",
    )


def _cors_check(root: Path) -> dict[str, object]:
    requirements = [
        _text_requirement(
            root,
            _BICEP_PATH,
            _cors_is_bounded,
            "CORS must use one non-empty allowlist parameter without credentials or implicit origins.",
        ),
        _text_requirement(
            root,
            _PARAMETERS_PATH,
            lambda text: "param corsAllowedOrigins" not in text,
            "Example CORS parameters must be explicit and must not contain a wildcard.",
        ),
    ]
    return _group(
        "cors",
        "Explicit CORS allowlist",
        requirements,
        "Restore the explicit non-wildcard CORS allowlist and rerun the offline check.",
    )


def _readiness_files_check(root: Path) -> dict[str, object]:
    requirements = [
        _file_with_markers(
            root,
            "src/nac_bff/fastapi_adapter.py",
            ('@app.get("/healthz"', '@app.get("/readyz"', "ready=False"),
        ),
        _file_with_markers(
            root,
            "src/nac_bff/composition.py",
            ("return create_unconfigured_app()", "def create_app_from_env"),
        ),
        _file_with_markers(
            root,
            f"{_HOST_ROOT}/host.json",
            ('"routePrefix": ""',),
        ),
    ]
    return _group(
        "readiness_files",
        "Health and readiness files",
        requirements,
        "Restore fail-closed health/readiness wiring and rerun the offline check.",
    )


def _dependency_lock_requirement(root: Path) -> dict[str, object]:
    relative_path = f"{_HOST_ROOT}/requirements.txt"
    ready = False
    try:
        content = (root / relative_path).read_bytes()
        text = content.decode("utf-8")
        entries = [
            (re.sub(r"[-_.]+", "-", name).lower(), version)
            for name, version in re.findall(
                r"(?m)^([A-Za-z0-9_.-]+)==([A-Za-z0-9_.+-]+)\s+\\$",
                text,
            )
        ]
        evidence = _verification_descriptor(root).get("dependency_lock_evidence", {})
        ready = (
            len(entries) == len(_EXPECTED_LOCK)
            and dict(entries) == _EXPECTED_LOCK
            and isinstance(evidence, dict)
            and evidence.get("status") == "PASSED"
            and evidence.get("path") == relative_path
            and evidence.get("sha256") == hashlib.sha256(content).hexdigest()
            and evidence.get("package_count") == len(_EXPECTED_LOCK)
            and evidence.get("python_runtime") == "3.12"
            and evidence.get("platform") == "linux-x86_64"
        )
    except (OSError, UnicodeError, json.JSONDecodeError):
        ready = False
    return {
        "path": relative_path,
        "status": "READY" if ready else "NOT_READY",
        "detail": (
            "Exact transitive dependency closure and artifact hashes are bound."
            if ready
            else "Dependency lock must match the exact reviewed closure, hashes and evidence digest."
        ),
    }


def _package_builder_requirement(root: Path) -> dict[str, object]:
    relative_path = f"{_HOST_ROOT}/build_package.py"
    ready = False
    try:
        spec = importlib.util.spec_from_file_location(
            "_nac_bff_offline_package_builder",
            root / relative_path,
        )
        if spec is None or spec.loader is None:
            raise ImportError("package builder is not loadable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        first = module.build_package_bytes()
        second = module.build_package_bytes()
        ready = first == second and module.validate_package(first) == []
    except Exception:
        ready = False
    return {
        "path": relative_path,
        "status": "READY" if ready else "NOT_READY",
        "detail": (
            "Two in-memory builds match and manifest, ZIP metadata, Python compilation and import closure validate."
            if ready
            else "Deterministic package build, manifest or import-closure validation failed."
        ),
    }


def _bicep_compile_evidence_requirement(root: Path) -> dict[str, object]:
    ready = False
    evidence = _verification_descriptor(root).get("bicep_compile_evidence", {})
    try:
        template = evidence.get("template", {})
        parameters = evidence.get("parameters", {})
        execution = evidence.get("execution_boundary", {})
        ready = (
            isinstance(evidence, dict)
            and evidence.get("status") == "PASSED"
            and evidence.get("compiler") == "bicep-cli"
            and evidence.get("compiler_version") == "0.45.6"
            and evidence.get("commands")
            == [
                "az bicep build --file deploy/runtime/azure/nac-bff/infra/main.bicep --stdout",
                "az bicep build-params --file deploy/runtime/azure/nac-bff/infra/main.example.bicepparam --stdout",
            ]
            and _compiled_input_matches(root, template, _BICEP_PATH)
            and _compiled_input_matches(root, parameters, _PARAMETERS_PATH)
            and isinstance(execution, dict)
            and execution
            and all(value is False for value in execution.values())
        )
    except (OSError, AttributeError, TypeError):
        ready = False
    return {
        "path": _VERIFICATION_PATH,
        "status": "READY" if ready else "NOT_READY",
        "detail": (
            "Pinned Bicep compiler outputs are hash-bound to both current inputs."
            if ready
            else "Fresh pinned Bicep build and build-params evidence is missing or stale."
        ),
    }


def _compiled_input_matches(
    root: Path,
    evidence: object,
    expected_path: str,
) -> bool:
    if not isinstance(evidence, dict) or evidence.get("path") != expected_path:
        return False
    output_hash = evidence.get("compiled_sha256")
    compiled_path = evidence.get("compiled_path")
    if not isinstance(compiled_path, str) or not compiled_path:
        return False
    compiled_file = root / compiled_path
    try:
        compiled_bytes = compiled_file.read_bytes()
        compiled_document = json.loads(compiled_bytes.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False
    return (
        evidence.get("source_sha256")
        == hashlib.sha256((root / expected_path).read_bytes()).hexdigest()
        and isinstance(output_hash, str)
        and output_hash == hashlib.sha256(compiled_bytes).hexdigest()
        and isinstance(compiled_document, dict)
    )


def _managed_identity_adapter_requirement(root: Path) -> dict[str, object]:
    relative_path = "src/nac_bff/composition.py"
    ready = False
    try:
        composition = (root / relative_path).read_text(encoding="utf-8")
        forbidden = (
            "ClientSecretCredential",
            "CertificateCredential",
            "DefaultAzureCredential",
            "client_secret",
            "certificate_path",
            "certificate_data",
        )
        ready = (
            "from azure.identity import ManagedIdentityCredential" in composition
            and "credential_factory = ManagedIdentityCredential" in composition
            and "credential_factory(client_id=client_id)" in composition
            and '"https://graph.microsoft.com/.default"' in composition
            and "ManagedIdentityGraphTokenProvider(credential)" in composition
            and not any(marker in composition for marker in forbidden)
        )
    except (OSError, UnicodeError, ValueError):
        ready = False
    return {
        "path": relative_path,
        "status": "READY" if ready else "NOT_READY",
        "detail": (
            "BFF composition uses explicit user-assigned ManagedIdentityCredential for Graph."
            if ready
            else "BFF composition must use a client-id-bound ManagedIdentityCredential adapter without secret or certificate credentials."
        ),
    }


def _verification_descriptor(root: Path) -> dict[str, object]:
    try:
        value = json.loads((root / _VERIFICATION_PATH).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _group(
    check_id: str,
    title: str,
    requirements: list[dict[str, object]],
    remediation: str,
) -> dict[str, object]:
    status = "READY" if all(item["status"] == "READY" for item in requirements) else "NOT_READY"
    return {
        "id": check_id,
        "title": title,
        "status": status,
        "requirements": requirements,
        "next_action": "No change required; retain offline review evidence." if status == "READY" else remediation,
    }


def _file_with_markers(root: Path, relative_path: str, markers: tuple[str, ...]) -> dict[str, object]:
    return _text_requirement(
        root,
        relative_path,
        lambda text: all(marker in text for marker in markers),
        "Required file or static markers are missing.",
    )


def _text_requirement(
    root: Path,
    relative_path: str,
    predicate: Callable[[str], bool],
    failure: str,
) -> dict[str, object]:
    path = root / relative_path
    try:
        text = path.read_text(encoding="utf-8")
        ready = path.is_file() and predicate(text)
    except (OSError, UnicodeError):
        ready = False
    return {
        "path": relative_path,
        "status": "READY" if ready else "NOT_READY",
        "detail": "Static requirement satisfied." if ready else failure,
    }


def _json_requirement(
    root: Path,
    relative_path: str,
    predicate: Callable[[dict[str, object]], bool],
    failure: str,
) -> dict[str, object]:
    path = root / relative_path
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        ready = path.is_file() and isinstance(value, dict) and predicate(value)
    except (OSError, UnicodeError, json.JSONDecodeError):
        ready = False
    return {
        "path": relative_path,
        "status": "READY" if ready else "NOT_READY",
        "detail": "Static requirement satisfied." if ready else failure,
    }


def _contains_no_bicep_secrets(text: str) -> bool:
    lowered = text.lower()
    forbidden = (
        "@secure",
        "listkeys(",
        "listcredentials(",
        "client_secret",
        "clientsecret",
        "password",
        "sharedaccesssignature",
        "microsoft.graph/",
        "serviceprincipals@",
        "approleassignments@",
    )
    return not any(term in lowered for term in forbidden)


def _cors_is_bounded(text: str) -> bool:
    origins = (
        "https://funktion8.sharepoint.com",
        "https://teams.microsoft.com",
        "https://teams.cloud.microsoft",
    )
    return (
        text.count("var corsAllowedOrigins = [") == 1
        and "param corsAllowedOrigins" not in text
        and all(text.count(origin) == 1 for origin in origins)
        and text.count("allowedOrigins: corsAllowedOrigins") == 1
        and "supportCredentials: false" in text
        and "azurewebsites.net" not in text.lower()
        and "'*'" not in text
    )
